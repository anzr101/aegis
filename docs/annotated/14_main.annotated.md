# Annotated: `main.py` — the FastAPI application

The top of the stack. Builds the app, wires up the SSE run endpoint, run-history
and export routes, and serves the build-free frontend from the same process.

**Data flow:** `uvicorn backend.main:app` imports `app`. On startup the DB is
initialised. Requests hit `/api/*` handlers (which call `orchestrator`,
`database`, `export`); everything else is served as a static frontend file.

```python
1-7   """AEGIS — FastAPI application. Serves the SPA, the SSE pipeline endpoint, run
       history, and brief export. Backend + frontend ship as one process."""
8   import uuid

10  from fastapi import FastAPI, Request
11-17 from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                                     PlainTextResponse, StreamingResponse)
18  from fastapi.staticfiles import StaticFiles

20  from . import config, database, export, orchestrator   # the whole backend, wired here

22  app = FastAPI(title=f"{config.APP_NAME} · {config.AGENCY}")   # "AEGIS · Ezor Media"

24  FRONTEND_DIR = config.BASE_DIR / "frontend"                   # where index.html + assets live
```
- One `FastAPI` instance. `FRONTEND_DIR` is resolved from `config.BASE_DIR`, so
  the app finds the frontend regardless of the working directory it's launched
  from.

```python
27  @app.on_event("startup")
28  def _startup():
29      database.init_db()          # ensure the runs table exists before any request
```
- Startup hook: creates the SQLite schema once when the server boots. (`config.py`
  already created the `data/` directory at import.)

```python
32  @app.get("/api/health")
33  def health():
34      return {
35          "status": "ok",
36          "mode":   config.mode_label(),                    # "DEMO" | "LIVE"
37          "model":  config.MODEL if config.LIVE_MODE else None,  # hide model name in DEMO
38          "agency": config.AGENCY,
39      }
```
- Liveness + config echo. The frontend reads this on load to render the DEMO/LIVE
  pill in the top-right. `model` is `None` in DEMO so the UI doesn't imply a model
  is in use.

```python
42  @app.post("/api/run")
43  async def start_run(request: Request):
44      """Kick off a pipeline run. Returns an SSE stream of agent events."""
45      brief   = await request.json()          # the client brief posted from the form
46      run_id  = uuid.uuid4().hex[:12]         # short unique id for this run

48      async def event_source():
49          async for evt in orchestrator.run_pipeline(run_id, brief):
50              yield evt                        # forward each SSE frame verbatim

52      return StreamingResponse(
53          event_source(),
54          media_type="text/event-stream",      # the SSE content type
55          headers={
56              "Cache-Control":    "no-cache",  # never cache a live stream
57              "Connection":       "keep-alive",
58              "X-Accel-Buffering":"no",        # tell nginx/proxies NOT to buffer → tokens flow live
59          },
60      )
```
- **The core endpoint.** Reads the brief, mints a 12-char `run_id`, and returns a
  `StreamingResponse` whose body is the orchestrator's SSE generator.
- **Lines 48–50:** the inner `event_source` is a thin pass-through — the
  orchestrator already yields fully-formatted SSE frames, so `main` just relays
  them.
- **Lines 54–59 matter a lot for behaviour:** `text/event-stream` is what makes
  the browser treat this as SSE; `no-cache` + `X-Accel-Buffering: no` stop
  intermediaries from buffering, which is what lets tokens arrive incrementally
  rather than all at the end.

```python
63  @app.get("/api/runs")
64  def runs():
65      return JSONResponse(database.list_runs())      # history list (newest first)

68  @app.get("/api/runs/{run_id}")
69  def run_detail(run_id: str):
70      run = database.get_run(run_id)
71      if not run:
72          return JSONResponse({"error": "not found"}, status_code=404)
73      return JSONResponse(run)                        # full stored run (brief + outputs)
```
- History endpoints. `list_runs` powers the History panel; `run_detail` reopens a
  past run (returns 404 when `get_run` yields `None`).

```python
76  @app.get("/api/runs/{run_id}/export.md")
77  def export_md(run_id: str):
78      run = database.get_run(run_id)
79      if not run:
80          return JSONResponse({"error": "not found"}, status_code=404)
81      md    = export.build_markdown(run)                        # assemble the brief
82      brand = (run["brief"].get("brand") or "campaign").replace(" ", "_")  # safe filename stem
83      return PlainTextResponse(
84          md,
85          headers={"Content-Disposition": f'attachment; filename="{brand}_brief.md"'},  # force download
86          media_type="text/markdown",
87      )
```
- Export endpoint. Loads the run, calls `export.build_markdown`, and returns it as
  a **downloadable** file: the `Content-Disposition: attachment` header plus a
  brand-derived filename (`Acme_Co` → `Acme_Co_brief.md`). Blank brand falls back
  to `campaign`.

```python
90  # ---- Frontend ----
91  @app.get("/", response_class=HTMLResponse)
92  def index():
93      return FileResponse(FRONTEND_DIR / "index.html")   # explicit route for the root page

96  app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")  # everything else → static files
```
- **Serving the single-page app from one process.** `index()` serves
  `index.html` at `/`; the `StaticFiles` mount at `/` serves `styles.css`,
  `app.js`, `scene.js`, and any other asset by path.
- **Order matters:** the explicit `@app.get("/")` is declared *before* the mount,
  and all `/api/*` routes are declared above it, so the catch-all static mount
  never shadows the API or the root handler. This is the one-command,
  no-build-step deployment the README promises.
