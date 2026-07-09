"""Engine entrypoint — spawned by Electron main (dev: `python -m app.main --port N`).

Reads from environment (set by Electron main, TDD.md §2):
- ENGINE_TOKEN : per-session auth token (no token = open, dev/test only)
- AIVIEW_DB    : SQLite file path (default: ./aiview.sqlite3)
"""

from __future__ import annotations

import argparse
import os

import uvicorn

from app.api.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="aiview-engine")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    app = create_app(
        db_path=os.environ.get("AIVIEW_DB", "aiview.sqlite3"),
        token=os.environ.get("ENGINE_TOKEN") or None,
    )
    # loopback only — never expose to the network (TDD.md §9)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
