"""Orchestrator — the single place the multi-agent pipeline is defined.

Execution graph:

    ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │ Trend Agent  │  │ Audience Agent   │  │ Creative Agent   │
    │ (web search) │  │                  │  │                  │
    └──────┬───────┘  └────────┬─────────┘  └────────┬─────────┘
           │                   │                     │
           └──── Stage 1: PARALLEL (asyncio.gather) ─┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Scoring Agent    │   Stage 2 — needs creative output
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Supervisor       │   Stage 3 — needs all 4 outputs
                    │ (Sonnet)         │
                    └──────────────────┘

Why this graph: Trend, Audience, and Creative are independent → parallel.
Scoring needs concepts to score → after Creative. Supervisor needs
everything → last. BaseAgent.run() captures failures as
AgentResult(success=False), so one agent failing degrades the pipeline
instead of crashing it — the supervisor is told which inputs are missing.
"""
import asyncio
import uuid

import structlog

from app.agents import (
    AudienceAgent,
    CreativeAgent,
    ScoringAgent,
    SupervisorAgent,
    TrendAgent,
)
from app.db.store import RunStore, get_store
from app.schemas import AgentEvent, AgentStatus, CampaignBrief, PipelineRun
from app.services.event_bus import EventBus, get_event_bus
from app.services.llm import LLMClient, get_llm_client

log = structlog.get_logger()


class Orchestrator:
    """Stateless — safe to share across requests. Dependencies are injectable
    so tests can pass a stub LLM client and an isolated store."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        bus: EventBus | None = None,
        store: RunStore | None = None,
    ):
        self.llm = llm or get_llm_client()
        self.bus = bus or get_event_bus()
        self.store = store or get_store()

    async def execute(self, brief: CampaignBrief, run_id: str | None = None) -> PipelineRun:
        run_id = run_id or str(uuid.uuid4())
        run = PipelineRun(run_id=run_id, brief=brief, status="running")
        start_time = asyncio.get_event_loop().time()

        await self._emit(run_id, AgentStatus.RUNNING, "Pipeline initialized.")
        log.info("pipeline_start", run_id=run_id, brand=brief.brand)

        try:
            # ── Stage 0: memory retrieval ──────────────────────────────
            similar = await self.store.retrieve_similar(brief)
            context: dict = {"similar_past_runs": similar}
            if similar:
                await self._emit(
                    run_id, AgentStatus.RUNNING,
                    f"Retrieved {len(similar)} similar past campaigns from memory.",
                )

            # ── Stage 1: parallel independent agents ──────────────────
            await self._emit(
                run_id, AgentStatus.RUNNING,
                "Dispatching 3 agents in parallel: Trend, Audience, Creative.",
            )
            trend = TrendAgent(self.llm, self.bus, run_id)
            audience = AudienceAgent(self.llm, self.bus, run_id)
            creative = CreativeAgent(self.llm, self.bus, run_id)

            t_res, a_res, c_res = await asyncio.gather(
                trend.run(brief, context),
                audience.run(brief, context),
                creative.run(brief, context),
            )
            run.trend_intelligence = t_res.output if t_res.success else None
            run.audience_psychology = a_res.output if a_res.success else None
            run.creative_strategy = c_res.output if c_res.success else None
            run.total_tokens += t_res.tokens_used + a_res.tokens_used + c_res.tokens_used

            # ── Stage 2: scoring (depends on creative) ─────────────────
            if c_res.success:
                await self._emit(
                    run_id, AgentStatus.RUNNING, "Stage 2: Evaluating creative concepts."
                )
                scoring = ScoringAgent(self.llm, self.bus, run_id)
                s_res = await scoring.run(brief, {
                    "creative_output": run.creative_strategy,
                    "trend_output": run.trend_intelligence,
                    "audience_output": run.audience_psychology,
                })
                run.evaluation = s_res.output if s_res.success else None
                run.total_tokens += s_res.tokens_used
            else:
                await self._emit(
                    run_id, AgentStatus.RUNNING,
                    "Skipping scoring — no creative concepts to evaluate.",
                )

            # ── Stage 3: supervisor synthesis ──────────────────────────
            await self._emit(
                run_id, AgentStatus.RUNNING, "Stage 3: Supervisor cross-agent synthesis."
            )
            supervisor = SupervisorAgent(self.llm, self.bus, run_id)
            sup_res = await supervisor.run(brief, {
                "trend_output": run.trend_intelligence,
                "audience_output": run.audience_psychology,
                "creative_output": run.creative_strategy,
                "evaluation_output": run.evaluation,
            })
            run.final_brief = sup_res.output if sup_res.success else None
            run.total_tokens += sup_res.tokens_used

            # ── Finalize + persist ─────────────────────────────────────
            run.total_latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            run.status = "completed" if sup_res.success else "failed"
            await self.store.save_run(run)

            await self._emit(
                run_id,
                AgentStatus.COMPLETED if run.status == "completed" else AgentStatus.FAILED,
                f"Pipeline complete. Total tokens: {run.total_tokens}. "
                f"Latency: {run.total_latency_ms}ms.",
            )
            log.info("pipeline_complete", run_id=run_id, status=run.status,
                     total_tokens=run.total_tokens, latency_ms=run.total_latency_ms)
            return run

        except Exception as e:
            log.exception("pipeline_failed", run_id=run_id, error=str(e))
            run.status = "failed"
            run.total_latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            try:
                await self.store.save_run(run)
            except Exception:
                log.exception("run_save_failed", run_id=run_id)
            await self._emit(run_id, AgentStatus.FAILED, f"Pipeline failed: {e}", error=str(e))
            return run

    async def _emit(self, run_id: str, status: AgentStatus,
                    thought: str, error: str | None = None) -> None:
        await self.bus.publish(run_id, AgentEvent(
            agent_name="__pipeline__",
            status=status,
            thought=thought,
            error=error,
        ))


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
