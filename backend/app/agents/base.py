"""BaseAgent — abstract base class for all five reasoning agents.

A concrete agent supplies three things:
  - system_prompt      (its expertise + instructions)
  - output_schema      (the Pydantic model its JSON reply must match)
  - build_user_message (how the brief + context become the user message)

The base provides everything else: event publishing to the SSE bus, the
LLM call (with retries handled inside LLMClient), token/latency tracking,
and error capture — a failed agent returns AgentResult(success=False)
instead of raising, so the orchestrator keeps the other agents running.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Type

import structlog
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas import AgentEvent, AgentStatus, CampaignBrief
from app.services.event_bus import EventBus
from app.services.llm import LLMClient, LLMResult

log = structlog.get_logger()


class AgentResult(BaseModel):
    agent_name: str
    output: Any
    tokens_used: int
    latency_ms: int
    success: bool
    error: str | None = None


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""
    use_web_search: bool = False
    max_tokens: int = 4096

    def __init__(self, llm: LLMClient, bus: EventBus, run_id: str):
        self.llm = llm
        self.bus = bus
        self.run_id = run_id

    @property
    def model_override(self) -> str | None:
        """None → the default operational model. The supervisor overrides this."""
        return None

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        ...

    @abstractmethod
    def build_user_message(self, brief: CampaignBrief, context: dict[str, Any]) -> str:
        ...

    async def emit(self, status: AgentStatus, thought: str | None = None,
                   tokens: int | None = None, latency: int | None = None,
                   error: str | None = None) -> None:
        await self.bus.publish(self.run_id, AgentEvent(
            agent_name=self.name,
            status=status,
            thought=thought,
            tokens_used=tokens,
            latency_ms=latency,
            error=error,
        ))

    async def run(self, brief: CampaignBrief, context: dict[str, Any]) -> AgentResult:
        await self.emit(AgentStatus.RUNNING, thought=f"{self.description} — starting...")
        try:
            user_msg = self.build_user_message(brief, context)

            if self.use_web_search and get_settings().enable_web_search:
                await self.emit(
                    AgentStatus.RUNNING,
                    thought="Searching the live web for current signals...",
                )
                result: LLMResult = await self.llm.call_with_web_search(
                    system=self.system_prompt,
                    user=user_msg,
                    output_model=self.output_schema,
                    model=self.model_override,
                    max_tokens=self.max_tokens,
                )
            else:
                result = await self.llm.structured_call(
                    system=self.system_prompt,
                    user=user_msg,
                    output_model=self.output_schema,
                    model=self.model_override,
                    max_tokens=self.max_tokens,
                )

            await self.emit(
                AgentStatus.COMPLETED,
                thought=f"{self.description} — synthesis complete.",
                tokens=result.tokens_used,
                latency=result.latency_ms,
            )
            return AgentResult(
                agent_name=self.name,
                output=result.parsed,
                tokens_used=result.tokens_used,
                latency_ms=result.latency_ms,
                success=True,
            )

        except asyncio.CancelledError:
            await self.emit(AgentStatus.FAILED, error="cancelled")
            raise
        except Exception as e:
            log.exception("agent_failed", agent=self.name, error=str(e))
            await self.emit(AgentStatus.FAILED, error=str(e))
            return AgentResult(
                agent_name=self.name,
                output=None,
                tokens_used=0,
                latency_ms=0,
                success=False,
                error=str(e),
            )
