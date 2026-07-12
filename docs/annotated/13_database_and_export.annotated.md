# Annotated: `database.py`, `export.py` — persistence & brief assembly

`database.py` is the entire persistence layer — one SQLite table, stdlib only.
`export.py` turns a stored run into a downloadable Markdown campaign brief.

---

## `backend/database.py` — SQLite run history

**Data flow:** `orchestrator` calls `create_run` (start) and `finalize_run` (end);
`main.py` calls `init_db` (startup), `get_run`, and `list_runs` (API reads).

```python
1   """SQLite persistence for AEGIS runs. Stdlib only — no extra deps."""
2   import json
3   import sqlite3
4   import time
5   from contextlib import contextmanager
6   from typing import Optional
8   from . import config           # for config.DB_PATH

11  @contextmanager
12  def _conn():
13      conn = sqlite3.connect(config.DB_PATH)   # opens (creates) data/aegis.db
14      conn.row_factory = sqlite3.Row           # rows accessible by column name
15      try:
16          yield conn
17          conn.commit()                        # commit on clean exit
18      finally:
19          conn.close()                         # always close, even on error
```
- A tiny connection context manager: **open → yield → commit → always close.**
  Every function below uses `with _conn() as c:` so nobody forgets to commit or
  close. `Row` factory (line 14) is what lets `_row_to_dict` index by column name.
- A fresh connection per operation is fine here — SQLite is a local file and the
  workload is light (one run at a time).

```python
22  def init_db():
23      with _conn() as c:
24          c.execute("""
25-34         CREATE TABLE IF NOT EXISTS runs (
                  id TEXT PRIMARY KEY, created_at REAL, mode TEXT,
                  brief TEXT, outputs TEXT, status TEXT )""")
```
- Idempotent schema creation (called at every app startup). `brief` and `outputs`
  are `TEXT` columns holding **JSON** — so the brief/outputs shape can evolve with
  no migration.

```python
38  def create_run(run_id: str, brief: dict, mode: str):
39      with _conn() as c:
40          c.execute(
41              "INSERT OR REPLACE INTO runs (id, created_at, mode, brief, outputs, status) "
42              "VALUES (?,?,?,?,?,?)",
43              (run_id, time.time(), mode, json.dumps(brief), json.dumps({}), "running"),
44          )
```
- Inserts the run at pipeline start: current timestamp, the brief serialized to
  JSON, **empty** outputs, status `"running"`. `INSERT OR REPLACE` makes it safe
  if the same `run_id` somehow recurs. Parameterised (`?`) — no SQL injection.

```python
47  def finalize_run(run_id: str, outputs: dict, status: str = "complete"):
48      with _conn() as c:
49          c.execute("UPDATE runs SET outputs=?, status=? WHERE id=?",
50                    (json.dumps(outputs), status, run_id))
```
- Called once at pipeline end: writes the full outputs JSON and flips status to
  `complete`.

```python
55  def get_run(run_id: str) -> Optional[dict]:
56      with _conn() as c:
57          row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
58      if not row:
59          return None                          # unknown id → None (main.py turns this into 404)
60      return _row_to_dict(row)

63  def list_runs(limit: int = 50) -> list:
64      with _conn() as c:
65          rows = c.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
66      return [_row_to_dict(r) for r in rows]   # newest first, capped at 50
```
- `get_run` returns one run or `None`; `list_runs` returns the most-recent-first
  history (the "History" panel in the UI).

```python
71  def _row_to_dict(row: sqlite3.Row) -> dict:
72      return {
73          "id":         row["id"],
74          "created_at": row["created_at"],
75          "mode":       row["mode"],
76          "brief":      json.loads(row["brief"]),     # JSON text → dict
77          "outputs":    json.loads(row["outputs"]),   # JSON text → dict
78          "status":     row["status"],
79      }
```
- The single deserialization point: reverses the `json.dumps` from `create_run` /
  `finalize_run` so callers get real dicts back, not JSON strings.

---

## `backend/export.py` — assemble a run into a Markdown brief

**Data flow:** `main.export_md` loads a run via `database.get_run`, passes it here,
and returns the string as a downloadable `.md` file.

```python
1   """Assemble a finished run into a downloadable campaign brief (Markdown)."""
2   from datetime import datetime
4   from . import agents          # to iterate AGENTS in the canonical order

7   def build_markdown(run: dict) -> str:
8       brief   = run["brief"]
9       outputs = run["outputs"]
10      when = datetime.fromtimestamp(run["created_at"]).strftime("%d %B %Y, %H:%M")  # e.g. "08 July 2026, 14:30"

12      lines = [
13          f"# {brief.get('brand', 'Campaign')} — Campaign Brief",
14          "",
15          f"*Prepared by AEGIS · Ezor Media · {when} · {run['mode']} mode*",   # provenance line
16-25       "## Brief", ... one bullet per brief field (brand/product/goal/audience/market/budget/timeline) ...
27          "---", "",
29      ]

31      for agent in agents.AGENTS:                     # SAME order as the pipeline
32          aid = agent["id"]
33          lines.append(f"## {agent['icon']} · {agent['name']} — {agent['role']}")  # section header
34          lines.append("")
35          lines.append(outputs.get(aid, "_No output._"))   # the agent's markdown, or a placeholder
36          lines.append("")
37          lines.append("---")
38          lines.append("")

40      lines.append("*Generated by AEGIS — the campaign intelligence platform for Ezor Media.*")
41      return "\n".join(lines)
```
- Builds the document as a **list of lines** joined at the end — easy to read and
  reorder. Structure: title → provenance → the brief recap → one `##` section per
  agent → footer.
- **Line 31** iterates `agents.AGENTS`, so the export order always matches the
  pipeline order (Research → … → Media), regardless of insertion order in the
  `outputs` dict.
- **Line 35** uses `outputs.get(aid, "_No output._")`, so a skipped agent (from the
  orchestrator's per-agent `except`) still produces a clean section rather than a
  `KeyError`. Because the agent outputs are *already Markdown* (tables, bullets),
  they drop straight into the document unchanged.
