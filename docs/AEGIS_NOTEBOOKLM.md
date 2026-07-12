# AEGIS — Complete Technical Source Document

> A single, self-contained deep-dive into the AEGIS backend: what it is, how it
> is built, how data flows through it, and every file and function explained.
> This document is written to stand on its own — you can read it top to bottom
> without opening the code, or feed it to a notebook/knowledge tool as one
> source and ask questions of it.

---

## 1. What AEGIS is, in one paragraph

AEGIS is a **campaign-intelligence platform built for Ezor Media**, a Mumbai
marketing and modeling agency. It takes a single **client brief** (brand,
product, goal, audience, market, budget, timeline, notes) and turns it into a
**finished, downloadable campaign strategy**. It does this by running **five
specialised AI agents in a fixed sequence** — Research, Competitor, Strategy,
Creative, and Media & Budget — where each agent's output is fed forward as
context to the next, so later agents build on the work of earlier ones. The
whole product is a **single Python (FastAPI) process** that serves both the API
and a build-free web frontend. Output streams to the browser token-by-token
over **Server-Sent Events (SSE)**, every run is saved to **SQLite**, and any run
can be exported as a **Markdown brief**.

---

## 2. The two runtime modes (the most important design idea)

AEGIS always runs in one of two modes, chosen automatically at startup:

- **DEMO mode** — the default when no API key is present. The five agents return
  **realistic, brief-adaptive canned copy** (written into the code) that is
  streamed to the browser word-by-word so it *reads* like a live AI thinking.
  DEMO mode needs no credentials, no network, and cannot fail on a fresh
  machine. It exists so the product always works for a demo.
- **LIVE mode** — active when a real Anthropic API key (starting with `sk-`) is
  present. The same five agents now call **Claude** (Anthropic's model, default
  `claude-sonnet-4-6`) and stream genuine AI output.

The crucial property: **DEMO and LIVE run the exact same pipeline, the exact
same UI, the exact same streaming, persistence, and export.** The *only*
difference is where each agent's text comes from. This is decided in one place
(`config.LIVE_MODE`) and branched in one place (`orchestrator._stream_agent_text`).

Why this matters: it means the product can be demonstrated, deployed, and
developed with zero setup, and "going live" is a single environment variable —
no code path diverges, so nothing new can break when the key is added.

---

## 3. Glossary (terms used throughout)

- **Brief** — the input: a dict of brand, product, goal, audience, market,
  budget, timeline, notes. Comes from the frontend form as JSON.
- **Agent** — one specialised step in the pipeline. Five of them, run in order.
  Each has an `id`, display `name`, one-line `role`, an `icon` (a number
  string like "01"), and a prompt builder.
- **Pipeline / run** — one execution of all five agents for one brief. Has a
  unique `run_id` (12 hex chars) and is persisted.
- **Context** — the accumulated outputs of all agents that have finished so far
  in the current run. Passed into each subsequent agent's prompt.
- **SSE (Server-Sent Events)** — a one-way HTTP streaming protocol. The server
  keeps the connection open and pushes named events; the browser consumes them
  as they arrive. AEGIS uses this to drive the live "relay" animation.
- **Mode** — DEMO or LIVE (see section 2).

---

## 4. Folder and file map

```
aegis-ezor/
├── run.sh / run.bat            one-command setup + launch (venv → deps → uvicorn)
├── docker-compose.yml          dev container (port 8000)
├── docker-compose.prod.yml     production container (port 80, reads .env file)
├── Dockerfile                  python:3.11-slim image, runs uvicorn
├── requirements.txt            fastapi, uvicorn, anthropic, python-dotenv
├── .env / .env.example         config (API key, model, pacing) — .env is git-ignored
├── .gitignore
│
├── backend/                    ← the application (all Python)
│   ├── __init__.py             package marker + one-line title
│   ├── config.py               env → DEMO/LIVE decision, paths, pacing constants
│   ├── agents.py               the 5-agent roster + prompt builder (shared context)
│   ├── demo_data.py            brief-adaptive canned output (DEMO text source)
│   ├── claude_client.py        Anthropic streaming + retries (LIVE text source)
│   ├── orchestrator.py         runs agents in sequence, emits SSE events, feeds context
│   ├── database.py             SQLite: create / finalize / get / list runs
│   ├── export.py               assemble a finished run into a Markdown brief
│   └── main.py                 FastAPI app: SSE endpoint, history, export, serves frontend
│
├── frontend/                   vanilla, build-free (NOT the subject of this doc)
│   ├── index.html              single-page interface
│   ├── styles.css              editorial aesthetic
│   ├── app.js                  SSE client, live relay, Markdown renderer
│   └── scene.js                3D background (three.js)
│
├── deploy/aws/                 one-command EC2 deployment
│   └── deploy.py               creates infra, uploads app, starts container
│
├── docs/annotated/             line-by-line annotation of every backend file
└── data/                       SQLite DB (created at runtime; git-ignored)
```

**Layer responsibilities:**

| Layer | Files | Responsibility |
|---|---|---|
| Config | `config.py` | Decide mode, resolve paths, expose constants |
| Domain | `agents.py`, `demo_data.py` | Define the agents and their prompts / demo text |
| Model I/O | `claude_client.py` | Talk to the Anthropic API (LIVE only) |
| Orchestration | `orchestrator.py` | Run the pipeline, stream SSE, thread context |
| Persistence | `database.py` | Save and read runs (SQLite) |
| Presentation | `export.py`, `main.py` | Markdown export + HTTP/SSE surface + serve UI |

---

## 5. The dependency graph (who imports whom)

```
main.py
 ├── config        (mode label, paths)
 ├── database      (init, list, get)
 ├── export        (build markdown)  ──► agents (roster for section order)
 └── orchestrator
      ├── agents        (roster + prompt builder)
      ├── config        (mode, pacing)
      ├── database      (create + finalize run)
      ├── demo_data     (DEMO text)          [used in DEMO mode]
      └── claude_client (LIVE streaming)     [imported lazily, LIVE mode only]

config.py  ── standalone (only reads env + filesystem)
agents.py  ── standalone (pure prompt strings)
demo_data.py ── standalone (pure text templates)
claude_client.py ── imports config; imports `anthropic` lazily inside the function
database.py ── imports config (for DB path)
export.py  ── imports agents (to order the sections)
```

Two deliberate choices here:

1. **`claude_client` and `anthropic` are imported lazily** — only when an agent
   actually runs in LIVE mode. So the `anthropic` package being missing or the
   key being absent can never break DEMO mode or app startup.
2. **`config` is the only module that touches the environment.** Everyone else
   reads decisions from `config`, so mode logic lives in exactly one place.

---

## 6. Every file, every function — explained

### 6.1 `backend/__init__.py`
A one-line package marker with the docstring
`"AEGIS — Campaign Intelligence for Ezor Media."`. Its only job is to make
`backend/` an importable Python package.

---

### 6.2 `backend/config.py` — configuration and mode detection

This module runs top-to-bottom at import time and computes global constants.

- **`load_dotenv(...)`** (in a `try/except`) — loads a local `.env` file if
  `python-dotenv` is installed. Wrapped in a bare `except` so the app still runs
  if the package is missing (e.g. the environment already has the vars set).
- **`BASE_DIR`** — the project root (parent of `backend/`).
- **`DATA_DIR`** — `BASE_DIR/data`, created with `mkdir(exist_ok=True)` so the
  SQLite folder always exists.
- **`DB_PATH`** — `DATA_DIR/aegis.db`, the SQLite file location.
- **`ANTHROPIC_API_KEY`** — read from env, stripped. Empty string if unset.
- **`MODEL`** — from `AEGIS_MODEL` env, default `claude-sonnet-4-6`.
- **`LIVE_MODE`** — `True` only if the key is non-empty **and** starts with
  `sk-`. This single boolean is what every other module reads to decide DEMO vs
  LIVE. A blank or malformed key silently degrades to DEMO instead of crashing.
- **`APP_NAME`, `APP_TAGLINE`, `AGENCY`** — display strings ("AEGIS",
  "Campaign Intelligence", "Ezor Media").
- **`DEMO_CHUNK_DELAY`** (default 0.012s) and **`DEMO_AGENT_PAUSE`** (default
  0.35s) — pacing in seconds used only in DEMO mode so the streamed text reads
  as genuine "thinking" rather than appearing instantly.
- **`mode_label() -> str`** — returns `"LIVE"` or `"DEMO"`; used in the health
  endpoint, the run record, and the UI pill.

---

### 6.3 `backend/agents.py` — the agent roster and prompt builder

This is the "brain wiring": it defines who the five agents are and exactly what
each is asked to produce.

- **`EZOR_CONTEXT`** (constant) — a shared system-style preamble injected into
  every agent prompt. It tells the model it is an agent inside AEGIS working for
  Ezor Media, describes the house voice (premium, editorial, confident — not
  generic growth-hack copy), and stresses Indian-market specifics (festive
  calendars, regional languages, tier-1/2 city behaviour, INR budgets).
- **`_brief_block(brief) -> str`** — formats the incoming brief dict into a
  labelled `CLIENT BRIEF` block (Brand, Product, Goal, Audience, Market, Budget,
  Timeline, Notes), filling `N/A`/defaults for missing fields.
- **`_prior(context) -> str`** — turns the accumulated prior-agent outputs into
  `### <Agent Name>` sections joined together, or an empty string if this is the
  first agent. This is the mechanism that feeds each agent the work of the ones
  before it.
- **`AGENTS`** (list of dicts) — the ordered roster. Each entry has `id`,
  `name`, `role`, `icon`:
  1. `research` — "Research" — Audience, market & cultural signals — icon 01
  2. `competitor` — "Competitor" — Positioning gaps & rival activity — icon 02
  3. `strategy` — "Strategy" — Campaign concept, pillars & KPIs — icon 03
  4. `creative` — "Creative" — Hooks, copy & content calendar — icon 04
  5. `media` — "Media & Budget" — Channel mix & spend allocation — icon 05
  The order of this list **is** the pipeline order.
- **`build_prompt(agent_id, brief, context) -> str`** — assembles the full
  prompt for one agent by concatenating: `EZOR_CONTEXT` + the brief block + (if
  any) the prior-agents block + a per-agent instruction. The per-agent
  instructions live in a dict inside this function and specify exactly what each
  agent must output and in what format:
  - **research**: 2–3 audience segments with one-line personas, 3–4 cultural
    signals, single biggest opportunity + risk. Markdown, under ~350 words.
  - **competitor**: 3 competitor archetypes and what each owns, 2 positioning
    gaps Ezor can take, one white-space angle. Markdown, under ~300 words.
  - **strategy**: a campaign big idea (line + 2-sentence rationale), 3 messaging
    pillars, primary + 2 secondary KPIs with target ranges. Under ~320 words.
  - **creative**: 3 hooks/taglines, sample ad copy for one hero asset
    (headline + 2-line body + CTA), and a 2-week content calendar as a compact
    Markdown table (Day | Platform | Format | Theme). Under ~380 words.
  - **media**: a channel-mix Markdown table (Channel | % of budget | Why)
    summing to 100%, conversion of percentages to amounts using the brief's
    budget, a one-line projected outcome, and one line on measurement cadence.
    Under ~320 words.
  Every instruction ends with "Write only the deliverable. No preamble" so the
  model returns clean, presentable content with no "Sure, here is…".

---

### 6.4 `backend/demo_data.py` — DEMO-mode text source

Provides the canned-but-realistic output used when there is no API key.

- **`_g(brief, key, default) -> str`** — small helper: return the brief's value
  for `key` if present and non-empty, otherwise the default. Used to interpolate
  real brief details into the templates.
- **`demo_output(agent_id, brief) -> str`** — returns a fully written,
  brand-interpolated deliverable for the given agent. It pulls brand, product,
  audience, market, goal, and budget from the brief (with sensible defaults) and
  drops them into a hand-written template per agent (market read + segments +
  signals for research; a competitor table + gaps for competitor; big idea +
  pillars + KPIs for strategy; hooks + hero asset + a two-week content-calendar
  table for creative; a channel-mix table + projected outcome + measurement
  cadence for media). If an unknown `agent_id` is passed, it returns a clear
  placeholder string. Because the brief values are interpolated, the DEMO output
  changes with each brief and looks like genuine work.

---

### 6.5 `backend/claude_client.py` — LIVE-mode text source

A thin, resilient async wrapper over the Anthropic streaming API. Imported only
in LIVE mode.

- **`stream_completion(prompt, max_retries=3) -> AsyncIterator[str]`** — an
  async generator that yields text chunks from Claude as they stream in. It:
  1. Lazily imports `AsyncAnthropic` (so a missing package can't break DEMO).
  2. Builds a client with the configured API key.
  3. Opens a streaming message request (`model=config.MODEL`,
     `max_tokens=1400`, the single user prompt) and yields each text delta from
     `stream.text_stream`.
  4. On any exception, retries with a short backoff (`0.8 * attempt` seconds).
     After `max_retries` attempts it raises a clean `RuntimeError` describing
     the failure — which the orchestrator catches per-agent.
  The retry loop makes transient network/API blips self-healing without the
  caller knowing.

---

### 6.6 `backend/orchestrator.py` — the pipeline engine

This is the heart of the system: it runs the five agents in order, streams SSE
events, threads context forward, and isolates failures.

- **`_sse(event, data) -> str`** — formats a Python dict into the raw SSE wire
  format: `event: <name>\ndata: <json>\n\n`. Every event the frontend receives
  is produced here.
- **`_stream_agent_text(agent_id, brief, context) -> AsyncIterator[str]`** —
  the single branch point between the two modes:
  - In **LIVE mode**: builds the prompt via `agents.build_prompt`, lazily
    imports `claude_client`, and yields chunks straight from Claude.
  - In **DEMO mode**: gets the full text from `demo_data.demo_output`, then
    yields it **three words at a time** with a `DEMO_CHUNK_DELAY` sleep between
    batches, so the browser sees a realistic streaming effect.
  This is the only place that knows about the two text sources — everything
  above it is mode-agnostic.
- **`run_pipeline(run_id, brief) -> AsyncIterator[str]`** — the top-level
  generator the HTTP endpoint consumes. Its sequence:
  1. Determine `mode`, create the run row in SQLite (`database.create_run`).
  2. Emit **`run_started`** with the run id, mode, and the full agent roster
     (so the UI can draw all five lanes up front).
  3. For **each agent in order**:
     - Emit **`agent_started`** (id + name).
     - In DEMO mode, pause `DEMO_AGENT_PAUSE` for pacing (no pause in LIVE).
     - Stream the agent's text: for every chunk, append to a buffer and emit an
       **`agent_chunk`** (id + text) so the browser renders it live.
     - On success: store the full text in `outputs[id]`, add it to `context`
       under the agent's display name (so the *next* agent sees it), and emit
       **`agent_done`**.
     - On **any exception**: store an inline error note in `outputs[id]` and
       emit **`agent_error`** — but **do not stop the loop**. A single failing
       agent never wastes the whole run; the pipeline continues with the rest.
  4. After all agents: `database.finalize_run` writes the outputs and marks the
     run `complete`, then emit **`run_complete`** with the run id and the full
     outputs map.
  The per-agent try/except plus context-threading are the two defining
  behaviours: **resilient** (one agent can fail) and **compounding** (each agent
  builds on the last).

---

### 6.7 `backend/database.py` — SQLite persistence

Standard-library `sqlite3` only; no ORM, no extra dependency.

- **`_conn()`** (context manager) — opens a connection to `config.DB_PATH`, sets
  `row_factory` to `sqlite3.Row` (so rows read like dicts), commits on success,
  and always closes. Every DB call goes through this.
- **`init_db()`** — creates the `runs` table if it doesn't exist. Schema:
  `id TEXT PRIMARY KEY`, `created_at REAL`, `mode TEXT`, `brief TEXT` (JSON),
  `outputs TEXT` (JSON), `status TEXT`. Called once at app startup.
- **`create_run(run_id, brief, mode)`** — inserts a new row at the start of a
  run with the brief serialized to JSON, empty outputs, and status `running`.
  Uses `INSERT OR REPLACE` so a re-used id overwrites cleanly.
- **`finalize_run(run_id, outputs, status="complete")`** — updates the row with
  the final outputs (JSON) and status once the pipeline finishes.
- **`get_run(run_id) -> dict | None`** — fetches one run by id, or `None`.
- **`list_runs(limit=50) -> list`** — returns recent runs newest-first, for the
  history drawer.
- **`_row_to_dict(row) -> dict`** — converts a `sqlite3.Row` back into a plain
  dict, JSON-decoding the `brief` and `outputs` fields.

The `brief` and `outputs` are stored as JSON text inside single columns — simple
and sufficient for this scale, and it keeps the schema trivial.

---

### 6.8 `backend/export.py` — Markdown brief assembly

- **`build_markdown(run) -> str`** — turns a finished run into a single
  downloadable Markdown document. It writes a title with the brand, a metadata
  line (prepared by AEGIS · Ezor Media · timestamp · mode), a **Brief** section
  echoing the inputs, then iterates `agents.AGENTS` **in order** and appends each
  agent's section (`## <icon> · <name> — <role>` followed by that agent's
  output, or "_No output._" if missing), separated by horizontal rules, and a
  closing signature line. Iterating the shared `AGENTS` list guarantees the
  export order always matches the pipeline order.

---

### 6.9 `backend/main.py` — the FastAPI application

The HTTP surface. One process serves the API and the frontend.

- **`app`** — the FastAPI instance, titled "AEGIS · Ezor Media".
- **`FRONTEND_DIR`** — path to `frontend/`.
- **`_startup()`** (on `startup` event) — calls `database.init_db()` so the
  table exists before any request.
- **`GET /api/health`** — returns status, current mode, the model name (in LIVE)
  or `null` (in DEMO), and the agency. Used by the UI to render the mode pill.
- **`POST /api/run`** — the core endpoint. Reads the brief JSON from the request
  body, generates a 12-hex-char `run_id`, and returns a **`StreamingResponse`**
  with media type `text/event-stream` whose body is `orchestrator.run_pipeline`.
  Sets `Cache-Control: no-cache`, `Connection: keep-alive`, and
  `X-Accel-Buffering: no` so proxies don't buffer the stream. This is what makes
  the live relay work.
- **`GET /api/runs`** — returns the run history (`database.list_runs`) as JSON.
- **`GET /api/runs/{run_id}`** — returns one run, or 404 if not found.
- **`GET /api/runs/{run_id}/export.md`** — builds the Markdown via
  `export.build_markdown` and returns it as a file download
  (`Content-Disposition: attachment; filename="<brand>_brief.md"`).
- **`GET /`** — serves `frontend/index.html`.
- **Static mount** — `app.mount("/", StaticFiles(directory=frontend))` serves
  `styles.css`, `app.js`, `scene.js`, and assets. Mounted last so the explicit
  API routes take precedence.

---

## 7. The end-to-end request lifecycle (data flow)

Follow one campaign from click to download:

1. **User fills the brief** in the browser and clicks "Generate campaign".
   `app.js` collects the eight form fields into a JSON object.
2. **`POST /api/run`** is sent with that JSON. `main.start_run` reads it, mints a
   `run_id`, and returns a streaming response wired to
   `orchestrator.run_pipeline`.
3. **`run_pipeline`** creates the SQLite row (status `running`) and emits
   `run_started` with the whole agent roster. The browser draws five lanes.
4. **For each agent** (Research → Competitor → Strategy → Creative → Media):
   - `agent_started` fires; the UI lights that lane.
   - Text is produced: in LIVE mode by streaming Claude with a prompt that
     contains the Ezor context, the brief, **and every earlier agent's output**;
     in DEMO mode from the interpolated template. Either way it arrives as a
     series of `agent_chunk` events and renders live.
   - `agent_done` fires; the finished text is saved to `outputs` and added to
     `context` so the next agent can see it.
   - If that agent throws, `agent_error` fires instead and the loop moves on.
5. **`finalize_run`** writes all outputs and marks the run `complete`;
   `run_complete` is emitted with the full outputs map. The UI assembles the
   final brief.
6. **Export**: clicking download hits `GET /api/runs/{id}/export.md`, which
   rebuilds the Markdown from the stored run and returns it as a file.
7. **History**: the run is now listed by `GET /api/runs` and can be reopened via
   `GET /api/runs/{id}` at any time.

The **context-threading** in step 4 is what makes the output cohesive rather
than five disconnected paragraphs: Strategy literally reads Research and
Competitor; Creative reads everything above it; Media sees the whole plan.

---

## 8. The SSE event contract (server → browser)

The frontend is driven entirely by these six named events. Each `data` payload
is JSON.

| Event | When | Payload |
|---|---|---|
| `run_started` | Once, at the start | `run_id`, `mode`, `agents` (full roster: id, name, role, icon) |
| `agent_started` | Before each agent | `id`, `name` |
| `agent_chunk` | Repeatedly, per agent | `id`, `text` (a piece of streamed output) |
| `agent_done` | After an agent succeeds | `id` |
| `agent_error` | If an agent fails | `id`, `error` |
| `run_complete` | Once, at the end | `run_id`, `outputs` (id → full text map) |

A well-formed run emits exactly one `run_started`, then for each of the five
agents either (`agent_started` … many `agent_chunk` … `agent_done`) or
(`agent_started` … `agent_error`), and finally one `run_complete`.

---

## 9. The SQLite schema

One table, `runs`:

| Column | Type | Meaning |
|---|---|---|
| `id` | TEXT PRIMARY KEY | The 12-hex-char run id |
| `created_at` | REAL | Unix timestamp when the run started |
| `mode` | TEXT | `LIVE` or `DEMO` at the time of the run |
| `brief` | TEXT | The input brief, JSON-encoded |
| `outputs` | TEXT | Agent-id → output-text map, JSON-encoded |
| `status` | TEXT | `running` while in flight, `complete` when finished |

The DB file lives at `data/aegis.db` and is mounted as a Docker volume in
production so history survives container rebuilds.

---

## 10. Configuration and environment variables

| Variable | Default | Effect |
|---|---|---|
| `ANTHROPIC_API_KEY` | (empty) | Non-empty `sk-…` value → LIVE mode; else DEMO |
| `AEGIS_MODEL` | `claude-sonnet-4-6` | Which Claude model LIVE mode calls |
| `AEGIS_DEMO_DELAY` | `0.012` | Seconds between streamed word-batches (DEMO) |
| `AEGIS_AGENT_PAUSE` | `0.35` | Seconds paused before each agent (DEMO) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | — | Used only by the deploy script |

The `.env` file is git-ignored; only `.env.example` is committed. Switching from
DEMO to LIVE is literally uncommenting/setting the key and restarting — no code
change.

---

## 11. Deployment (production)

- **`Dockerfile`** — `python:3.11-slim`, installs `requirements.txt`, copies
  `backend/` and `frontend/`, runs `uvicorn backend.main:app` on port 8000.
- **`docker-compose.prod.yml`** — one service, maps host **port 80** to the
  container's 8000, injects config from the `.env` file, mounts `./data` for
  DB persistence, and restarts unless stopped.
- **`deploy/aws/deploy.py`** — one command to stand the whole thing up on a
  free-tier EC2 instance: it creates an SSH key pair, a security group (opens
  ports 80 and 22), and a `t3.micro` instance whose cloud-init installs Docker
  plus the compose and buildx plugins; then it zips the app (excluding local and
  generated files), uploads it with a server-side `.env`, and runs
  `docker compose -f docker-compose.prod.yml up -d --build`. Supports
  `--redeploy` (push new code to the same instance) and `--terminate` (tear
  down). The deployed app inherits the same key from `.env`, so the identical
  DEMO/LIVE switch works in the cloud.

---

## 12. Design rationale — why it's built this way

- **One process, no build step.** Backend and the vanilla frontend ship
  together and run from a single command. There is no `npm install`, no bundler,
  no CDN dependency for core function — so it cannot break on a fresh machine
  over a toolchain mismatch.
- **DEMO/LIVE parity.** Because both modes share every code path except the text
  source, "going live" introduces no new, untested path. The demo is always
  faithful to the real thing.
- **Streaming as a first-class experience.** SSE turns a slow multi-step AI job
  into a live, legible relay the user can watch, rather than a spinner.
- **Fail-soft pipeline.** Each agent is isolated; one transient error degrades
  to a single skipped section instead of a wasted run.
- **Compounding context.** Feeding each agent the prior outputs is what makes
  the final brief read as one coherent strategy rather than five stitched-together
  answers.
- **Single source of truth for order and mode.** The agent order lives once in
  `AGENTS`; the mode decision lives once in `config.LIVE_MODE`. Persistence,
  export, and the UI all derive from those, so they can never drift apart.

---

## 13. Extending AEGIS (common changes and where to make them)

| To change… | Edit… |
|---|---|
| Add / remove / reorder an agent | `agents.AGENTS` (order) and its `build_prompt` instructions; add matching DEMO text in `demo_data.demo_output` |
| Change what an agent asks for | the per-agent instruction dict in `agents.build_prompt` |
| Change the model or token limit | `config.MODEL` / `AEGIS_MODEL`; `max_tokens` in `claude_client.stream_completion` |
| Change DEMO pacing/feel | `AEGIS_DEMO_DELAY`, `AEGIS_AGENT_PAUSE` |
| Change the exported document | `export.build_markdown` |
| Add a new API route | `main.py` |
| Change persisted fields | `database.py` schema + `_row_to_dict` |

Because the two text sources and the mode decision are each isolated, most
changes touch exactly one file.

---

## 14. Frequently asked questions

**Does it need an API key to run?** No. With no key it runs in DEMO mode with
realistic output. A key switches it to LIVE Claude output; nothing else changes.

**What happens if Claude errors mid-run?** The `claude_client` retries transient
failures; if an agent still fails, the orchestrator records an error note for
that one section and continues — the run completes with the other four.

**Is the frontend part of this documentation?** No. The frontend is vanilla,
build-free HTML/CSS/JS and is intentionally out of scope here; this document
covers the backend, data flow, and architecture.

**Where is data stored?** In a local SQLite file (`data/aegis.db`), one row per
run. In production that folder is a Docker volume, so history persists across
rebuilds.

**How is the output kept coherent across five agents?** Each agent's prompt
includes the outputs of all earlier agents (the "context"), so later agents
build directly on earlier ones.

**How do you go from demo to production?** Add the API key to `.env`, restart
locally to verify LIVE, then `python deploy/aws/deploy.py` (first time) or
`--redeploy` (subsequent) to push it to EC2.

---

*AEGIS · Campaign Intelligence for Ezor Media. This document describes the
backend architecture, every module and function, the data flow, and the design
reasoning as a single self-contained source.*
