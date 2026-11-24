"""Regressions for the client's testing notes (Lite/production build)."""
from src.data.models import Property
from src.ui.main_window import MainWindow


def _close_window(kekar_app, window):
    try:
        kekar_app.data_changed.disconnect(window.reload_all)
    except (TypeError, RuntimeError):
        pass
    window.close()


def test_lease_property_selector_is_populated_at_startup(kekar_app):
    """Note 1: Lease > Property must list the properties already in data."""
    kekar_app.property_repo.create(Property(address="99 Lease Lane"))
    window = MainWindow(kekar_app)
    try:
        labels = [window.lease_tab.property_combo.itemText(i)
                  for i in range(window.lease_tab.property_combo.count())]
        assert any("99 Lease Lane" in label for label in labels)
    finally:
        _close_window(kekar_app, window)


def test_applicant_property_cell_is_a_populated_combo(kekar_app):
    """Note 2: Applicants > Property lists the live properties."""
    pid = kekar_app.property_repo.create(Property(address="55 Applicant Way"))
    kekar_app.applicant_repo.create(
        __import__("src.data.models", fromlist=["Applicant"]).Applicant(
            applicant_name="Test Person", property_id=pid))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    combo = tab.table.cellWidget(0, 1)
    assert combo is not None
    labels = [combo.itemText(i) for i in range(combo.count())]
    assert any("55 Applicant Way" in label for label in labels)
    assert combo.currentData() == pid


def test_applicant_property_combo_saves_the_new_link(kekar_app):
    from src.data.models import Applicant

    first = kekar_app.property_repo.create(Property(address="First Rental"))
    second = kekar_app.property_repo.create(Property(address="Second Rental"))
    aid = kekar_app.applicant_repo.create(
        Applicant(applicant_name="Mover", property_id=first))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    combo = tab.table.cellWidget(0, 1)
    index = combo.findData(second)
    combo.setCurrentIndex(index)
    assert kekar_app.applicant_repo.get(aid).property_id == second


def test_lease_property_selector_refreshes_after_save(kekar_app):
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
