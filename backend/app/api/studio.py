"""Routes for the AEGIS studio frontend (the 3D single-page app).

Contract (fixed by frontend/app.js):
  GET  /api/health                — extended with {mode, model} by main routes
  POST /api/run                   — start a pipeline; SSE streamed in the response
  GET  /api/runs                  — history list
  GET  /api/runs/{id}             — one run with per-agent markdown outputs
  GET  /api/runs/{id}/export.md   — the whole brief as a markdown document

SSE events emitted: run_started, agent_started, agent_chunk, agent_done,
agent_error, run_complete. Agent "chunks" arrive as one markdown block per
agent on completion (the pipeline computes structured JSON, not tokens).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.store import get_store
from app.schemas import AgentStatus, CampaignBrief
from app.services.event_bus import get_event_bus
from app.services.markdown import render_agent_output
from app.services.orchestrator import get_orchestrator

router = APIRouter()

# Order matches pipeline stages; icons are the section numbers in the UI.
AGENTS_META = [
    {"id": "trend_agent", "name": "Trend Intelligence", "role": "Live market & cultural signals", "icon": "01"},
    {"id": "audience_agent", "name": "Audience Psychology", "role": "9-axis behavioral profile", "icon": "02"},
    {"id": "creative_agent", "name": "Creative Strategy", "role": "3 distinct campaign concepts", "icon": "03"},
    {"id": "scoring_agent", "name": "Evaluation Engine", "role": "8-dimension scoring & self-critique", "icon": "04"},
    {"id": "supervisor", "name": "Supervisor", "role": "Conflict resolution & final brief", "icon": "05"},
]


class StudioBrief(BaseModel):
    """The studio form's free-text brief."""
    brand: str = ""
    product: str = ""
    goal: str = ""
    audience: str = ""
    market: str = ""
    budget: str = ""
    timeline: str = ""
    notes: str = ""

    def to_campaign_brief(self) -> CampaignBrief:
        extra = "; ".join(
            p for p in (
                f"Budget: {self.budget}" if self.budget else "",
                f"Timeline: {self.timeline}" if self.timeline else "",
                self.notes,
            ) if p
        )
        return CampaignBrief(
            brand=self.brand or self.product or "Untitled",
            industry=self.product or self.brand or "general",
            product_or_service=self.product or self.brand or "unspecified",
            campaign_goal=self.goal or "Build awareness and engagement",
            target_audience=self.audience or "General consumers",
            geographic_focus=self.market or "India",
            extra_context=extra or None,
        )


def _mode() -> str:
    return "LIVE" if get_settings().anthropic_api_key else "DEMO"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/run")
async def run(brief: StudioBrief):
    campaign = brief.to_campaign_brief()
    run_id = str(uuid.uuid4())
    bus = get_event_bus()

    async def stream():
        # Subscribe BEFORE the pipeline starts so no event is missed.
        subscription = bus.subscribe(run_id)
        yield _sse("run_started", {"run_id": run_id, "mode": _mode(), "agents": AGENTS_META})

        task = asyncio.create_task(get_orchestrator().execute(campaign, run_id))
        started: set[str] = set()
        try:
            async for ev in subscription:
                aid = ev.agent_name
                if aid == "__pipeline__":
                    continue  # terminal pipeline event ends the subscription loop
                if ev.status == AgentStatus.RUNNING and aid not in started:
                    started.add(aid)
                    meta = next((a for a in AGENTS_META if a["id"] == aid), None)
                    yield _sse("agent_started", {"id": aid, "name": meta["name"] if meta else aid})
                elif ev.status == AgentStatus.COMPLETED:
                    yield _sse("agent_chunk", {"id": aid, "text": render_agent_output(aid, ev.output)})
                    yield _sse("agent_done", {"id": aid})
                elif ev.status == AgentStatus.FAILED:
                    yield _sse("agent_error", {"id": aid, "error": ev.error or "failed"})
            yield _sse("run_complete", {"run_id": run_id})
        finally:
            if not task.done():
                await task

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


_AGENT_OUTPUT_KEYS = {
    "trend_agent": "trend_intelligence",
    "audience_agent": "audience_psychology",
    "creative_agent": "creative_strategy",
    "scoring_agent": "evaluation",
    "supervisor": "final_brief",
}


def _epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp())


def _outputs_from_run(full_run: dict) -> dict[str, str]:
    return {
        aid: render_agent_output(aid, full_run.get(key))
        for aid, key in _AGENT_OUTPUT_KEYS.items()
    }


@router.get("/runs")
async def list_runs(limit: int = 30):
    rows = await get_store().list_recent(limit)
    return [
        {
            "id": r["run_id"],
            "brief": {"brand": r["brand"], "product": r["industry"]},
            "mode": _mode(),
            "status": r["status"],
            "created_at": _epoch(r["created_at"]),
        }
        for r in rows
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    full = await get_store().get_run(run_id)
    if not full:
        raise HTTPException(404, "Run not found")
    return {
        "id": run_id,
        "brief": {"brand": full["brief"].get("brand"), "product": full["brief"].get("product_or_service")},
        "outputs": _outputs_from_run(full),
        "mode": _mode(),
        "status": full.get("status"),
        "created_at": _epoch(full["created_at"]),
    }


@router.get("/runs/{run_id}/export.md")
async def export_md(run_id: str):
    full = await get_store().get_run(run_id)
    if not full:
        raise HTTPException(404, "Run not found")
    brief = full.get("brief", {})
    head = (
        f"# AEGIS Campaign Brief — {brief.get('brand', 'Untitled')}\n\n"
        f"*Goal:* {brief.get('campaign_goal', '—')}  \n"
        f"*Audience:* {brief.get('target_audience', '—')}  \n"
        f"*Market:* {brief.get('geographic_focus', '—')}  \n"
        f"*Generated:* {full.get('created_at', '')}\n\n---\n\n"
    )
    body = "\n\n---\n\n".join(_outputs_from_run(full).values())
    return PlainTextResponse(head + body, media_type="text/markdown; charset=utf-8")
