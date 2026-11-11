"""Bundle-safety tests.

The app must work when frozen by PyInstaller. In the bundle, .sql and .json
files next to the source are NOT shipped unless the spec lists them as data —
so anything the app needs at runtime must either be declared in KeKar.spec or
embedded in Python.
"""
import sys
from pathlib import Path

import pytest

from src.data import db as db_module
from src.data.db import Database, SCHEMA_VERSION, embedded_schema


def test_embedded_schema_is_non_empty():
    assert len(embedded_schema()) > 500


def test_embedded_schema_defines_all_tables():
    script = embedded_schema()
    for table in ("properties", "applicants", "applicant_docs",
                  "chat_messages", "listing_runs", "schema_meta"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in script


def test_embedded_schema_matches_version():
    assert SCHEMA_VERSION == 1


def test_migration_uses_embedded_schema_even_when_file_missing(tmp_path,
                                                                monkeypatch):
    """The bundle has no schema.sql — migration must still work."""
    missing = tmp_path / "nope.sql"
    monkeypatch.setattr(db_module, "_SCHEMA_PATH", missing)
    database = Database(path=tmp_path / "d" / "database.db")
    try:
        tables = {r[0] for r in database.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"properties", "applicants", "schema_meta"} <= tables
    finally:
        database.close()


def test_on_disk_schema_matches_embedded_copy():
    """If both exist they must not drift apart."""
    if not db_module._SCHEMA_PATH.exists():
        pytest.skip("schema.sql not present in this checkout")
    assert db_module._SCHEMA_PATH.read_text(encoding="utf-8") == embedded_schema()
