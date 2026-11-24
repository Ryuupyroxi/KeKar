"""GUI smoke tests.

These use the shared session `kekar_app` fixture from conftest.py rather than
pytest-qt's `qtbot`. qtbot creates a plain QApplication, which would stop our
Application subclass from ever being constructed (`QApplication.instance()`
returns whichever object was created first).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.data.applicant_repo import ApplicantRepo
from src.data.models import Applicant, Property
from src.data.property_repo import PropertyRepo


def test_app_constructs(kekar_app):
    assert kekar_app.main_window.windowTitle().startswith("KeKar")


def test_offline_banner_toggles(kekar_app):
    kekar_app.main_window.show_offline(True)
    assert kekar_app.main_window.offline_banner.isVisibleTo(kekar_app.main_window)
    kekar_app.main_window.show_offline(False)
    assert not kekar_app.main_window.offline_banner.isVisibleTo(kekar_app.main_window)


def test_drawer_lists_properties(kekar_app):
    repo = PropertyRepo(kekar_app.db.conn)
    before = len(repo.list())
    repo.create(Property(address="1 Drawer Way"))
    drawer = kekar_app.main_window.drawer
    drawer.reload()
    assert drawer.count() == before + 1


def test_form_loads_property(kekar_app):
    pid = PropertyRepo(kekar_app.db.conn).create(Property(
        address="2 Form St", rent_price=725.0, bedrooms=2))
    form = kekar_app.main_window.property_form
    form.load_property(pid)
    assert form.address_input.text() == "2 Form St"
    assert form.rent_input.value() == 725


def test_form_save_creates_property(kekar_app):
    form = kekar_app.main_window.property_form
    form.load_property(None)
    form.address_input.setText("3 Saved Pl")
    form.rent_input.setValue(900)
    form.save()
    assert form.current_id is not None
    assert kekar_app.property_repo.get(form.current_id).address == "3 Saved Pl"


def test_photo_panel_imports(kekar_app, tmp_path):
    from pathlib import Path
    from PIL import Image
    pid = PropertyRepo(kekar_app.db.conn).create(Property(address="3 Photo Pl"))
    src = tmp_path / "p.jpg"
    Image.new("RGB", (800, 600), (10, 20, 30)).save(src, "JPEG")
    panel = kekar_app.main_window.photo_panel
    panel.load_property(pid)
    panel.import_photos([Path(src)])
    assert len(panel.paths) == 1


# -- collapsible Photos section -------------------------------------------

def test_photos_section_collapses_and_expands(kekar_app):
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest

    panel = kekar_app.main_window.photo_panel
    assert panel.is_collapsed() is False
    assert panel.body.isVisibleTo(panel)

    QTest.mouseClick(panel.toggle_btn, Qt.MouseButton.LeftButton)
    kekar_app.processEvents()
    assert panel.is_collapsed() is True
    assert not panel.body.isVisibleTo(panel)
    assert kekar_app.settings.photos_collapsed is True

    QTest.mouseClick(panel.toggle_btn, Qt.MouseButton.LeftButton)
    kekar_app.processEvents()
    assert panel.is_collapsed() is False
    assert panel.body.isVisibleTo(panel)
    assert kekar_app.settings.photos_collapsed is False


def test_photos_collapse_is_remembered_between_runs(kekar_app):
    """A rebuilt panel (i.e. the next launch) starts from the setting."""
    from src.ui.photo_panel import PhotoPanel

    original = kekar_app.settings.photos_collapsed
    try:
        kekar_app.settings.photos_collapsed = True
        assert PhotoPanel(kekar_app).is_collapsed() is True
        kekar_app.settings.photos_collapsed = False
        assert PhotoPanel(kekar_app).is_collapsed() is False
    finally:
        kekar_app.settings.photos_collapsed = original


def test_crm_lists_applicants(kekar_app):
    repo = ApplicantRepo(kekar_app.db.conn)
    before = len(repo.list())
    repo.create(Applicant(applicant_name="CRM Person"))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    assert tab.table.rowCount() == before + 1


def test_chat_pane_shows_messages(kekar_app):
    pane = kekar_app.main_window.chat_pane
    pane.add_message("user", "hello")
    pane.add_message("assistant", "hi there")
    assert "hello" in pane.view.toPlainText()
    assert "hi there" in pane.view.toPlainText()


def test_wizard_rejects_empty_key(kekar_app):
    from src.ui.wizard import FirstRunWizard
    wizard = FirstRunWizard(kekar_app)
    wizard.key_input.setText("")
    ok, msg = wizard.test_connection()
    assert ok is False


def test_settings_dialog_opens(kekar_app):
    from src.ui.settings_dialog import SettingsDialog
    dialog = SettingsDialog(kekar_app)
    assert dialog.isVisible() is False
    dialog.open()
    assert dialog.isVisible() is True


# -- '+ Add New Property' --------------------------------------------------

def _add_button(window):
    """The drawer's add button, found by its label.

    It is created as a local inside PropertyDrawer, so the suite reaches it
    through the widget tree rather than a new attribute.
    """
    from PyQt6.QtWidgets import QPushButton
    hits = [b for b in window.drawer.findChildren(QPushButton)
            if "Add New Property" in b.text()]
    assert len(hits) == 1, f"expected one add button, found {len(hits)}"
    return hits[0]


def test_add_new_property_gives_visible_feedback(kekar_app):
    """Clicking '+ Add New Property' must always be unmistakable.

    The form is taller than its viewport. A click that only cleared the fields
    was invisible whenever the view happened to be scrolled past the top: the
    pill and the address field were both off-screen, so the button looked dead.
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest

    window = kekar_app.main_window
    form = window.property_form
    window.show()
    kekar_app.processEvents()

    pid = PropertyRepo(kekar_app.db.conn).create(
        Property(address="4 Feedback Rd", rent_price=640.0))
    form.load_property(pid)
    assert form.current_id == pid
    assert form.pill.text() != "New property"

    scroll = window.form_scroll.verticalScrollBar()
    scroll.setValue(scroll.maximum())       # worst case: scrolled past the top
    window.tabs.setCurrentIndex(2)          # and not even on Properties

    QTest.mouseClick(_add_button(window), Qt.MouseButton.LeftButton)
    kekar_app.processEvents()

    assert window.tabs.currentIndex() == 0
    assert form.current_id is None
    assert form.address_input.text() == ""
    assert form.pill.text() == "New property"
    assert scroll.value() == 0, "the form must scroll back to the address field"
    assert "New property" in window.statusBar().currentMessage()


def test_add_new_property_works_from_an_empty_portfolio(kekar_app):
    """A second click on an already-blank form still reports what happened."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest

    window = kekar_app.main_window
    form = window.property_form
    window.show()
    kekar_app.processEvents()

    QTest.mouseClick(_add_button(window), Qt.MouseButton.LeftButton)
    kekar_app.processEvents()
    QTest.mouseClick(_add_button(window), Qt.MouseButton.LeftButton)
    kekar_app.processEvents()

    assert form.current_id is None
    assert form.pill.text() == "New property"
    assert form.address_input.hasFocus()
    assert "New property" in window.statusBar().currentMessage()
