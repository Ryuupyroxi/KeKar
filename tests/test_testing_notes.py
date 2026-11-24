"""Regressions for the client's testing notes (Lite/production build)."""
from src.data.models import Property
from src.ui.main_window import MainWindow


def _close_window(kekar_app, window):
    try:
        kekar_app.data_changed.disconnect(window.reload_all)
    except (TypeError, RuntimeError):
        pass
    window.close()


def test_lease_property_selector_is_populated_at_startup(kekar_app, monkeypatch):
    """Note 1: Lease > Property must list the properties already in data."""
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    kekar_app.property_repo.create(Property(address="99 Lease Lane"))
    window = MainWindow(kekar_app)
    try:
        labels = [window.lease_tab.property_combo.itemText(i)
                  for i in range(window.lease_tab.property_combo.count())]
        assert any("99 Lease Lane" in label for label in labels)
    finally:
        _close_window(kekar_app, window)


def test_lease_property_selector_refreshes_after_save(kekar_app, monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    window = MainWindow(kekar_app)
    try:
        before = window.lease_tab.property_combo.count()
        kekar_app.property_repo.create(Property(address="100 New Lane"))
        window._on_property_saved(
            kekar_app.property_repo.list()[-1].id)
        labels = [window.lease_tab.property_combo.itemText(i)
                  for i in range(window.lease_tab.property_combo.count())]
        assert len(labels) == before + 1
        assert any("100 New Lane" in label for label in labels)
    finally:
        _close_window(kekar_app, window)
