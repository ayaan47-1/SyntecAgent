"""SQLite database connection and schema for classifications."""

import os
import json
import sqlite3
import threading
import logging

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "classifications.db"
)

_local = threading.local()


def get_db() -> sqlite3.Connection:
    """Return a thread-local SQLite connection to _DB_PATH.

    Re-opens the connection if the path has changed (e.g. patched in tests).
    """
    conn = getattr(_local, "conn", None)
    cached_path = getattr(_local, "db_path", None)
    if conn is None or cached_path != _DB_PATH:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
        _local.db_path = _DB_PATH
    return conn


def init_db() -> None:
    """Create schema if not exists, then migrate from JSON if present."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            sheet       TEXT DEFAULT '',
            category    TEXT DEFAULT '',
            source      TEXT DEFAULT 'agent',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_code ON classifications(code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON classifications(category)")
    conn.commit()
    _migrate_from_json(conn)


def _migrate_from_json(conn: sqlite3.Connection) -> None:
    """One-time migration from modules_db.json to SQLite if the JSON file exists."""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modules_db.json"
    )
    if not os.path.exists(json_path):
        return

    # Skip if agent rows already exist (migration already done)
    row = conn.execute(
        "SELECT COUNT(*) FROM classifications WHERE source = 'agent'"
    ).fetchone()
    if row[0] > 0:
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modules = data.get("modules", {})
        for name, info in modules.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO classifications
                    (code, name, description, source, created_at, updated_at)
                VALUES (?, ?, ?, 'agent', ?, ?)
                """,
                (
                    info.get("code", "") or None,
                    name,
                    info.get("description", ""),
                    info.get("created_at", ""),
                    info.get("updated_at", ""),
                ),
            )
        conn.commit()
        logger.info(f"Migrated {len(modules)} modules from modules_db.json to SQLite")
    except Exception as e:
        logger.warning(f"JSON migration failed (non-fatal): {e}")
