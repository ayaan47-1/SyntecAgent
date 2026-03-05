"""Storage module — compatibility shim backed by SQLite via agent/db.py."""

from agent.db import get_db, init_db  # noqa: F401 (re-exported for backwards compat)

__all__ = ["get_db", "init_db"]
