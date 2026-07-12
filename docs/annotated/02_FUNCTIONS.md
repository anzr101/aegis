# 02 · Function & Symbol Reference

Every function, constant, and route in the backend, grouped by file. Signatures
are exact; notes explain inputs, outputs, and gotchas.

---

## `backend/config.py`

| Symbol | Kind | Signature / value | Notes |
|---|---|---|---|
| `BASE_DIR` | const `Path` | `…/aegis-ezor` | Parent of `backend/`; the project root. |
| `DATA_DIR` | const `Path` | `BASE_DIR/"data"` | `.mkdir(exist_ok=True)` at import — guarantees the folder exists. |
| `DB_PATH` | const `Path` | `DATA_DIR/"aegis.db"` | SQLite file location used by `database.py`. |
| `ANTHROPIC_API_KEY` | const `str` | `os.getenv("ANTHROPIC_API_KEY","").strip()` | Empty string if unset. |
| `MODEL` | const `str` | `os.getenv("AEGIS_MODEL","claude-sonnet-4-6")` | Model id used in LIVE mode. |
| `LIVE_MODE` | const `bool` | `bool(key) and key.startswith("sk-")` | The single DEMO/LIVE switch. |
| `APP_NAME`, `APP_TAGLINE`, `AGENCY` | const `str` | `"AEGIS"`, `"Campaign Intelligence"`, `"Ezor Media"` | Branding strings. |
| `DEMO_CHUNK_DELAY` | const `float` | env `AEGIS_DEMO_DELAY` (0.012) | Seconds between DEMO word-batches. |
| `DEMO_AGENT_PAUSE` | const `float` | env `AEGIS_AGENT_PAUSE` (0.35) | Pause before each DEMO agent starts. |
| `mode_label()` | func | `() -> str` | Returns `"LIVE"` or `"DEMO"`. |

---

## `backend/agents.py`

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `EZOR_CONTEXT` | const `str` | dedented block | Shared system context (Ezor voice, Indian market) prepended to every prompt. |
| `AGENTS` | const `list[dict]` | 5 dicts: `{id,name,role,icon}` | The ordered roster. Iteration order = pipeline order. |
| `_brief_block(brief)` | func | `(dict) -> str` | Formats the client brief as a labelled text block; `.get(…, 'N/A')` for missing fields. |
| `_prior(context)` | func | `(dict) -> str` | Joins earlier agents' outputs as `### Name\n<text>` blocks; `""` if none. |
| `build_prompt(agent_id, brief, context)` | func | `(str, dict, dict) -> str` | Assembles the full prompt: context + brief + prior work + agent-specific instructions. Raises `KeyError` for an unknown `agent_id`. |

---

## `backend/demo_data.py`

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `_g(brief, key, default)` | func | `(dict, str, str) -> str` | Safe getter: returns `default` for missing/blank fields (so demo copy never shows "None"). |
| `demo_output(agent_id, brief)` | func | `(str, dict) -> str` | Returns brief-interpolated Markdown for one agent. Unknown id → a placeholder string (does not raise). |

---

## `backend/claude_client.py`

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `stream_completion(prompt, max_retries=3)` | async gen | `(str, int) -> AsyncIterator[str]` | Yields text chunks from Claude. Imports `anthropic` lazily. Retries transient errors with `0.8*attempt` backoff; raises `RuntimeError` after `max_retries`. |

---

## `backend/orchestrator.py`

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `_sse(event, data)` | func | `(str, dict) -> str` | Formats one SSE frame: `event: …\ndata: <json>\n\n`. |
| `_stream_agent_text(agent_id, brief, context)` | async gen | `(str, dict, dict) -> AsyncIterator[str]` | Picks the text source by mode. LIVE: Claude stream. DEMO: `demo_output` split into 3-word batches with `DEMO_CHUNK_DELAY` sleeps. |
| `run_pipeline(run_id, brief)` | async gen | `(str, dict) -> AsyncIterator[str]` | The whole pipeline. Creates the run, streams all 5 agents (per-agent `try/except`), feeds outputs forward as context, finalizes the run, emits all SSE events. |

---

## `backend/database.py`

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `_conn()` | contextmanager | `() -> Connection` | Opens SQLite with `Row` factory; commits on success, always closes. |
| `init_db()` | func | `() -> None` | Creates the `runs` table if missing. Called at app startup. |
| `create_run(run_id, brief, mode)` | func | `(str, dict, str) -> None` | Inserts a `running` row with empty outputs (`INSERT OR REPLACE`). |
| `finalize_run(run_id, outputs, status="complete")` | func | `(str, dict, str) -> None` | Updates outputs + status for a run. |
| `get_run(run_id)` | func | `(str) -> Optional[dict]` | Fetch one run (JSON columns parsed back to dicts) or `None`. |
| `list_runs(limit=50)` | func | `(int) -> list[dict]` | Most-recent-first list of runs. |
| `_row_to_dict(row)` | func | `(Row) -> dict` | Deserializes a DB row; `json.loads` the `brief`/`outputs` columns. |

---

## `backend/export.py`

| Symbol | Kind | Signature | Notes |
|---|---|---|---|
| `build_markdown(run)` | func | `(dict) -> str` | Assembles a full Markdown brief: title, formatted date, brief bullets, then one `##` section per agent in roster order. |

---

## `backend/main.py`  (routes)

| Route | Method | Handler | Returns |
|---|---|---|---|
| `/api/health` | GET | `health()` | `{status, mode, model, agency}` |
| `/api/run` | POST | `start_run(request)` | `StreamingResponse` (SSE) of the pipeline |
| `/api/runs` | GET | `runs()` | JSON list of runs |
| `/api/runs/{run_id}` | GET | `run_detail(run_id)` | JSON run, or 404 |
| `/api/runs/{run_id}/export.md` | GET | `export_md(run_id)` | Markdown file download, or 404 |
| `/` | GET | `index()` | `frontend/index.html` |
| `/` (mount) | — | `StaticFiles(frontend/)` | Serves css/js/assets |

| Symbol | Kind | Notes |
|---|---|---|
| `app` | `FastAPI` | Titled `"AEGIS · Ezor Media"`. |
| `FRONTEND_DIR` | `Path` | `config.BASE_DIR/"frontend"`. |
| `_startup()` | startup hook | Calls `database.init_db()`. |
