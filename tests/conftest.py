import os

# Headless CI: use Qt's offscreen platform when there is no display. A real
# desktop session keeps the normal platform so the GUI can actually be seen.
if (os.name != "nt"
        and not os.environ.get("DISPLAY")
        and not os.environ.get("WAYLAND_DISPLAY")):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from src.data.db import Database


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    """Every test runs against its own throwaway KeKarData directory."""
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path / "KeKarData"))


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
