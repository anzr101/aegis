# Annotated: config & infra — deps, container, env, launch scripts

The non-Python files that install, configure, containerise, and launch AEGIS.
Together they deliver the "one command, no build step, can't break on a fresh
machine" promise.

---

## `requirements.txt` — Python dependencies

```
1  fastapi==0.115.6            # web framework: routing, StreamingResponse, StaticFiles
2  uvicorn[standard]==0.34.0   # ASGI server that runs the app; [standard] adds fast websockets/httptools
3  anthropic==0.42.0           # Claude SDK — only actually needed in LIVE mode
4  python-dotenv==1.0.1        # loads .env; config.py degrades gracefully if it's missing
```
- Four pinned deps, nothing else. `anthropic` is listed but imported lazily
  (`claude_client.py`), so DEMO works even if it fails to build. Pins keep a fresh
  install reproducible.

---

## `Dockerfile` — the container image

```dockerfile
1  FROM python:3.11-slim                          # small base image, Python 3.11
3  WORKDIR /app
5  COPY requirements.txt .
6  RUN pip install --no-cache-dir -r requirements.txt   # deps first → cached layer, no pip cache bloat
8  COPY backend  ./backend                        # app code copied AFTER deps (better layer caching)
9  COPY frontend ./frontend                        # frontend shipped inside the same image
11 EXPOSE 8000
13 CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- Standard layered build. **Deps are copied and installed before the app code**
  (lines 5–6) so code changes don't invalidate the pip layer.
- `--host 0.0.0.0` (line 13) binds all interfaces so the container is reachable
  from the host. Note `data/` is **not** baked in — it's provided as a volume (see
  compose) so the SQLite DB survives container restarts.

---

## `docker-compose.yml` — one-command container

```yaml
1  services:
2    aegis:
3      build: .                               # build from the local Dockerfile
4      ports:
5        - "8000:8000"                        # host:container
6      environment:
7        # Optional — leave blank for DEMO mode, add key for LIVE AI.
8        - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}          # passthrough; empty default → DEMO
9        - AEGIS_MODEL=${AEGIS_MODEL:-claude-sonnet-4-6}     # overridable model, sensible default
10     volumes:
11       - ./data:/app/data                   # persist the SQLite DB outside the container
12     restart: unless-stopped                # auto-restart on crash / reboot
```
- `docker compose up` is the whole deploy. The `${VAR:-default}` syntax (lines
  8–9) means it runs in DEMO with no host env set, and flips to LIVE when
  `ANTHROPIC_API_KEY` is exported — matching `config.LIVE_MODE`.
- **Line 11** is why history survives: `data/` is bind-mounted, so `aegis.db`
  lives on the host, not in the ephemeral container layer.

---

## `.env.example` — configuration template

```bash
1-3  # AEGIS configuration — leave as-is for DEMO; add a key for LIVE AI.
6    ANTHROPIC_API_KEY=              # blank → DEMO. Paste sk-ant-... to go LIVE.
9    AEGIS_MODEL=claude-sonnet-4-6   # model used in LIVE mode
10   AEGIS_DEMO_DELAY=0.012          # seconds between DEMO word-batches (config.DEMO_CHUNK_DELAY)
11   AEGIS_AGENT_PAUSE=0.35          # seconds before each DEMO agent (config.DEMO_AGENT_PAUSE)
```
- The template `run.sh`/`run.bat` copy to `.env` on first run. Every variable maps
  directly to a constant in `config.py`. Blank key = DEMO, by design.

---

## `run.sh` — one-command setup + launch (macOS / Linux)

```bash
1-3   #!/usr/bin/env bash ; set -e            # abort on any error
5     cd "$(dirname "$0")"                     # run from the script's own dir (path-independent)
11-15 # 1. Python check — fail clearly if python3 is missing
17-23 # 2. venv — create .venv on first run, then activate it
25-28 # 3. deps — pip install -r requirements.txt (quiet)
30-34 # 4. env — copy .env.example → .env if no .env yet (creates DEMO config)
37-41 # 5. launch — exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
- The five-step "cannot fail on a fresh machine" bootstrap: check Python → create
  & activate venv → install deps → seed `.env` → launch. `exec` on line 41
  replaces the shell with uvicorn so Ctrl-C stops the server cleanly.

---

## `run.bat` — the same, for Windows

```bat
2-3   @echo off ; cd /d "%~dp0"               # run from the script's directory
9-13  where python ... — fail if Python missing
15-19 if not exist ".venv" → python -m venv .venv ; activate
21-23 pip install -r requirements.txt
25-28 if no .env → copy .env.example .env
34    uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
- The Windows-native mirror of `run.sh`, so the same one-command experience works
  on `cmd`/PowerShell without WSL.

---

## `.gitignore`

```
1  .venv/          # local virtualenv (rebuilt by run scripts)
2  __pycache__/    # Python bytecode
3  *.pyc
4  .env            # secrets — the real key never gets committed (only .env.example is tracked)
5  data/*.db       # the runtime SQLite DB is not source
6  .DS_Store
```
- Keeps secrets (`.env`) and generated artefacts (venv, bytecode, the DB) out of
  version control. Only `.env.example` is tracked.
