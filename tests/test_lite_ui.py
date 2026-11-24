"""Widget-level behaviour of the Lite composition."""
from src.app import Application
from src.ui.main_window import MainWindow


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
