# 01 · End-to-End Explanation

## What AEGIS is

AEGIS is a **multi-agent campaign-intelligence platform** built for **Ezor Media**
(a Mumbai marketing & modeling agency). You feed it a single **client brief**
(brand, product, goal, audience, market, budget, timeline, notes) and it produces
a complete, on-brand, downloadable **campaign brief** — as if five specialists on
an account team each did their part in turn.

The five specialists are agents that run **as one pipeline, in a fixed order**:

1. **Research** — audience segments, cultural/behavioural signals, the biggest opportunity + risk.
2. **Competitor** — competitor archetypes, positioning gaps, one white-space angle.
3. **Strategy** — the big idea, three messaging pillars, KPIs.
4. **Creative** — hooks/taglines, hero ad copy, a two-week content calendar.
5. **Media & Budget** — channel mix table, spend split, projected outcome, measurement cadence.

The crucial design point: **each agent sees the brief plus everything the earlier
agents produced.** Strategy reads Research + Competitor; Creative reads all three
above it; Media reads all four. That's what makes the output feel like one
coherent team rather than five disconnected essays.

## The two runtime modes (this is the heart of the design)

Everything in AEGIS is built so it **cannot break on a fresh machine**. That goal
produces the DEMO/LIVE split:

- **DEMO mode** — the default. No API key, no network needed. Agent text comes
  from `demo_data.py`, which returns realistic, agency-grade copy that
  **interpolates the actual brief** (your brand name, budget, audience appear in
  the output). The orchestrator streams it word-by-word with small delays so it
  still *reads* like live thinking.
- **LIVE mode** — activated only when a plausibly-real Anthropic key
  (`sk-…`) is present. Agent text is streamed token-by-token from **Claude** via
  `claude_client.py`.

`config.py` makes the decision once (`LIVE_MODE`), and the rest of the app just
asks "which mode?" — the **UI, streaming, persistence, and export are identical**
in both. That means the product demos perfectly with zero credentials, and going
live is a one-line `.env` change.

```python
# config.py — the whole decision
LIVE_MODE = bool(ANTHROPIC_API_KEY) and ANTHROPIC_API_KEY.startswith("sk-")
```

## The request lifecycle (one campaign generation)

```
Browser                     FastAPI (main.py)          orchestrator.py            text source
  │  POST /api/run  ───────────►                            │                          │
  │  {brief JSON}              │  run_id = uuid[:12]        │                          │
  │                           │  StreamingResponse(SSE) ───►│                          │
  │                           │                            │  database.create_run()   │
  │  ◄── event: run_started ──┼────────────────────────────┤  (status "running")      │
  │                           │                            │                          │
  │        ┌── for each of the 5 agents, in order: ────────┤                          │
  │  ◄── event: agent_started ┤                            │                          │
  │                           │            _stream_agent_text(mode?) ────────────────►│
  │  ◄── event: agent_chunk ──┼◄─── chunk ─────────────────┤ DEMO: demo_data word-by-word
  │  ◄── event: agent_chunk ──┼◄─── chunk ─────────────────┤ LIVE: claude_client.stream_completion
  │        …                  │            full = "".join(chunks)                     │
  │  ◄── event: agent_done ───┤            context[name] = full  (fed to next agent)  │
  │        └───────────────────────────────────────────────┤                          │
  │                           │            database.finalize_run(outputs, "complete") │
  │  ◄── event: run_complete ─┴────────────────────────────┘                          │
```

Then, separately, the browser can:
- `GET /api/runs` — list history,
- `GET /api/runs/{id}` — reopen a past run,
- `GET /api/runs/{id}/export.md` — download the assembled Markdown brief
  (built by `export.py`).

## Why Server-Sent Events (not WebSockets)?

The data flow is strictly **one-way** (server → browser) and **request-scoped**
(one stream per generation). SSE is the exact fit: it's plain HTTP, works through
`StreamingResponse` with no extra dependency, auto-handles reconnection semantics
in the browser's `EventSource`, and needs no handshake protocol. The three
response headers (`Cache-Control: no-cache`, `Connection: keep-alive`,
`X-Accel-Buffering: no`) keep proxies from buffering the stream so tokens arrive
as they're produced.

## Why one process, no build step?

The frontend is **vanilla HTML/CSS/JS** and is served by the same FastAPI process
that runs the API (`main.py` mounts `frontend/` as static files and serves
`index.html` at `/`). There is deliberately **no `npm install`, no bundler, no
CDN dependency** for core function. The payoff: the entire product runs from one
Python command (`uvicorn backend.main:app`) and cannot fail on a fresh machine
over a node/npm/CDN mismatch.

## Why a single failing agent doesn't kill the run

Inside `orchestrator.run_pipeline`, each agent runs in its own `try/except`. If an
agent throws (e.g. a transient Claude error that survives `claude_client`'s three
retries), the orchestrator records a short "_this agent was skipped_" note in the
outputs, emits an `agent_error` event, and **moves on to the next agent**. A
single hiccup therefore degrades one section instead of wasting the whole brief.

## The resilience ladder (recurring theme)

| Failure | What saves it |
|---|---|
| No API key | DEMO mode — full pipeline still runs |
| `anthropic` package missing | `claude_client` imported lazily; only touched in LIVE |
| `python-dotenv` missing | `config.py` wraps the import in `try/except` |
| Transient Claude error | `claude_client` retries 3× with linear backoff |
| Persistent agent error | `orchestrator` catches per-agent, marks skipped, continues |
| Missing `data/` dir | `config.py` creates it at import (`DATA_DIR.mkdir`) |
| Proxy buffering the stream | explicit no-buffer SSE headers in `main.start_run` |

Every layer has a graceful degrade. That is the single most important thing to
understand about *why* this codebase is shaped the way it is.
