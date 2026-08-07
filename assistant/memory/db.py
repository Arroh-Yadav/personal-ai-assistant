"""SQLite connection and schema setup.

Provides get_connection() and init_db() helpers. The DB file lives at
`data/assistant.db` relative to the project root.
"""
from pathlib import Path
import sqlite3
from typing import Generator

DB_FILENAME = 'assistant.db'


def _project_root() -> Path:
    # assistant/memory/db.py -> project_root is two levels up
    return Path(__file__).resolve().parents[2]


def get_db_path() -> Path:
    data_dir = _project_root() / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / DB_FILENAME


def get_connection() -> sqlite3.Connection:
    path = str(get_db_path())
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create required tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # conversations table (from docs/06)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user','assistant','tool')),
            content TEXT NOT NULL,
            tool_name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, created_at);
        """
    )

    conn.commit()
    conn.close()


# Initialize DB on import to make the app easier to run.
init_db()
