"""Button-feedback regressions found in the QA sweep."""
import time

from PIL import Image

from src.data.models import Property
from src.services import image_service
from src.ui import worker


def test_hidden_thumbnails_are_not_photos(kekar_app, monkeypatch):
    pid = kekar_app.property_repo.create(Property(address="1 QA Lane"))
    folder = image_service._property_dir(pid)
    folder.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), "red").save(folder / "01_real.jpg")
    Image.new("RGB", (4, 4), "blue").save(folder / ".thumb_240_01_real.jpg")
    names = [p.name for p in image_service.property_photos(pid)]
    assert names == ["01_real.jpg"]


def test_set_cover_reports_single_photo(kekar_app):
    pid = kekar_app.property_repo.create(Property(address="2 QA Lane"))
    folder = image_service._property_dir(pid)
    folder.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), "red").save(folder / "01_only.jpg")
    assert image_service.set_cover(pid, folder / "01_only.jpg") is False


def test_status_button_without_selection_explains_why(kekar_app, monkeypatch):
    from src.ui import property_form

    messages = []
    monkeypatch.setattr(property_form.QMessageBox, "information",
                        lambda *args: messages.append(args[-1]))
    form = kekar_app.main_window.property_form
    form.load_property(None)
    form._set_status("Rented")
    assert any("saved property" in message for message in messages)


def test_test_connection_does_not_commit_on_cancel(kekar_app, monkeypatch):
    from src import features
    from src.ui import settings_dialog

    if features.is_lite():
        return

    def fake_run(self):
        self.done.emit(False, "nope")

    monkeypatch.setattr(settings_dialog._ProviderThread, "run", fake_run)
    dialog = settings_dialog.SettingsDialog(kekar_app)
    original = kekar_app.settings.api_key
    dialog.key_input.setText("temporary-key")
    dialog.provider.setCurrentIndex(0)
    dialog._test_connection()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        kekar_app.processEvents()
        if dialog._thread is None:
            break
        time.sleep(0.01)
    assert kekar_app.settings.api_key == original
    assert dialog.test_btn.text() == "Test connection"


def test_offline_pill_keeps_its_meaning_after_theme_change(kekar_app):
    from src import features

    if features.is_lite():
        return
    window = kekar_app.main_window
    window.show_offline(True)
    window.apply_theme(kekar_app.current_theme())
    assert window.status_pill.text() == "Offline"
    assert kekar_app.current_theme().offline in window.status_pill.styleSheet()


def test_stays_keeps_selected_property_on_reload(kekar_app):
    first = kekar_app.property_repo.create(Property(address="First"))
    second = kekar_app.property_repo.create(Property(address="Second"))
    tab = kekar_app.main_window.stays_tab
    tab.reload()
    index = tab.property_combo.findData(second)
    tab.property_combo.setCurrentIndex(index)
    tab.reload()
    assert tab.property_combo.currentData() == second


def test_listing_copy_shows_feedback_inside_dialog(kekar_app, monkeypatch):
    from src.ui import listing_dialog

    monkeypatch.setattr(listing_dialog, "copy_text", lambda text: None)
    prop = Property(address="3 QA Lane", rent_price=700)
    dialog = listing_dialog.ListingDialog(kekar_app, prop)
    dialog._copy()
    assert "copied" in dialog.copy_note.text().lower()
    dialog.close()
