"""UI tests for Google Maps address suggestions and optional autofill."""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QCompleter  # noqa: E402

from src.services import maps_service  # noqa: E402
from src.ui import worker  # noqa: E402

DESCRIPTION = "10 Main St, Pawhuska, OK 74056"


@pytest.fixture
def maps_form(kekar_app):
    """A form with a key set, restoring the shared settings afterwards."""
    form = kekar_app.main_window.property_form
    settings = kekar_app.settings
    old_key, old_autofill = settings.maps_key, settings.maps_autofill
    settings.maps_key = "test-maps-key"
    settings.maps_autofill = True
    form.load_property(None)
    yield form
    settings.maps_key = old_key
    settings.maps_autofill = old_autofill
    form.load_property(None)


def _pump(kekar_app, predicate, timeout=3.0):
    """Run Qt events until the predicate is true (worker replies are queued)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        kekar_app.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return False


def _type(form, text):
    form.address_input.setText(text)
    form.address_input.textEdited.emit(text)


def test_address_input_owns_a_completer_and_string_model(maps_form):
    completer = maps_form.address_input.completer()
    assert isinstance(completer, QCompleter)
    assert completer.model() is maps_form._maps_model
    assert maps_form._maps_model.rowCount() == 0


def test_suggestions_populate_the_completer_model(maps_form, kekar_app,
                                                  monkeypatch):
    calls = []

    def fake_autocomplete(key, text):
        calls.append((key, text))
        return [maps_service.Suggestion(DESCRIPTION, "place-1"),
                maps_service.Suggestion("20 Oak Ave, Tulsa, OK", "place-2")]

    monkeypatch.setattr(maps_service, "autocomplete", fake_autocomplete)
    baseline = worker.live_count()

    maps_form.address_input.setFocus()
    _type(maps_form, "10 main")
    assert calls == []                     # debounced, not immediate
    assert _pump(kekar_app, lambda: maps_form._maps_model.rowCount() == 2)

    assert maps_form._maps_model.stringList() == [
        DESCRIPTION, "20 Oak Ave, Tulsa, OK"]
    assert maps_form.address_input.completer().popup().isVisible(), (
        "a delayed reply must reopen the dropdown, not wait for another key")
    assert calls == [("test-maps-key", "10 main")]
    assert _pump(kekar_app, lambda: worker.live_count() == baseline)


def test_no_key_means_no_popup_and_no_network(maps_form, kekar_app,
                                              monkeypatch):
    kekar_app.settings.maps_key = ""

    def forbidden(*args, **kwargs):
        raise AssertionError("a missing key must never reach the network")

    monkeypatch.setattr(maps_service, "autocomplete", forbidden)
    _type(maps_form, "123 Main Street")
    kekar_app.processEvents()

    assert maps_form._maps_model.rowCount() == 0
    assert not maps_form.address_input.completer().popup().isVisible()


def test_fewer_than_four_characters_never_searches(maps_form, kekar_app,
                                                   monkeypatch):
    calls = []
    monkeypatch.setattr(maps_service, "autocomplete",
                        lambda key, text: calls.append(text) or [])

    for text in ("1", "12", "123"):
        _type(maps_form, text)
    kekar_app.processEvents()

    assert calls == []
    assert maps_form._maps_model.rowCount() == 0


def test_selecting_a_suggestion_fills_only_empty_fields(maps_form, kekar_app,
                                                        monkeypatch):
    calls = []

    def fake_details(key, place_id):
        calls.append((key, place_id))
        return maps_service.PlaceDetails(
            formatted_address=DESCRIPTION, city="Pawhuska",
            postal_code="74056", street_number="10", route="Main Street")

    monkeypatch.setattr(maps_service, "place_details", fake_details)
    maps_form._map_suggestions = {DESCRIPTION: "place-1"}
    maps_form._maps_model.setStringList([DESCRIPTION])
    maps_form.city_input.clear()
    maps_form.zip_input.setText("74123")          # user data: keep it
    baseline = worker.live_count()

    maps_form._maps_completer.activated.emit(DESCRIPTION)

    assert maps_form.address_input.text() == DESCRIPTION
    assert _pump(kekar_app, lambda: maps_form.city_input.text() == "Pawhuska")
    assert maps_form.zip_input.text() == "74123"
    assert calls == [("test-maps-key", "place-1")]
    assert _pump(kekar_app, lambda: worker.live_count() == baseline)


def test_autofill_can_be_switched_off(maps_form, kekar_app, monkeypatch):
    kekar_app.settings.maps_autofill = False

    def forbidden(*args, **kwargs):
        raise AssertionError("autofill was disabled")

    monkeypatch.setattr(maps_service, "place_details", forbidden)
    maps_form._map_suggestions = {DESCRIPTION: "place-1"}
    maps_form._maps_model.setStringList([DESCRIPTION])

    maps_form._maps_completer.activated.emit(DESCRIPTION)
    kekar_app.processEvents()

    assert maps_form.address_input.text() == DESCRIPTION
    assert maps_form.city_input.text() == ""
    assert maps_form.zip_input.text() == ""


def test_provider_error_is_visible_in_the_form(maps_form, kekar_app,
                                               monkeypatch):
    message = "HTTP 429 — You have exceeded your daily request quota."

    def fail(key, text):
        raise maps_service.MapsError(message)

    monkeypatch.setattr(maps_service, "autocomplete", fail)
    _type(maps_form, "10 main")
    assert _pump(kekar_app, lambda: bool(maps_form.last_maps_error))
    assert maps_form.last_maps_error == message
    assert maps_form._maps_model.rowCount() == 0


def test_settings_dialog_saves_the_maps_key_and_checkbox(kekar_app,
                                                          monkeypatch):
    from src.ui.settings_dialog import SettingsDialog

    settings = kekar_app.settings
    old_key, old_on = settings.maps_key, settings.maps_autofill
    dialog = SettingsDialog(kekar_app)
    try:
        dialog.maps_key.setText("typed-maps-key")
        dialog.maps_autofill.setChecked(False)
        monkeypatch.setattr(settings, "save", lambda: None)
        dialog._save()
        assert settings.maps_key == "typed-maps-key"
        assert settings.maps_autofill is False
    finally:
        settings.maps_key = old_key
        settings.maps_autofill = old_on
