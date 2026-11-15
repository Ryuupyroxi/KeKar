"""Accounts and sessions: the login plumbing for the client-facing feature.

There is no portal yet. This repository and the auth service exist so that the
feature which needs a login has somewhere real to put it, rather than a
homegrown password check invented alongside it.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..services import auth

ROLES = ("owner", "member")


def _row_to_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


class UserRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        """A connection owned by the calling thread (see PropertyRepo)."""
        db = self._db
        return db.conn if hasattr(db, "conn") else db

    def create(self, username: str, password: str, display_name: str = "",
               role: str = "member") -> int:
        if role not in ROLES:
            raise ValueError(f"invalid role: {role}")
        cur = self.conn.execute(
            "INSERT INTO users (username, display_name, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            (username, display_name, auth.hash_password(password), role))
        return int(cur.lastrowid)

    def get(self, user_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _row_to_user(row) if row else None

    def get_by_username(self, username: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM users WHERE username=? COLLATE NOCASE",
            (username,)).fetchone()
        return _row_to_user(row) if row else None

    def list(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM users ORDER BY username COLLATE NOCASE")
        return [_row_to_user(r) for r in rows]

    def delete(self, user_id: int) -> None:
        self.conn.execute("DELETE FROM users WHERE id=?", (user_id,))

    def set_password(self, user_id: int, password: str) -> None:
        self.conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (auth.hash_password(password), user_id))

    def authenticate(self, username: str, password: str) -> dict | None:
        """The user record when the password matches, else None.

        An unknown username returns None without running the KDF, so the cost of
        a wrong guess is the same whether or not the account exists.
        """
        user = self.get_by_username(username)
        if user is None:
            # Spend comparable effort so timing does not reveal whether the
            # account exists.
            auth.verify_password(password, auth.hash_password(password))
            return None
        if not auth.verify_password(password, user["password_hash"]):
            return None
        return user

    # -- sessions ----------------------------------------------------------

    def create_session(self, user_id: int,
                       now: datetime | None = None) -> str:
        token = auth.new_session_token()
        now = now or datetime.now(timezone.utc)
        self.conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(), auth.session_expiry(now)))
        return token

    def session_user(self, token: str) -> dict | None:
        """The user behind a live session token, or None."""
        if not token:
            return None
        row = self.conn.execute(
            "SELECT u.*, s.expires_at FROM users u "
            "JOIN sessions s ON s.user_id = u.id WHERE s.token = ?",
            (token,)).fetchone()
        if row is None:
            return None
        if auth.is_expired(row["expires_at"]):
            self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        return _row_to_user(row)

    def delete_session(self, token: str) -> None:
        self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def purge_expired(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            "DELETE FROM sessions WHERE expires_at <= ?", (now,))
        return cur.rowcount

    def count_users(self) -> int:
        return int(self.conn.execute(
            "SELECT COUNT(*) FROM users").fetchone()[0])
