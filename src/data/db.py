"""SQLite connection management, schema migration, integrity checking."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from ..paths import database_path
from ._schema_embedded import embedded_schema

SCHEMA_VERSION = 1
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class Database:
    """A SQLite database that is safe to use from more than one thread.

    sqlite3 connections are pinned to the thread that created them by default,
    and the agent's tools run in a worker QThread. Rather than sharing one
    connection across threads (which needs locking everywhere), each thread
    gets its own connection to the same file. WAL mode makes that safe: one
    writer plus any number of readers.
    """

    def __init__(self, path: Path | None = None, migrate: bool = True):
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._migrate_enabled = migrate
        if migrate:
            # Run once on the creating thread so a broken schema fails fast.
            self._migrate(self.conn)

    @property
    def conn(self) -> sqlite3.Connection:
        """A connection owned by the calling thread."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.path), timeout=5.0,
                                   isolation_level=None,
                                   check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
            self._connections.append(conn)
            if self._migrate_enabled:
                self._migrate(conn)
        return conn

    def _migrate(self, conn: sqlite3.Connection | None = None) -> None:
        conn = conn if conn is not None else self.conn
        # executescript() commits any pending transaction itself, so there must
        # be no explicit BEGIN/COMMIT wrapper here — it makes COMMIT/ROLLBACK
        # fail with "no transaction is active". The schema is idempotent
        # (CREATE ... IF NOT EXISTS), so re-running migration is safe.
        conn.executescript(embedded_schema())
        conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SCHEMA_VERSION),),
        )

    def integrity_check(self) -> bool:
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row) and row[0] == "ok"

    def close(self) -> None:
        for conn in self._connections:
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass
            try:
                conn.close()
            except sqlite3.Error:
                pass
        self._connections.clear()
        self._local = threading.local()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
