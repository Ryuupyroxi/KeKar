from __future__ import annotations

import sqlite3


class ChatRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        """A connection owned by the calling thread (see PropertyRepo)."""
        db = self._db
        return db.conn if hasattr(db, "conn") else db

    def add(self, role: str, content: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO chat_messages (role, content) VALUES (?, ?)",
            (role, content))
        return int(cur.lastrowid)

    def history(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content FROM chat_messages "
            "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"role": r["role"], "content": r["content"]}
                for r in reversed(rows)]

    def clear(self) -> None:
        self.conn.execute("DELETE FROM chat_messages")
