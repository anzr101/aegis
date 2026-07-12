# AEGIS — Backend Documentation Set

Complete technical documentation for the **non-frontend** (backend) of AEGIS —
the campaign-intelligence platform built for **Ezor Media**. Every Python module
plus the infra/config files, annotated line-by-line, with architecture, a
narrative explanation, and a function reference. The vanilla `frontend/`
(`index.html`, `styles.css`, `app.js`, `scene.js`) is intentionally excluded.

## How to read this

Start at the top three overview docs, then dive into whichever annotated file
covers the module you're working on.

| # | File | What it is |
|---|------|------------|
| — | [`00_ARCHITECTURE_FOLDER.md`](00_ARCHITECTURE_FOLDER.md) | The whole folder tree, layer responsibilities, the import/dependency graph, the SSE event contract, and the SQLite schema. |
| — | [`01_EXPLANATION.md`](01_EXPLANATION.md) | End-to-end narrative: what AEGIS is, the two runtime modes (DEMO/LIVE), the five-agent pipeline, request lifecycle, and *why* it's built this way. |
| — | [`02_FUNCTIONS.md`](02_FUNCTIONS.md) | Every function / constant / route with signature, inputs, outputs, and technical notes. |

## Line-by-line annotated source

| # | File | Covers |
|---|------|--------|
| 10 | [`10_config_and_agents.annotated.md`](10_config_and_agents.annotated.md) | `backend/config.py`, `backend/__init__.py`, `backend/agents.py` — mode detection, paths, the agent roster and prompt builder. |
| 11 | [`11_demo_and_claude_client.annotated.md`](11_demo_and_claude_client.annotated.md) | `backend/demo_data.py`, `backend/claude_client.py` — the two text sources (canned DEMO vs. live Claude streaming). |
| 12 | [`12_orchestrator.annotated.md`](12_orchestrator.annotated.md) | `backend/orchestrator.py` — the pipeline that runs the five agents and emits SSE events. |
| 13 | [`13_database_and_export.annotated.md`](13_database_and_export.annotated.md) | `backend/database.py`, `backend/export.py` — SQLite run persistence and Markdown brief assembly. |
| 14 | [`14_main.annotated.md`](14_main.annotated.md) | `backend/main.py` — the FastAPI app: SSE endpoint, run history, export, static frontend serving. |
| 15 | [`15_config_and_infra.annotated.md`](15_config_and_infra.annotated.md) | `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `run.sh`, `run.bat`, `.gitignore`. |
| 16 | [`16_deploy_aws.annotated.md`](16_deploy_aws.annotated.md) | `deploy/aws/deploy.py`, `docker-compose.prod.yml` — one-command EC2 deployment: what it creates, section-by-section, and post-deploy operations. |

## The one-paragraph summary

AEGIS turns **one client brief** into a **finished, downloadable campaign brief**
by running five specialised agents in sequence — **Research → Competitor →
Strategy → Creative → Media & Budget** — where each agent sees the brief plus the
accumulated output of every prior agent. The whole thing runs as a **single
FastAPI process** that serves both the API and the build-free frontend. It has
two interchangeable modes: **DEMO** (brief-adaptive canned copy, zero setup, no
API key) and **LIVE** (real Anthropic Claude streaming) — selected automatically
by `config.py` based on whether a real `sk-…` key is present. Output streams to
the browser token-by-token over **Server-Sent Events**; every run is saved to
**SQLite** and can be re-opened from history or exported as **Markdown**. The
design goal throughout: it **cannot break on a fresh machine** — no key, no build
step, no CDN dependency, and a single failing agent never kills the run.
