from pathlib import Path

from app.store import db


def test_migrations_apply_and_set_version(tmp_path: Path) -> None:
    conn = db.connect(tmp_path / "m.sqlite3")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version == db.SCHEMA_VERSION
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "settings" in tables
    conn.close()


def test_reconnect_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "m.sqlite3"
    conn1 = db.connect(path)
    db.put_settings(conn1, {"a": 1})
    conn1.close()
    conn2 = db.connect(path)  # migrations must not wipe data
    assert db.get_settings(conn2) == {"a": 1}
    conn2.close()


def test_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "m.sqlite3"
    conn = db.connect(path)
    assert path.exists()
    conn.close()
