import os
import shutil
from pathlib import Path

# Headless CI: use Qt's offscreen platform when there is no display. A real
# desktop session keeps the normal platform so the GUI can actually be seen.
if (os.name != "nt"
        and not os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# The UI pings the provider to drive the offline banner. Tests never network.
os.environ.setdefault("KEKAR_TESTING", "1")

import pytest

from src.data.db import Database


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """Every test runs against its own throwaway KeKarData directory."""
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path / "KeKarData"))


@pytest.fixture(autouse=True)
def _empty_portfolio(kekar_app):
    """Start every test from an empty portfolio.

    There can be only one QApplication per process, so the Application (and
    its database connection) is session-scoped and would otherwise accumulate
    rows across tests. Photos are removed via the app's own data directory
    rather than ``photos_dir()``, which follows the per-test env var.
    """
    root = Path(kekar_app.db.path).parent
    for prop in kekar_app.property_repo.list():
        kekar_app.property_repo.delete(prop.id)
    for applicant in kekar_app.applicant_repo.list():
        kekar_app.applicant_repo.delete(applicant.id)
    for lease in kekar_app.lease_repo.list():
        kekar_app.lease_repo.delete(lease.id)
    for user in kekar_app.user_repo.list():
        kekar_app.user_repo.delete(user["id"])
    kekar_app.chat_repo.clear()
    shutil.rmtree(root / "photos", ignore_errors=True)
    kekar_app.main_window.reload_all()
    yield


@pytest.fixture(autouse=True)
def _no_blocking_dialogs(monkeypatch):
    """Modal message boxes would block forever on the offscreen platform.

    Tests that care about a dialog's answer monkeypatch it themselves; this
    fixture only guarantees the suite can never hang on an unpatched one.
    """
    from PyQt6.QtWidgets import QInputDialog, QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    # A cancelled picker, so any code path that asks which property an
    # applicant belongs to simply does nothing instead of blocking.
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("", False))


@pytest.fixture
def db():
    database = Database()
    yield database
    database.close()


@pytest.fixture(scope="session")
def kekar_app():
    """KeKar's Application *is* the QApplication — create it exactly once.

    Kept here so every test file shares one instance, and so it is created
    before any test module can make a plain QApplication of its own.
    """
    from PyQt6.QtWidgets import QApplication

    from src.app import Application

    assert QApplication.instance() is None, (
        "a plain QApplication already exists; KeKar's Application must be "
        "created first")
    application = Application([])
    yield application
    application.main_window.close()
