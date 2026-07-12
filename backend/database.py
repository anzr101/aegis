"""SQLite persistence for AEGIS runs. Stdlib only — no extra deps."""
import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Optional

from . import config


@contextmanager
def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id          TEXT PRIMARY KEY,
                created_at  REAL NOT NULL,
                mode        TEXT NOT NULL,
                brief       TEXT NOT NULL,
                outputs     TEXT NOT NULL,
                status      TEXT NOT NULL
            )
            """
        )


def create_run(run_id: str, brief: dict, mode: str):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO runs (id, created_at, mode, brief, outputs, status) "
            "VALUES (?,?,?,?,?,?)",
            (run_id, time.time(), mode, json.dumps(brief), json.dumps({}), "running"),
        )


def finalize_run(run_id: str, outputs: dict, status: str = "complete"):
    with _conn() as c:
        c.execute(
            "UPDATE runs SET outputs=?, status=? WHERE id=?",
            (json.dumps(outputs), status, run_id),
        )


def get_run(run_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def list_runs(limit: int = 50) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "mode": row["mode"],
        "brief": json.loads(row["brief"]),
        "outputs": json.loads(row["outputs"]),
        "status": row["status"],
    }
