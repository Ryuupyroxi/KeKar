"""Demo mode: a separate database, leaving the user's real one untouched."""
from pathlib import Path

from src.data.db import Database
from src.data.property_repo import PropertyRepo
from src.data.models import Property
from src.paths import data_dir, demo_database_path


def test_demo_path_is_separate():
    assert demo_database_path() != data_dir() / "database.db"
    assert demo_database_path().name == "database.db"
    assert demo_database_path().parent.name == "demo"


def test_enter_and_exit_demo_mode(kekar_app):
    real_repo = PropertyRepo(kekar_app.db)
    real_id = real_repo.create(Property(address="1 Real Street"))

    kekar_app.enter_demo_mode()
    try:
        assert kekar_app.demo_mode is True
        demo_repo = PropertyRepo(kekar_app.db)
        assert demo_repo.list() == [], "demo database should start empty"
        assert demo_repo.get(real_id) is None, "real property leaked into demo"
    finally:
        kekar_app.exit_demo_mode()

    assert kekar_app.demo_mode is False
    assert PropertyRepo(kekar_app.db).get(real_id) is not None, (
        "real property vanished after leaving demo mode")


def test_demo_database_file_is_created(kekar_app):
    kekar_app.enter_demo_mode()
    try:
        assert kekar_app._demo_db_path.exists()
    finally:
        kekar_app.exit_demo_mode()


def test_demo_mode_keeps_the_database_it_started_with(kekar_app, monkeypatch):
    """If the data directory changes mid-session, leaving demo mode must still
    reopen the database the app started with — not whatever the directory
    resolves to now."""
    real_id = PropertyRepo(kekar_app.db).create(
        Property(address="1 Startup Street"))
    started_at = kekar_app._real_db_path

    monkeypatch.setenv("KEKAR_DATA_DIR", str(Path(started_at).parent / "elsewhere"))

    kekar_app.enter_demo_mode()
    kekar_app.exit_demo_mode()

    assert kekar_app._real_db_path == started_at
    assert PropertyRepo(kekar_app.db).get(real_id) is not None
