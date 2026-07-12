"""
AEGIS — FastAPI application.

Serves the single-page frontend, exposes the SSE pipeline endpoint, run
history, and brief export. Backend + frontend ship as one process so the whole
product runs with a single command and no build step.
"""
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from . import config, database, export, orchestrator

app = FastAPI(title=f"{config.APP_NAME} · {config.AGENCY}")

FRONTEND_DIR = config.BASE_DIR / "frontend"


@app.on_event("startup")
def _startup():
    database.init_db()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": config.mode_label(),
        "model": config.MODEL if config.LIVE_MODE else None,
        "agency": config.AGENCY,
    }


@app.post("/api/run")
async def start_run(request: Request):
    """Kick off a pipeline run. Returns an SSE stream of agent events."""
    brief = await request.json()
    run_id = uuid.uuid4().hex[:12]

    async def event_source():
        async for evt in orchestrator.run_pipeline(run_id, brief):
            yield evt

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/runs")
def runs():
    return JSONResponse(database.list_runs())


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    run = database.get_run(run_id)
    if not run:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(run)


@app.get("/api/runs/{run_id}/export.md")
def export_md(run_id: str):
    run = database.get_run(run_id)
    if not run:
        return JSONResponse({"error": "not found"}, status_code=404)
    md = export.build_markdown(run)
    brand = (run["brief"].get("brand") or "campaign").replace(" ", "_")
    return PlainTextResponse(
        md,
        headers={"Content-Disposition": f'attachment; filename="{brand}_brief.md"'},
        media_type="text/markdown",
    )


# ---- Frontend ----
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
