"""Collapsible sidebar and chat panels."""
import pytest

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent

from src.ui.main_window import CollapsibleSplitter, _PaneHandle


@pytest.fixture(autouse=True)
def _visible(kekar_app):
    """Splitter geometry is only real once the window is shown.

    Qt does not lay a hidden widget out, so collapsing in a hidden window does
    not produce a zero-width pane.
    """
    kekar_app.main_window.show()
    kekar_app.processEvents()
    yield


@pytest.fixture(autouse=True)
def _restore_layout(kekar_app):
    """Leave both panels expanded so each test starts from the same layout."""
    yield
    kekar_app.main_window.top_splitter.collapse(0, False)
    kekar_app.main_window.main_splitter.collapse(1, False)
    kekar_app.main_window._remember_layout()


def _live_handle(splitter):
    """A two-pane splitter's real handle is at index 1; index 0 is a hidden
    placeholder Qt keeps around."""
    return splitter.handle(1)


def _mouse(kind, position, buttons):
    return QMouseEvent(kind, position, position,
                      Qt.MouseButton.LeftButton, buttons,
                      Qt.KeyboardModifier.NoModifier)


def test_pressing_the_handle_does_not_collapse(kekar_app):
    """The handle must not hijack the click: collapsing is the buttons' job."""
    window = kekar_app.main_window
    handle = _live_handle(window.top_splitter)
    rect = handle.geometry()
    point = QPointF(rect.center().x(), rect.center().y())

    handle.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, point,
                                  Qt.MouseButton.LeftButton))
    handle.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, point,
                                    Qt.MouseButton.NoButton))

    assert window.top_splitter.is_collapsed(0) is False
    assert window.drawer.width() > 0


def test_handle_leaves_mouse_events_to_qt(kekar_app):
    """Overriding the handle's mouse events breaks drag-to-resize, so the
    handle must only paint."""
    handle = _live_handle(kekar_app.main_window.top_splitter)
    for name in ("mousePressEvent", "mouseMoveEvent", "mouseReleaseEvent"):
        assert name not in type(handle).__dict__, (
            f"_PaneHandle must not override {name}")


def test_panes_start_expanded(kekar_app):
    window = kekar_app.main_window
    assert window.top_splitter.is_collapsed(0) is False
    assert window.main_splitter.is_collapsed(1) is False


def test_toggle_sidebar_collapses_then_restores(kekar_app):
    window = kekar_app.main_window
    before = window.top_splitter.sizes()

    window._toggle_sidebar()
    assert window.top_splitter.is_collapsed(0) is True
    assert window.drawer.width() == 0

    window._toggle_sidebar()
    assert window.top_splitter.is_collapsed(0) is False
    assert window.drawer.width() > 0
    assert window.top_splitter.sizes() == before


def test_toggle_chat_collapses_then_restores(kekar_app):
    window = kekar_app.main_window
    before = window.main_splitter.sizes()

    window._toggle_chat()
    assert window.main_splitter.is_collapsed(1) is True
    assert window.chat_pane.height() == 0

    window._toggle_chat()
    assert window.main_splitter.is_collapsed(1) is False
    assert window.chat_pane.height() > 0
    assert window.main_splitter.sizes() == before


def test_collapsed_state_is_remembered(kekar_app):
    window = kekar_app.main_window
    window._toggle_sidebar()
    window._toggle_chat()

    assert kekar_app.settings.sidebar_collapsed is True
    assert kekar_app.settings.chat_collapsed is True


def test_view_menu_labels_follow_the_state(kekar_app):
    window = kekar_app.main_window
    assert window.sidebar_action.text() == "Collapse property list"
    assert window.chat_action.text() == "Collapse chat"

    window._toggle_sidebar()
    window._toggle_chat()
    assert window.sidebar_action.text() == "Expand property list"
    assert window.chat_action.text() == "Expand chat"


def test_toggle_buttons_track_the_state(kekar_app):
    """The corner buttons are the always-reachable control, so their labels
    must say which way the panel will move."""
    window = kekar_app.main_window
    assert window.sidebar_toggle.text() == "◀ Properties"
    assert window.chat_toggle.text() == "▼ Chat"

    window._toggle_sidebar()
    window._toggle_chat()
    assert window.sidebar_toggle.text() == "▶ Properties"
    assert window.chat_toggle.text() == "▲ Chat"


def test_toggle_buttons_survive_a_collapsed_panel(kekar_app):
    """A control inside the panel would vanish with it."""
    window = kekar_app.main_window
    window._toggle_sidebar()
    window._toggle_chat()

    assert window.sidebar_toggle.isVisible()
    assert window.chat_toggle.isVisible()
    assert window.drawer.width() == 0


def test_clicking_a_toggle_button_collapses_that_pane(kekar_app):
    window = kekar_app.main_window

    window.sidebar_toggle.click()
    assert window.top_splitter.is_collapsed(0) is True
    assert window.main_splitter.is_collapsed(1) is False, (
        "the properties button must not touch the chat")

    window.sidebar_toggle.click()
    assert window.top_splitter.is_collapsed(0) is False

    window.chat_toggle.click()
    assert window.main_splitter.is_collapsed(1) is True
    assert window.top_splitter.is_collapsed(0) is False

    window.chat_toggle.click()
    assert window.main_splitter.is_collapsed(1) is False


def test_toggles_live_in_the_menu_bar_corner(kekar_app):
    window = kekar_app.main_window
    corner = window.menuBar().cornerWidget()
    assert corner is not None
    assert window.sidebar_toggle.parent() is corner
    assert window.chat_toggle.parent() is corner


def test_restoring_a_saved_layout(kekar_app):
    """The layout the user left behind comes back on the next launch."""
    kekar_app.settings.sidebar_collapsed = True
    kekar_app.main_window._restore_layout()

    assert kekar_app.main_window.top_splitter.is_collapsed(0) is True
    assert kekar_app.main_window.sidebar_action.text() == "Expand property list"


def test_handle_is_visible_on_the_boundary_when_collapsed(kekar_app):
    """The grip must remain draggable even with the pane collapsed."""
    window = kekar_app.main_window
    before = _live_handle(window.top_splitter).geometry()

    window._toggle_sidebar()

    handle = _live_handle(window.top_splitter)
    assert handle.isVisible()
    assert handle.geometry().left() <= 16
    assert before.width() == handle.geometry().width(), "handle size changed"


def test_handle_still_draws_a_grip(kekar_app):
    handle = _live_handle(kekar_app.main_window.top_splitter)
    assert isinstance(handle, _PaneHandle)


def test_splitter_is_the_collapsible_kind(kekar_app):
    assert isinstance(kekar_app.main_window.top_splitter, CollapsibleSplitter)
    assert isinstance(kekar_app.main_window.main_splitter, CollapsibleSplitter)
