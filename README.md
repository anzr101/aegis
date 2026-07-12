# AEGIS — Campaign Intelligence for Ezor Media

A multi-agent platform that turns a single client brief into a complete,
on-brand campaign strategy. Five specialised agents run as one pipeline —
**Research → Competitor → Strategy → Creative → Media & Budget** — each one
streaming live, each feeding its work to the next. The result is a finished,
downloadable campaign brief your account team can present.

Built for **Ezor Media**.

---

## Quick start (60 seconds, no API key needed)

The platform ships in **DEMO mode** — it runs the full pipeline and UI with
realistic, brief-adaptive output so it works on a fresh machine with zero setup.
Add an Anthropic key whenever you want real AI output (**LIVE mode**).

### Option A — one command (macOS / Linux)

```bash
./run.sh
```

### Option A — one command (Windows)

```bat
run.bat
```

### Option B — Docker

```bash
docker compose up
```

Then open **http://localhost:8000**.

> First run installs dependencies into a local `.venv` — give it a minute.
> Every run after that is instant.

---

## Going LIVE (real AI output)

1. Copy the env file (the run scripts do this for you):
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste your key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   Get one at https://console.anthropic.com.
3. Restart. The mode pill in the top-right flips from **DEMO** to **LIVE**.

That's the only difference — DEMO and LIVE run the exact same pipeline, UI,
streaming, persistence and export.

---

## What's inside

| Layer | Tech | Notes |
|---|---|---|
| Backend | FastAPI | One process serves API **and** frontend |
| Orchestration | Async pipeline | 5 agents in sequence, context passed forward |
| Streaming | Server-Sent Events | Per-agent token streaming drives the live relay |
| AI | Anthropic Claude | `claude-sonnet-4-6`, with retries + graceful per-agent failure |
| Persistence | SQLite | Every run saved; browsable history |
| Frontend | Vanilla HTML/CSS/JS | No build step, no CDN dependency — self-contained |
| Export | Markdown | Download or copy the finished brief |
| Deploy | Docker / Compose | Single-command container |

### Why no `npm install`?
The frontend is intentionally build-free so the whole product runs from one
Python process with one command and **cannot break on a fresh machine** over a
node/npm mismatch. It still streams live over SSE and renders Markdown (tables
included) with a self-contained renderer.

---

## Project layout

```
aegis-ezor/
├── run.sh / run.bat          one-command setup + launch
├── docker-compose.yml        one-command container
├── requirements.txt
├── .env.example
├── backend/
│   ├── main.py               FastAPI app, SSE endpoint, serves frontend
│   ├── orchestrator.py       runs the 5 agents, emits SSE events
│   ├── agents.py             agent roster + prompt builders
│   ├── claude_client.py      Anthropic streaming + retries (LIVE only)
│   ├── demo_data.py          brief-adaptive DEMO output (no key needed)
│   ├── database.py           SQLite run history
│   ├── export.py             assemble brief as Markdown
│   └── config.py             DEMO/LIVE detection
├── frontend/
│   ├── index.html            single-page interface
│   ├── styles.css            Ezor editorial aesthetic
│   └── app.js                SSE client, relay, Markdown renderer
└── data/                     SQLite db (created at runtime)
```

---

## How to use it

1. Open the app, fill in the brief (or hit **Load sample brief**).
2. Press **Generate campaign**. Watch the gold relay charge as each agent
   completes and its section streams into the brief.
3. When the pipeline finishes, **Download brief (.md)** or **Copy as Markdown**.
4. Revisit any past run from **History** (top-right).

---

*AEGIS · built for Ezor Media.*
