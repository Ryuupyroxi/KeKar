"""SQLite backup, restore, verification, and automatic corruption recovery."""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..paths import backups_dir
from .db import Database


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def _days_since(path: Path) -> float:
    from time import time
    return (time() - path.stat().st_mtime) / 86400


def create_backup(db: Database, label: str = "") -> Path:
    target = backups_dir() / f"{_timestamp()}{('-' + label) if label else ''}"
    target.mkdir(parents=True, exist_ok=True)
    db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    dest = sqlite3.connect(str(target / "database.db"))
    try:
        with dest:
            db.conn.backup(dest)
    finally:
        dest.close()
    return target


def verify_backup(backup_dir: Path) -> bool:
    path = backup_dir / "database.db"
    if not path.exists():
        return False
    try:
        conn = sqlite3.connect(str(path))
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            return bool(row) and row[0] == "ok"
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def restore_backup(db: Database, backup_dir: Path) -> None:
    """Restore a backup into the live database connection, in place.

    Uses SQLite's online backup API so every existing repository object keeps
    its connection — no reconnect, no stale handles.
    """
    src = backup_dir / "database.db"
    if not src.exists():
        raise FileNotFoundError(f"no database in {backup_dir}")
    if not verify_backup(backup_dir):
        raise RuntimeError(f"backup failed integrity check: {backup_dir}")
    db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    source = sqlite3.connect(str(src))
    try:
        source.backup(db.conn)
    finally:
        source.close()


def list_backups() -> list[Path]:
    root = backups_dir()
    if not root.exists():
        return []
    return sorted((p for p in root.iterdir() if p.is_dir()),
                  key=lambda p: p.name, reverse=True)


def prune_backups(keep_days: int = 30) -> int:
    removed = 0
    for path in list_backups():
        if _days_since(path) > keep_days:
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    return removed


def open_with_recovery(path: Path | None) -> Database:
    """Open the database; if it is corrupt, swap in the newest good backup."""
    try:
        db = Database(path)
        if db.integrity_check():
            return db
        db.close()
    except sqlite3.DatabaseError:
        pass

    target = Path(path) if path else database_path()
    for candidate in list_backups():
        if not verify_backup(candidate):
            continue
        src = candidate / "database.db"
        # Replace the damaged file wholesale, then open and migrate normally.
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        shutil.copy2(src, target)
        db = Database(target)
        if db.integrity_check():
            return db
        db.close()

    raise RuntimeError(
        "The local database is damaged and no usable backup was found. "
        "Please contact support before continuing.")
