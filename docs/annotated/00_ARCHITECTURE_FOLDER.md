# 00 · Architecture & Folder Map

## The folder tree (non-frontend focus)

```
aegis-ezor/
├── run.sh / run.bat            one-command setup + launch (venv → deps → .env → uvicorn)
├── docker-compose.yml          one-command container (mounts ./data, passes key through)
├── Dockerfile                  python:3.11-slim image, runs uvicorn
├── requirements.txt            fastapi, uvicorn, anthropic, python-dotenv
├── .env / .env.example         config (key, model, pacing) — .env is git-ignored
├── .gitignore
│
├── backend/                    ← everything documented here
│   ├── __init__.py             package marker + title
│   ├── config.py               env → DEMO/LIVE decision, paths, pacing constants
│   ├── agents.py               the 5-agent roster + prompt builder (shared context)
│   ├── demo_data.py            brief-adaptive canned output (DEMO mode text source)
│   ├── claude_client.py        Anthropic streaming + retries (LIVE mode text source)
│   ├── orchestrator.py         runs agents in sequence, emits SSE events, feeds context forward
│   ├── database.py             SQLite: create / finalize / get / list runs
│   ├── export.py               assemble a finished run into a Markdown brief
│   └── main.py                 FastAPI app: /api/run (SSE), history, export, serves frontend
│
├── frontend/                   ← intentionally EXCLUDED from this doc set
│   ├── index.html
│   ├── styles.css
│   ├── app.js                  SSE client + Markdown renderer
│   └── scene.js                hero 3D / motion
│
└── data/
    └── aegis.db                SQLite DB (created at runtime by config.py / database.init_db)
```

## Layer responsibilities

| Layer | File(s) | Responsibility | Depends on |
|---|---|---|---|
| **Config** | `config.py`, `__init__.py` | Load `.env`, decide DEMO vs LIVE, expose paths + pacing + labels. The one source of truth for "which mode are we in". | stdlib, `dotenv` (optional) |
| **Domain — agents** | `agents.py` | Static roster of 5 agents; builds each agent's prompt from the brief + prior agents' work. Pure, no I/O. | — |
| **Text sources** | `demo_data.py`, `claude_client.py` | The two ways a chunk of agent text can be produced: canned (DEMO) or streamed from Claude (LIVE). | `config` |
| **Pipeline** | `orchestrator.py` | Runs the 5 agents in order, picks the text source per mode, streams chunks, passes each output forward as context, and formats everything as SSE. | `agents`, `config`, `demo_data`, `claude_client`, `database` |
| **Persistence** | `database.py` | SQLite CRUD for runs (id, brief, outputs, status, mode, timestamp). | `config` |
| **Assembly** | `export.py` | Turn a stored run into a Markdown campaign brief. | `agents` |
| **Web** | `main.py` | FastAPI app: health, the SSE run endpoint, run history, Markdown export, and static serving of the frontend. | all of the above |

## Import / dependency graph

```
                       config.py ──────────────┐  (mode, paths, pacing)
                          ▲  ▲  ▲               │
                          │  │  │               ▼
   __init__.py        agents.py  demo_data.py  claude_client.py
        │                 ▲          ▲              ▲
        │                 │          │              │
        │                 └────┬─────┴──────────────┘
        │                      │
        │                 orchestrator.py ──► database.py ──► config.py
        │                      ▲
        │                      │
   database.py ◄──── main.py ──┼──► orchestrator.py
   export.py   ◄──── main.py   └──► export.py ──► agents.py
```

- **No circular imports.** `config` is a leaf everyone reads. `agents` is a pure
  leaf. `main` sits at the top and wires the request handlers to
  `orchestrator`, `database`, and `export`.
- `claude_client` is imported **lazily** (inside functions) so a missing
  `anthropic` package can never break DEMO mode.

## The SSE event contract

`/api/run` returns a `text/event-stream`. `orchestrator.run_pipeline` emits these
events (each as `event: <name>\ndata: <json>\n\n`):

| Event | When | `data` payload |
|---|---|---|
| `run_started` | Once, at the top | `{run_id, mode, agents:[{id,name,role,icon}×5]}` |
| `agent_started` | Before each agent | `{id, name}` |
| `agent_chunk` | Repeatedly, per token batch | `{id, text}` |
| `agent_done` | After an agent finishes cleanly | `{id}` |
| `agent_error` | If an agent throws | `{id, error}` (pipeline continues) |
| `run_complete` | Once, at the end | `{run_id, outputs:{agent_id → text}}` |

The frontend (`app.js`) consumes this stream to drive the live relay UI and to
assemble the final brief.

## The SQLite schema

One table, created by `database.init_db()`:

```sql
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,   -- uuid4().hex[:12], generated in main.start_run
    created_at  REAL NOT NULL,      -- time.time() at creation
    mode        TEXT NOT NULL,      -- "DEMO" | "LIVE" (config.mode_label())
    brief       TEXT NOT NULL,      -- JSON of the client brief dict
    outputs     TEXT NOT NULL,      -- JSON of {agent_id → markdown text}
    status      TEXT NOT NULL       -- "running" → "complete"
);
```

- `brief` and `outputs` are JSON blobs in `TEXT` columns — no schema migration
  needed when the brief shape changes.
- A run is written twice: `create_run` (status `running`, empty outputs) at the
  start, then `finalize_run` (status `complete`, full outputs) at the end.
