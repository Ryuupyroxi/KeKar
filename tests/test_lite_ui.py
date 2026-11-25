"""Widget-level behaviour of the Lite composition."""
from src.app import Application
from src.data.models import SHORT_STAY_KIND, Property
from src.ui.listing_dialog import ListingDialog
from src.ui.main_window import MainWindow
from src.ui.property_form import PropertyForm
from src.ui.settings_dialog import SettingsDialog
from src.ui.wizard import FirstRunWizard


def _lite_window(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    return MainWindow(kekar_app)


def _close_window(kekar_app, window):
    try:
        kekar_app.data_changed.disconnect(window.reload_all)
    except (TypeError, RuntimeError):
        pass
    window.close()


def test_lite_window_keeps_the_chat_pane(kekar_app, monkeypatch):
    window = _lite_window(kekar_app, monkeypatch)
    try:
        assert window.chat_pane is not None
        assert window.main_splitter.count() == 2
    finally:
        _close_window(kekar_app, window)


def test_lite_window_has_chat_controls(kekar_app, monkeypatch):
    window = _lite_window(kekar_app, monkeypatch)
    try:
        assert window.chat_action.isVisible()
        assert window.chat_toggle.isHidden() is False
    finally:
        _close_window(kekar_app, window)


def test_lite_form_has_no_publish_or_portals_but_keeps_copy(kekar_app,
                                                            monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    form = PropertyForm(kekar_app)
    assert form.publish_btn is None
    assert form.portals_box is None
    assert form.portal_rows == {}
    assert form.copy_btn.text() == "Copy listing"
    assert form.preview_btn.text() == "Preview listing"
    assert form.kind_combo.itemData(1) == SHORT_STAY_KIND
    assert form.kind_combo.itemText(1) == "Short stay"
    form.close()


def test_lite_form_never_starts_a_maps_request(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    monkeypatch.setattr(kekar_app.settings, "maps_key", "test-key")
    form = PropertyForm(kekar_app)
    assert form.address_input.completer() is None
    assert not form._maps_timer.isActive()
    form.address_input.setText("99 Network Free Street")
    form._on_address_edited("99 Network Free Street")
    assert not form._maps_timer.isActive()
    form.close()


def test_lite_form_still_saves_a_short_stay_without_portal_rows(
        kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    form = PropertyForm(kekar_app)
    form.address_input.setText("9 Lite Lane")
    form.kind_combo.setCurrentIndex(1)
    form.nightly_input.setValue(175)
    form.save()
    saved = kekar_app.property_repo.get(form.current_id)
    assert saved.kind == SHORT_STAY_KIND
    assert saved.nightly_price == 175
    assert kekar_app.portal_repo.list_for_property(saved.id) == []
    form.close()


def test_lite_listing_dialog_offers_only_local_rental_channels(
        kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    prop = Property(address="10 Copy Court", rent_price=900, sqft=800,
                    bedrooms=2, bathrooms=1.0)
    dialog = ListingDialog(kekar_app, prop)
    keys = [dialog.channel.itemData(i) for i in range(dialog.channel.count())]
    assert keys == ["generic", "apartments_com", "facebook_marketplace",
                    "zillow"]
    dialog.close()


def test_lite_listing_dialog_offers_only_local_stay_channels(
        kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    prop = Property(address="11 Copy Court", kind=SHORT_STAY_KIND,
                    nightly_price=190, max_guests=4, min_stay_nights=2)
    dialog = ListingDialog(kekar_app, prop)
    keys = [dialog.channel.itemData(i) for i in range(dialog.channel.count())]
    assert keys == ["generic", "airbnb", "booking_com", "vrbo"]

    assert "Airbnb" not in dialog.note.text()
    dialog.close()


def test_lite_compile_channel_still_accepts_a_hidden_key():
    """Hiding a channel in the picker must not change the data layer."""
    from src.services.listing_channels import compile_channel
    prop = Property(address="12 Copy Court", rent_price=700, sqft=700)
    package = compile_channel(prop, "apartments_com")
    assert "Description" in [name for name, _ in package.fields]


def test_lite_wizard_offers_the_api_key_page(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    wizard = FirstRunWizard(kekar_app)
    assert wizard.pages.count() == 2
    assert hasattr(wizard, "key_input")


def test_lite_settings_shows_provider_controls(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    dialog = SettingsDialog(kekar_app)
    for attr in ("key_input", "provider", "api_base", "models_input",
                 "test_btn", "remove_btn"):
        assert hasattr(dialog, attr), attr
    # Maps stays a direct connection and remains hidden in Lite.
    assert not hasattr(dialog, "maps_key")
    assert dialog.theme is not None
    dialog.close()


def test_lite_settings_save_preserves_existing_key(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    kekar_app.settings.api_key = "an-old-key"
    kekar_app.settings.maps_key = "maps-existing"
    dialog = SettingsDialog(kekar_app)
    dialog.keep_days.setValue(14)
    dialog._save()
    assert kekar_app.settings.backup_keep_days == 14
    assert kekar_app.settings.api_key == "an-old-key"
    assert kekar_app.settings.maps_key == "maps-existing"
