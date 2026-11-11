"""SQLite connection management, schema migration, integrity checking."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..paths import database_path
from ._schema_embedded import embedded_schema

SCHEMA_VERSION = 1
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class Database:
    def __init__(self, path: Path | None = None, migrate: bool = True):
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=5.0,
                                    isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._configure()
        if migrate:
            self._migrate()

    def _configure(self) -> None:
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")

    def _migrate(self) -> None:
        # executescript() commits any pending transaction itself, so there must
        # be no explicit BEGIN/COMMIT wrapper here — it makes COMMIT/ROLLBACK
        # fail with "no transaction is active". The schema is idempotent
        # (CREATE ... IF NOT EXISTS), so re-running migration is safe.
        script = embedded_schema()
        self.conn.executescript(script)
        self.conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SCHEMA_VERSION),),
        )

    def integrity_check(self) -> bool:
        row = self.conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row) and row[0] == "ok"

    def close(self) -> None:
        try:
            self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        finally:
            self.conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
