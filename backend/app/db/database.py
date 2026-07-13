"""SQLite connection management and schema initialization.

A single module-level connection (``check_same_thread=False``) guarded by a lock
is plenty for the app's low write concurrency and keeps the free-tier footprint
tiny. The database file lives under the configurable data dir so it survives on a
mounted persistent volume in the cloud.
"""

from __future__ import annotations

import sqlite3
import threading

from app.core.config import settings
from app.core.logging_setup import get_logger

log = get_logger("db")

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT 'New chat',
    kb_name     TEXT,
    provider    TEXT,
    model       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL DEFAULT '',
    sources_json TEXT,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

CREATE TABLE IF NOT EXISTS kb_meta (
    kb_name     TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    examples_json TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply lightweight, idempotent schema migrations for pre-existing DBs."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(kb_meta)").fetchall()}
    if "examples_json" not in cols:
        conn.execute("ALTER TABLE kb_meta ADD COLUMN examples_json TEXT NOT NULL DEFAULT '[]'")
        conn.commit()


def get_conn() -> sqlite3.Connection:
    """Return the shared SQLite connection, creating + initializing it once."""
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is not None:
            return _conn
        settings.ensure_dirs()
        conn = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # WAL lets readers and a writer work concurrently; busy_timeout makes
        # writers wait-and-retry (instead of hanging/erroring) under contention.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
        _conn = conn
        log.info("SQLite ready at %s", settings.sqlite_path)
        return _conn


def init_db() -> None:
    """Eagerly create the database + schema (called at app startup)."""
    get_conn()


def write_lock() -> threading.Lock:
    """Return the shared lock to serialize writes."""
    return _lock
