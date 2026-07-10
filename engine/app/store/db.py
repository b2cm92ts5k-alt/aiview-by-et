"""SQLite storage with versioned SQL migrations.

Migration policy (see MEMORY.md #no-silent-schema-change):
- never drop/rename an existing column in-place
- additive changes only, each as a new (version, sql) entry
- PRAGMA user_version tracks the applied schema version
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS signals (
            id         TEXT PRIMARY KEY,
            symbol     TEXT NOT NULL,
            tf         TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            payload    TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol, created_at DESC);
        """,
    ),
]

SCHEMA_VERSION = MIGRATIONS[-1][0]


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite db and apply pending migrations."""
    path = Path(db_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, sql in MIGRATIONS:
        if version > current:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.commit()


def get_settings(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: json.loads(row["value"]) for row in rows}


def save_signal(conn: sqlite3.Connection, signal_id: str, symbol: str, tf: str,
                created_at: int, payload: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO signals (id, symbol, tf, created_at, payload) VALUES (?, ?, ?, ?, ?)",
        (signal_id, symbol, tf, created_at, json.dumps(payload)),
    )
    conn.commit()


def list_signals(conn: sqlite3.Connection, symbol: str | None = None,
                 limit: int = 100) -> list[dict[str, Any]]:
    if symbol:
        rows = conn.execute(
            "SELECT payload FROM signals WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT payload FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def put_settings(conn: sqlite3.Connection, patch: dict[str, Any]) -> dict[str, Any]:
    """Merge patch into stored settings; a null value deletes the key."""
    for key, value in patch.items():
        if value is None:
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        else:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value)),
            )
    conn.commit()
    return get_settings(conn)
