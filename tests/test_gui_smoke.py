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
