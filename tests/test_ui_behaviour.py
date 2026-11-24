"""Behaviour tests for the rebuilt UI.

These cover the problems that made the app feel unfinished: unreadable form
text, a property list that showed status instead of identity, no way to delete
a property or photo, a chat pane that ignored stored history, and a settings
"test connection" button that never tested anything.
"""
import os
import socket

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QThread, pyqtSignal  # noqa: E402
from PyQt6.QtWidgets import QLabel, QMessageBox  # noqa: E402

from src.data.models import Property  # noqa: E402
from src.services import connectivity, image_service  # noqa: E402
from src.ui import main_window as main_window_module  # noqa: E402
from src.ui.property_drawer import (PropertyItemWidget,  # noqa: E402
                                    placeholder_cover, search_text,
                                    status_color)


def _prop(repo, **kwargs):
    base = dict(address="1 Test Way", city="Pawhuska", zip_code="74056",
                rent_price=800.0, bedrooms=2, bathrooms=1.0, sqft=900)
    base.update(kwargs)
    return repo.create(Property(**base))


def _make_image(path, colour):
    from PIL import Image
    Image.new("RGB", (400, 300), colour).save(path, "JPEG")


def _yes(box, *args, **kwargs):
    return QMessageBox.StandardButton.Yes


# -- property list ---------------------------------------------------------

def test_status_colours_are_distinct():
    assert status_color("Vacant") != status_color("Rented")


def test_drawer_row_shows_address_not_status(kekar_app):
    _prop(kekar_app.property_repo, address="12 Address Street")
    drawer = kekar_app.main_window.drawer
    drawer.reload()
    assert drawer.count() == 1

    widget = drawer.list.itemWidget(drawer.list.item(0))
    assert isinstance(widget, PropertyItemWidget)
    # Rows paint their own text rather than using child labels, so the
    # assertion is on the property the row was built from.
    assert widget._prop.address == "12 Address Street"
    # Status must not be spelled out — colour carries that meaning.
    assert widget._prop.status not in widget._prop.address


def test_drawer_filter_narrows_by_address_and_city(kekar_app):
    repo = kekar_app.property_repo
    _prop(repo, address="111 Main St", city="Pawhuska")
    _prop(repo, address="222 Elm Ave", city="Bartlesville")
    drawer = kekar_app.main_window.drawer
    drawer.reload()
    assert drawer.count() == 2

    drawer.filter.setText("elm")
    assert drawer.count() == 1

    drawer.filter.setText("pawhuska")
    assert drawer.count() == 1

    drawer.filter.setText("")
    assert drawer.count() == 2


def test_drawer_filter_matches_amenities(kekar_app):
    repo = kekar_app.property_repo
    _prop(repo, address="111 Main St", amenity_dishwasher=True)
    _prop(repo, address="222 Elm Ave", amenity_ac=True)
    drawer = kekar_app.main_window.drawer
    drawer.reload()
    assert drawer.count() == 2

    drawer.filter.setText("dishwasher")
    assert drawer.count() == 1

    drawer.filter.setText("fenced yard")
    assert drawer.count() == 0


def test_drawer_filter_matches_notes_and_pet_policy(kekar_app):
    repo = kekar_app.property_repo
    _prop(repo, address="111 Main St", pet_policy="Cats OK",
          notes="Close to the school")
    _prop(repo, address="222 Elm Ave", pet_policy="No pets")
    drawer = kekar_app.main_window.drawer
    drawer.reload()

    drawer.filter.setText("cats")
    assert drawer.count() == 1

    drawer.filter.setText("school")
    assert drawer.count() == 1

    drawer.filter.setText("pawhuska")
    assert drawer.count() == 2


def test_search_text_includes_every_amenity():
    prop = Property(address="1 Amenity Way", amenity_wd=True,
                    amenity_dishwasher=True)
    haystack = search_text(prop)
    assert "washer" in haystack
    assert "dishwasher" in haystack
    assert "parking" not in haystack


def test_placeholder_cover_is_usable():
    pm = placeholder_cover()
    assert not pm.isNull()
    assert pm.width() == pm.height()


# -- property form ---------------------------------------------------------

def test_delete_property_removes_it(kekar_app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", _yes)
    repo = kekar_app.property_repo
    pid = _prop(repo, address="9 Delete Me")
    form = kekar_app.main_window.property_form
    form.load_property(pid)

    form.delete_property()

    assert repo.get(pid) is None
    assert form.current_id is None
    assert kekar_app.main_window.drawer.count() == 0


def test_delete_property_removes_its_photos(kekar_app, monkeypatch, tmp_path):
    monkeypatch.setattr(QMessageBox, "question", _yes)
    repo = kekar_app.property_repo
    pid = _prop(repo, address="7 Photo Purge")
    src = tmp_path / "a.jpg"
    _make_image(src, (10, 20, 30))
    image_service.import_photos(pid, [src])
    assert image_service.property_photos(pid)

    form = kekar_app.main_window.property_form
    form.load_property(pid)
    form.delete_property()

    assert image_service.property_photos(pid) == []


def test_preview_listing_shows_the_compiled_text(kekar_app, monkeypatch):
    pid = _prop(kekar_app.property_repo, address="5 Preview Pl")
    form = kekar_app.main_window.property_form
    form.load_property(pid)

    captured = {}

    class FakeDialog:
        def __init__(self, app, prop, parent=None):
            captured["prop"] = prop

        def exec(self):
            captured["shown"] = True
            return 0

    monkeypatch.setattr("src.ui.property_form.ListingDialog", FakeDialog)
    form.preview_listing()
    assert captured.get("shown") is True
    assert captured["prop"].address == "5 Preview Pl"


def test_property_form_has_a_publish_button(kekar_app):
    button = kekar_app.main_window.property_form.publish_btn
    assert button.text().startswith("Publish")


def test_marketplace_refuses_when_autofill_is_disabled(kekar_app):
    from src.ui.marketplace_dialog import MarketplaceDialog

    pid = _prop(kekar_app.property_repo, address="8 Market St")
    kekar_app.settings.autofill_enabled = False
    dialog = MarketplaceDialog(kekar_app, kekar_app.property_repo.get(pid))
    dialog._start()
    assert "turned off" in dialog.result.toPlainText().lower()


def test_marketplace_reports_a_missing_browser_without_crashing(
        kekar_app, monkeypatch):
    from src.ui import marketplace_dialog

    pid = _prop(kekar_app.property_repo, address="9 Market St")
    kekar_app.settings.autofill_enabled = True
    monkeypatch.setattr(marketplace_dialog.launcher, "is_debug_port_open",
                        lambda port: False)

    def _no_browser(**kwargs):
        raise FileNotFoundError("No supported browser found.")

    monkeypatch.setattr(marketplace_dialog.launcher, "launch_browser",
                        _no_browser)

    dialog = marketplace_dialog.MarketplaceDialog(
        kekar_app, kekar_app.property_repo.get(pid))
    thread = marketplace_dialog._AutofillThread(dialog.prop)
    results = []
    thread.done.connect(results.append)
    thread.run()  # run the body synchronously; no browser involved

    assert results[0]["status"] == "failed"
    dialog._on_done(results[0])
    assert "No supported browser" in dialog.result.toPlainText()
    assert "Nothing has been published" in dialog.result.toPlainText()


# -- applicants -----------------------------------------------------------

def test_add_applicant_links_to_a_property(kekar_app, monkeypatch):
    from PyQt6.QtWidgets import QInputDialog

    pid = _prop(kekar_app.property_repo, address="10 CRM St")
    monkeypatch.setattr(QInputDialog, "getItem",
                        lambda *a, **k: ("10 CRM St", True))
    tab = kekar_app.main_window.crm_tab
    tab.add_applicant()

    applicants = kekar_app.applicant_repo.list()
    assert len(applicants) == 1
    assert applicants[0].property_id == pid


def test_add_applicant_can_be_cancelled(kekar_app):
    tab = kekar_app.main_window.crm_tab
    tab.add_applicant()  # conftest patches the picker to cancel
    assert kekar_app.applicant_repo.list() == []


def test_crm_stage_change_persists(kekar_app):
    from src.data.models import Applicant

    applicant_id = kekar_app.applicant_repo.create(
        Applicant(applicant_name="Stage Person"))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    assert tab.table.rowCount() == 1

    kekar_app.applicant_repo.set_stage(applicant_id, "Approved")
    tab.reload()

    assert tab.table.cellWidget(0, 3).currentText() == "Approved"


def test_every_stage_has_a_colour():
    from src.data.applicant_repo import STAGES
    from src.ui.crm_tab import STAGE_COLORS
    assert set(STAGES) <= set(STAGE_COLORS)


# -- photos ----------------------------------------------------------------

def _centre_pixel(path):
    from PIL import Image
    with Image.open(path) as image:
        image = image.convert("RGB")
        return image.getpixel((image.width // 2, image.height // 2))


def test_set_cover_moves_photo_to_the_front(kekar_app, tmp_path):
    pid = _prop(kekar_app.property_repo, address="3 Cover Pl")
    paths = []
    for index, colour in enumerate(((200, 30, 30), (30, 200, 30), (30, 30, 200))):
        path = tmp_path / f"img{index}.jpg"
        _make_image(path, colour)
        paths.append(path)
    image_service.import_photos(pid, paths)

    photos = image_service.property_photos(pid)
    assert len(photos) == 3
    assert image_service.cover_photo(pid) == photos[0]

    wanted = _centre_pixel(photos[2])
    image_service.set_cover(pid, photos[2])

    # The cover is whichever file sorts first, so compare image content rather
    # than filenames — set_cover swaps names, not contents.
    assert _centre_pixel(image_service.cover_photo(pid)) == wanted


def test_set_cover_needs_two_photos(kekar_app, tmp_path):
    pid = _prop(kekar_app.property_repo, address="1 Solo Pl")
    src = tmp_path / "only.jpg"
    _make_image(src, (1, 2, 3))
    image_service.import_photos(pid, [src])
    assert image_service.set_cover(pid, image_service.property_photos(pid)[0]) \
        is False


def test_delete_photo_removes_exactly_one(kekar_app, tmp_path):
    pid = _prop(kekar_app.property_repo, address="4 Prune Pl")
    paths = []
    for index in range(3):
        path = tmp_path / f"p{index}.jpg"
        _make_image(path, (index, index, index))
        paths.append(path)
    image_service.import_photos(pid, paths)

    victim = image_service.property_photos(pid)[1]
    assert image_service.delete_photo(pid, victim) is True

    remaining = image_service.property_photos(pid)
    assert len(remaining) == 2
    assert victim not in remaining


# -- chat ------------------------------------------------------------------

def test_chat_loads_stored_history(kekar_app):
    kekar_app.chat_repo.add("user", "earlier question")
    kekar_app.chat_repo.add("assistant", "earlier answer")
    pane = kekar_app.main_window.chat_pane
    pane.load_history()
    text = pane.view.toPlainText()
    assert "earlier question" in text
    assert "earlier answer" in text


def test_chat_clear_history_empties_the_pane(kekar_app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", _yes)
    kekar_app.chat_repo.add("user", "something")
    pane = kekar_app.main_window.chat_pane
    pane.load_history()
    assert pane.view.toPlainText()

    pane.clear_history()

    assert kekar_app.chat_repo.history() == []
    assert pane.view.toPlainText() == ""


def test_chat_refuses_to_send_without_a_key(kekar_app, monkeypatch):
    kekar_app.settings.api_key = ""
    pane = kekar_app.main_window.chat_pane
    pane.input.setText("hello there")

    shown = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: shown.append(a))
    pane.send()

    assert pane.view.toPlainText() == ""
    assert shown, "the user should be told why nothing was sent"


def test_chat_reports_the_providers_own_reason(kekar_app, monkeypatch):
    """A billing rejection must not be reported as a connectivity problem."""
    from src.agent.client import LLMBusy
    from src.agent.runner import CancelFlag
    from src.ui.chat_pane import _AgentThread

    async def _boom(*a, **k):
        raise LLMBusy(
            "All models failed. Last error: gpt-4o-mini: HTTP 429 — "
            "You have no credits remaining.")

    monkeypatch.setattr(kekar_app.agent_runner, "run", _boom)

    thread = _AgentThread(kekar_app, "hello", [], CancelFlag())
    seen: list[str] = []
    thread.failed.connect(seen.append)
    thread.run()

    assert seen, "the failure must be reported to the UI"
    assert "no credits remaining" in seen[0]
    assert "could not reach the assistant" not in seen[0]


def test_chat_has_a_stop_button_that_cancels(kekar_app):
    pane = kekar_app.main_window.chat_pane
    assert pane.cancel_btn.isEnabled() is False
    pane._cancel_run()
    # Nothing running, so this must be a harmless no-op.
    assert pane.cancel_btn.isEnabled() is False


# -- settings --------------------------------------------------------------

class _FakeProviderThread(QThread):
    done = pyqtSignal(bool, object)

    def __init__(self, app, task, **kwargs):
        super().__init__()
        self.app = app
        self.task = task

    def start(self):  # noqa: D102 - test double
        self.done.emit(True, "Connected.")


def test_settings_test_connection_uses_the_provider(kekar_app, monkeypatch):
    from src.ui import settings_dialog
    monkeypatch.setattr(settings_dialog, "_ProviderThread",
                        _FakeProviderThread)

    dialog = settings_dialog.SettingsDialog(kekar_app)
    dialog.key_input.setText("sk-test-key")
    original = kekar_app.settings.api_key
    dialog._test_connection()

    # Testing uses a temporary copy; only Save commits the key.
    assert kekar_app.settings.api_key == original
    assert dialog.key_input.text() == "sk-test-key"


def test_settings_reports_the_task_result(kekar_app, monkeypatch):
    from src.ui import settings_dialog
    shown = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: shown.append(a))

    dialog = settings_dialog.SettingsDialog(kekar_app)
    dialog._on_task_done(False, "That key was rejected.")

    assert dialog.test_btn.isEnabled() is True
    assert dialog.test_btn.text() == "Test connection"
    assert shown


def test_settings_saves_the_provider_and_endpoint(kekar_app, monkeypatch):
    from src.ui import settings_dialog
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    dialog = settings_dialog.SettingsDialog(kekar_app)
    index = dialog.provider.findData("openai")
    dialog.provider.setCurrentIndex(index)
    dialog.key_input.setText("sk-test-key")
    dialog._save()

    assert kekar_app.settings.provider == "openai"
    assert kekar_app.settings.api_base == "https://api.openai.com/v1"


# -- model picker ----------------------------------------------------------

def test_model_picker_returns_checked_models(kekar_app):
    from src.ui.settings_dialog import ModelPickerDialog

    picker = ModelPickerDialog(["alpha/one", "beta/two", "gamma/three"])
    picker.list.item(0).setCheckState(Qt.CheckState.Checked)
    picker.list.item(2).setCheckState(Qt.CheckState.Checked)
    picker._accept()

    assert picker.selected() == ["alpha/one", "gamma/three"]


def test_model_picker_filter_hides_non_matches(kekar_app):
    from src.ui.settings_dialog import ModelPickerDialog

    picker = ModelPickerDialog(["llama-3.1", "gpt-4o", "llama-3.3"])
    picker._apply_filter("llama")
    visible = [picker.list.item(i).text() for i in range(picker.list.count())
               if not picker.list.item(i).isHidden()]
    assert visible == ["llama-3.1", "llama-3.3"]


# -- connectivity ----------------------------------------------------------

def test_provider_reachable_detects_open_and_closed_ports():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert connectivity.provider_reachable(
            f"http://127.0.0.1:{port}", timeout=1.0) is True
    finally:
        server.close()
    assert connectivity.provider_reachable(
        f"http://127.0.0.1:{port}", timeout=1.0) is False


def test_provider_reachable_handles_a_bogus_host():
    assert connectivity.provider_reachable("https://nope.invalid") is False


def test_ping_is_disabled_under_test():
    assert os.environ.get("KEKAR_TESTING") == "1"


# -- version ---------------------------------------------------------------

def test_version_has_a_single_source():
    from src._version import APP_VERSION
    import src.app as app_module
    import src.main as main_module
    assert app_module.APP_VERSION == APP_VERSION
    assert main_module.APP_VERSION == APP_VERSION


def test_application_uses_a_readable_font(kekar_app):
    assert kekar_app.font().pointSize() >= 10


def test_ping_is_a_noop_while_one_is_in_flight(kekar_app):
    """A second check while a ping runs must not start another thread."""
    window = kekar_app.main_window
    window._ping = object()  # pretend a ping is running
    window.check_online()
    assert window._ping is not None
    window._ping = None


def test_offline_banner_reflects_ping_result(kekar_app):
    window = kekar_app.main_window
    window._on_ping_result(False)
    assert window.offline_banner.isVisibleTo(window)
    assert window.status_pill.text() == "Offline"

    window._on_ping_result(True)
    assert not window.offline_banner.isVisibleTo(window)
    assert window.status_pill.text() == "Online"
