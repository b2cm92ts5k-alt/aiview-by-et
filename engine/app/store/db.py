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
