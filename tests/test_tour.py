"""Guided tour: spotlight overlay, step targets, and navigation."""
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QPushButton

from src import features
from src.ui.tour import TourOverlay, TourStep, build_tour_steps


def test_tour_steps_target_real_widgets(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)

    assert len(steps) == (11 if features.chat_enabled() else 10)
    for step in steps:
        assert isinstance(step, TourStep)
        if step.target is not None:
            assert step.target.parent() is not None, (
                f"{step.title!r} target is not in the widget tree")


def test_tour_covers_every_tab(kekar_app):
    """A tab nobody visits in the tour is a feature the user may never find.

    A step aimed inside a tab counts: the details form is the Properties tab.
    """
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    for index in range(window.tabs.count()):
        page = window.tabs.widget(index)
        covered = any(
            step.target is page
            or (step.target is not None and page.isAncestorOf(step.target))
            for step in steps)
        assert covered, f"tab {window.tabs.tabText(index)!r} is not in the tour"


def test_tour_describes_the_real_feature_set(kekar_app):
    """The wording must match what the app can actually do."""
    steps = build_tour_steps(kekar_app.main_window)
    text = " ".join(f"{step.title} {step.body}" for step in steps)
    for phrase in ("collapse", "Light", "OLED", "Leases", "template",
                   "Accounts", "print", "calendar", "status bar",
                   "Photos heading", "Help menu", "garage", "parking",
                   "pet deposit", "profile", "legend", "purple", "one line"):
        assert phrase in text, f"the tour never mentions {phrase!r}"
    if features.chat_enabled():
        for phrase in ("Zillow", "apartments.com", "Airbnb",
                       "Publish to Marketplace"):
            assert phrase in text, f"the tour never mentions {phrase!r}"
    else:
        for phrase in ("Facebook", "autofill", "Airbnb", "Vrbo",
                       "apartments.com", "Marketplace"):
            assert phrase not in text, f"Lite tour still mentions {phrase!r}"


def test_overlay_paints_without_raising(kekar_app):
    window = kekar_app.main_window
    overlay = TourOverlay(window, build_tour_steps(window))
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()

    overlay.grab()  # forces a paint; raises if painting fails
    overlay.finish()


def test_finish_button_closes_the_tour_on_the_last_step(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    overlay = TourOverlay(window, steps)
    closed = []
    overlay.closed.connect(lambda: closed.append(True))
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()
    overlay.goto_last()
    assert overlay.next_button.text() == "Finish"
    overlay.next()
    assert closed == [True]


def test_overlay_navigation(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    overlay = TourOverlay(window, steps)
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()

    assert overlay.current_index == 0
    overlay.next()
    assert overlay.current_index == 1
    overlay.back()
    assert overlay.current_index == 0
    overlay.back()
    assert overlay.current_index == 0, "cannot go before the first step"

    overlay.goto_last()
    overlay.next()
    assert overlay.current_index == len(steps) - 1, (
        "cannot go past the last step")
    overlay.finish()


def test_overlay_switches_to_applicants_tab(kekar_app):
    window = kekar_app.main_window
    window.tabs.setCurrentIndex(0)  # establish the starting tab explicitly
    steps = build_tour_steps(window)
    overlay = TourOverlay(window, steps)
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()

    index = next(i for i, s in enumerate(steps) if s.title == "Applicants")
    overlay.goto_step(index)
    kekar_app.processEvents()
    assert window.tabs.currentIndex() == 1

    overlay.finish()
    assert window.tabs.currentIndex() == 0, "tour must restore the tab"


def test_esc_closes_the_tour(kekar_app):
    window = kekar_app.main_window
    overlay = TourOverlay(window, build_tour_steps(window))
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()
    # The main window is not shown in tests, so isVisible() is always False;
    # isHidden() reflects this overlay's own state.
    assert not overlay.isHidden()

    overlay.keyPressEvent(QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert overlay.isHidden()


def test_caption_stays_inside_the_window(kekar_app):
    """A caption that runs off the edge would be unreadable, so every step at
    two very different window sizes must keep it inside."""
    window = kekar_app.main_window
    steps = build_tour_steps(window)

    for size in ((1100, 720), (1600, 1000)):
        window.resize(*size)
        overlay = TourOverlay(window, steps)
        overlay.resize(*size)
        overlay.show()
        kekar_app.processEvents()

        for index in range(len(steps)):
            overlay.goto_step(index)
            kekar_app.processEvents()
            rect = overlay.caption.geometry()
            assert rect.left() >= 0 and rect.top() >= 0, (
                f"step {index} caption escaped at {size}: {rect}")
            assert rect.right() <= size[0] and rect.bottom() <= size[1], (
                f"step {index} caption escaped at {size}: {rect}")

        overlay.finish()


def test_overlay_follows_window_resize(kekar_app):
    """A child widget does not resize itself when its parent does, so the
    overlay must follow or the dim layer leaves the new area uncovered.

    The window is shown first because Qt does not deliver resize events to a
    hidden widget — in the real app the main window is always visible before
    the tour starts.
    """
    window = kekar_app.main_window
    window.show()
    kekar_app.processEvents()

    overlay = TourOverlay(window, build_tour_steps(window))
    overlay.start()  # start() installs the resize filter
    kekar_app.processEvents()

    window.resize(1400, 900)
    kekar_app.processEvents()
    assert overlay.size() == window.size()

    window.resize(1100, 720)
    kekar_app.processEvents()
    assert overlay.size() == window.size()

    overlay.finish()


def test_starting_a_second_tour_does_not_stack(kekar_app):
    window = kekar_app.main_window
    kekar_app.enter_demo_mode()
    try:
        window._start_tour()
        first = window._tour
        assert first is not None

        window._start_tour()
        assert window._tour is not first, "a second overlay was stacked"
        assert first.isHidden(), "the first tour should have been closed"

        window._finish_tour()
        assert window._tour is None
    finally:
        kekar_app.exit_demo_mode()


def test_exiting_demo_mode_after_the_tour_ended(kekar_app):
    """A finished overlay deletes itself, so the window must drop its reference
    rather than calling into a deleted object later."""
    window = kekar_app.main_window
    kekar_app.enter_demo_mode()
    try:
        window._start_tour()
        window._finish_tour()
        assert window._tour is None
        kekar_app.processEvents()  # let deleteLater() run
    finally:
        kekar_app.exit_demo_mode()  # must not raise
