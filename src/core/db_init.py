"""
Database Initialization - SQLite schema setup for audit logs and app data.
"""

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    user        TEXT    NOT NULL DEFAULT 'system',
    details     TEXT,
    signature   TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_logs(action);

CREATE TABLE IF NOT EXISTS user_preferences (
    key         TEXT PRIMARY KEY,
    value_enc   BLOB    NOT NULL,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversation_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role        TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversation_history(timestamp);
"""


def init_database(db_path: str = "data/jarvis.db") -> sqlite3.Connection:
    """
    Initialize the SQLite database with the required schema.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Open database connection
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def get_connection(db_path: str = "data/jarvis.db") -> sqlite3.Connection:
    """Return a connection to an already-initialized database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
