import pytest

from src.data.db import Database, SCHEMA_VERSION


def test_schema_created(db):
    tables = {r[0] for r in db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"properties", "applicants", "applicant_docs",
            "chat_messages", "listing_runs", "schema_meta"} <= tables


def test_integrity_check_ok(db):
    assert db.integrity_check() is True


def test_wal_mode_enabled(db):
    mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_foreign_keys_enforced(db):
    with pytest.raises(Exception):
        db.conn.execute(
            "INSERT INTO applicants(property_id, applicant_name) VALUES(999, 'X')")


def test_schema_version_recorded(db):
    row = db.conn.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
    assert row[0] == str(SCHEMA_VERSION)


def test_migration_is_idempotent(db):
    db._migrate()
    db._migrate()
    count = db.conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
    assert count == 0


def test_repos_work_from_another_thread(db):
    """The agent's tools run in a worker QThread, and sqlite3 pins a connection
    to the thread that made it. A repo built on a Database must still work
    there, or every tool call dies with "SQLite objects created in a thread can
    only be used in that same thread"."""
    import threading

    from src.data.property_repo import PropertyRepo
    from src.data.models import Property

    repo = PropertyRepo(db)
    problems: list[str] = []

    def worker():
        try:
            pid = repo.create(Property(address="1 Thread Way"))
            found = repo.get(pid)
            assert found is not None, "created property not found"
            assert found.address == "1 Thread Way"
            repo.set_status(pid, "Rented")
            assert repo.get(pid).status == "Rented"
        except Exception as exc:  # pragma: no cover - only on failure
            problems.append(f"{type(exc).__name__}: {exc}")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=20)

    assert not thread.is_alive(), "worker thread hung"
    assert not problems, problems
