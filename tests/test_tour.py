"""Guided tour: spotlight overlay, step targets, and navigation."""
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QPushButton

from src.ui.tour import TourOverlay, TourStep, build_tour_steps


def test_tour_steps_target_real_widgets(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)

    assert len(steps) == 8
    for step in steps:
        assert isinstance(step, TourStep)
        if step.target is not None:
            assert step.target.parent() is not None, (
                f"{step.title!r} target is not in the widget tree")


def test_overlay_paints_without_raising(kekar_app):
    window = kekar_app.main_window
    overlay = TourOverlay(window, build_tour_steps(window))
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()

    overlay.grab()  # forces a paint; raises if painting fails
    overlay.finish()


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
