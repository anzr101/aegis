"""API routes — thin layer: validate input, delegate to the orchestrator/store.

POST /api/pipeline/run          — kick off a pipeline (returns run_id immediately)
GET  /api/pipeline/{id}/stream  — SSE stream of live agent events
GET  /api/pipeline/{id}         — final result of a run
GET  /api/pipeline/history/list — recent runs
GET  /api/health                — liveness check
"""
import asyncio
import uuid

import structlog
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.studio import router as studio_router
from app.core.config import get_settings
from app.db.store import get_store
from app.schemas import CampaignBrief
from app.services.event_bus import get_event_bus
from app.services.orchestrator import get_orchestrator

log = structlog.get_logger()
router = APIRouter()
router.include_router(studio_router)  # /run, /runs — the 3D studio frontend

# In-process job table. One process handles a whole run, so this is enough;
# a job queue becomes necessary only with multiple API replicas.
_jobs: dict[str, asyncio.Task] = {}


@router.get("/health")
async def health():
    settings = get_settings()
    live = bool(settings.anthropic_api_key)
    return {
        "status": "ok",
        "service": "aegis",
        "mode": "LIVE" if live else "DEMO",
        "model": settings.operational_model if live else None,
    }


@router.post("/pipeline/run")
async def run_pipeline(brief: CampaignBrief):
    """Start a pipeline in the background and return its run_id immediately.
    The client subscribes to /pipeline/{run_id}/stream for live updates."""
    run_id = str(uuid.uuid4())
    task = asyncio.create_task(get_orchestrator().execute(brief, run_id))
    _jobs[run_id] = task
    task.add_done_callback(lambda _: _jobs.pop(run_id, None))
    return {"run_id": run_id, "status": "started"}


@router.get("/pipeline/{run_id}/stream")
async def stream_pipeline(run_id: str):
    """Server-Sent Events stream of agent events for a run."""
    bus = get_event_bus()

    async def event_generator():
        try:
            async for event in bus.subscribe(run_id):
                yield {"event": "agent_event", "data": event.model_dump_json()}
        except asyncio.CancelledError:
            log.info("sse_disconnected", run_id=run_id)
            raise

    return EventSourceResponse(event_generator())


@router.get("/pipeline/history/list")
async def list_history(limit: int = 50):
    """Recent pipeline runs (registered before the {run_id} route so
    'history' is not captured as a run_id)."""
    return {"runs": await get_store().list_recent(limit)}


@router.get("/pipeline/{run_id}")
async def get_pipeline(run_id: str):
    """Final result of a completed run."""
    run = await get_store().get_run(run_id)
    if not run:
        if run_id in _jobs and not _jobs[run_id].done():
            return {"status": "running", "run_id": run_id}
        raise HTTPException(404, f"Run {run_id} not found")
    return run
