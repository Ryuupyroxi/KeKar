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
        # Demo mode seeds on entry, so it is populated — but with none of the
        # real user's records.
        assert demo_repo.list() != [], "demo database should be seeded"
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


def test_seed_populates_an_empty_database(db):
    from src.data import demo_seed

    assert demo_seed.seed_if_empty(db) is True
    assert len(PropertyRepo(db).list()) == 4


def test_seed_is_idempotent(db):
    from src.data import demo_seed

    demo_seed.seed_if_empty(db)
    assert demo_seed.seed_if_empty(db) is False
    assert len(PropertyRepo(db).list()) == 4


def test_enter_demo_mode_seeds_once(kekar_app):
    kekar_app.enter_demo_mode()
    try:
        assert len(PropertyRepo(kekar_app.db).list()) == 4
    finally:
        kekar_app.exit_demo_mode()


def test_seed_content(db):
    from src.data import demo_seed
    from src.data.applicant_repo import ApplicantRepo

    demo_seed.seed_if_empty(db)
    props = {p.address: p for p in PropertyRepo(db).list()}
    assert set(props) == {
        "123 Main Street", "456 Oak Avenue",
        "789 Elm Lane", "321 Pine Court"}
    assert props["123 Main Street"].rent_price == 1200.0
    assert props["456 Oak Avenue"].status == "Rented"
    assert props["789 Elm Lane"].amenity_yard is True

    stages = {a.screening_stage for a in ApplicantRepo(db).list()}
    assert stages == {"Inquiry Received", "Background Check",
                      "Approved", "Rejected"}


def test_tour_completed_defaults_false(kekar_app):
    assert kekar_app.settings.tour_completed is False


def test_banner_is_hidden_until_demo_mode(kekar_app):
    from src.ui.widgets import DemoBanner

    banner = kekar_app.main_window.demo_banner
    assert isinstance(banner, DemoBanner)
    assert banner.isHidden()

    kekar_app.enter_demo_mode()
    assert kekar_app.main_window.demo_mode is True
    kekar_app.exit_demo_mode()
    assert kekar_app.main_window.demo_mode is False


def test_settings_disabled_in_demo_mode(kekar_app):
    window = kekar_app.main_window
    assert window.settings_action.isEnabled() is True
    kekar_app.enter_demo_mode()
    assert window.settings_action.isEnabled() is False
    kekar_app.exit_demo_mode()
    assert window.settings_action.isEnabled() is True


def test_exit_demo_action_visible_only_in_demo(kekar_app):
    window = kekar_app.main_window
    assert window.exit_demo_action.isVisible() is False

    kekar_app.enter_demo_mode()
    assert window.exit_demo_action.isVisible() is True

    kekar_app.exit_demo_mode()
    assert window.exit_demo_action.isVisible() is False


def test_maybe_offer_tour_sets_the_flag(kekar_app):
    kekar_app.settings.tour_completed = False
    try:
        kekar_app.maybe_offer_tour()
        assert kekar_app.settings.tour_completed is True
    finally:
        # The dialog is patched to "Yes" in tests, so demo mode is left on.
        kekar_app.exit_demo_mode()
    assert kekar_app.demo_mode is False


def test_maybe_offer_tour_does_nothing_once_completed(kekar_app):
    kekar_app.settings.tour_completed = True
    kekar_app.maybe_offer_tour()
    assert kekar_app.demo_mode is False
