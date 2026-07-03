# AEGIS — Autonomous Engagement & Generative Intelligence System

Turn a one-line marketing brief into a complete, evaluated campaign strategy —
five specialized AI agents running as a coordinated pipeline, streamed live to
the browser.

## What it does

Submit a brief (brand, industry, goal, audience). AEGIS runs:

```
 Trend Intelligence   Audience Psychology   Creative Strategy
 (live web search)                          (3 distinct concepts)
        └────────── Stage 1: PARALLEL ──────────┘
                          │
                  Scoring / Evaluation      ← 8-dimension weighted rubric
                          │                   + adversarial self-critique
                  Supervisor Synthesis      ← conflict detection across agents,
                                              concept selection, honest confidence
```

Every stage streams its status and "thoughts" to the UI over Server-Sent
Events. Completed runs are persisted to PostgreSQL, and past high-scoring
campaigns in the same industry are retrieved as context for new runs.

## Architecture

- **Backend** — FastAPI (async), clean layering:
  `api/` routes → `services/` (orchestrator, event bus, LLM client) →
  `agents/` (5 agents on a shared `BaseAgent`) → `db/` (SQLAlchemy 2.0 async).
- **Agents** — each agent is a system prompt + a **strictly typed Pydantic
  output schema**. The LLM client injects the JSON schema into the prompt,
  validates the response, and retries on invalid output.
- **Orchestration** — plain `asyncio.gather` for the independent agents;
  no agent framework. Failures degrade gracefully: a failed agent becomes a
  "FAILED OR UNAVAILABLE" section in the supervisor's input, not a crash.
- **Models** — Claude Haiku 4.5 for the four operational agents (fast, cheap),
  Claude Sonnet 5 for the supervisor (cross-agent synthesis). ~$0.05–0.10/run.
- **Database** — PostgreSQL (JSONB for full run payloads, real columns for
  query fields), SQLite fallback for zero-setup dev. Same code path via
  SQLAlchemy async.
- **Frontend** — Next.js 14 + Tailwind + Zustand; live pipeline graph fed by SSE.

## Run locally

```bash
# Backend (SQLite — no DB setup needed)
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements-dev.txt
copy .env.example .env                              # add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload                       # http://localhost:8000/docs

# Frontend
cd ../frontend
npm install && npm run dev                          # http://localhost:3000
```

With PostgreSQL: set `DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/aegis`
in `backend/.env` (tables are created on startup). Or `docker compose up`.

## Tests

```bash
cd backend
pytest        # 27 tests, fully offline — stub LLM, isolated SQLite
```

The stub LLM returns valid instances of every agent's output schema, so the
orchestrator, degradation paths, event bus, persistence, and API surface are
all exercised end-to-end without an API key.

## Design decisions (short version)

- **No LangChain/LangGraph** — the pipeline is a fixed DAG; `asyncio.gather`
  plus a typed base class is simpler, debuggable, and fully owned.
- **Typed outputs everywhere** — Pydantic schemas as the contract between
  agents prevents hallucinated structure; validation failure triggers a retry.
- **Self-evaluation layer** — the Scoring agent's weighted rubric and
  self-critique make quality measurable rather than vibes-based.
- **In-memory event bus** — one run lives in one process; Redis pub/sub is the
  documented seam if this ever scales to multiple replicas.
