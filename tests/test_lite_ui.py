"""Widget-level behaviour of the Lite composition."""
from src.app import Application
from src.data.models import SHORT_STAY_KIND
from src.ui.main_window import MainWindow
from src.ui.property_form import PropertyForm


def _lite_window(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    return MainWindow(kekar_app)


def _close_window(kekar_app, window):
    try:
        kekar_app.data_changed.disconnect(window.reload_all)
    except (TypeError, RuntimeError):
        pass
    window.close()


def test_lite_window_has_no_chat_pane(kekar_app, monkeypatch):
    window = _lite_window(kekar_app, monkeypatch)
    try:
        assert window.chat_pane is None
        assert window.main_splitter.count() == 1
    finally:
        _close_window(kekar_app, window)


def test_lite_window_has_no_chat_controls_or_offline_ping(
        kekar_app, monkeypatch):
    window = _lite_window(kekar_app, monkeypatch)
    try:
        assert window.chat_action.isVisible() is False
        assert window.chat_toggle.isVisible() is False
        assert not window._ping_timer.isActive()
        assert window.offline_banner.isHidden()
        assert window.status_pill.isHidden()
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
