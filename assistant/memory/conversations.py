"""Conversation persistence helpers.

save_turn(session_id, role, content, tool_name=None)
load_recent(session_id, limit=20)
"""
from typing import List, Dict, Optional
from . import db


def save_turn(session_id: str, role: str, content: str, tool_name: Optional[str] = None) -> int:
    """Save a turn to the conversations table. Returns the inserted row id."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO conversations (session_id, role, content, tool_name)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, role, content, tool_name),
    )
    conn.commit()
    rowid = cur.lastrowid
    conn.close()
    return rowid


def load_recent(session_id: str, limit: int = 20) -> List[Dict[str, str]]:
    """Load the most recent `limit` turns for a session.

    Returns a list ordered chronologically (oldest first).
    """
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content, tool_name, created_at
        FROM conversations
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cur.fetchall()
    conn.close()

    # rows are newest-first; reverse to return oldest-first
    turns = []
    for r in reversed(rows):
        turns.append({
            'role': r['role'],
            'content': r['content'],
            'tool_name': r['tool_name'],
            'created_at': r['created_at'],
        })
    return turns
