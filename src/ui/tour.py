"""Guided tour: a spotlight overlay that walks the user through the UI.

The overlay is a transparent child of the main window. It paints a dim layer
everywhere except a hole around the current target, and hosts a caption panel
with Back / Next / Skip.

The overlay is modal: it captures clicks, so the tour is a guided walkthrough
rather than free play.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QEvent, QRect, Qt
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QRegion, QShortcut
from PyQt6.QtWidgets import (QDialogButtonBox, QFrame, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from .theme import font

DIM = QColor(20, 16, 12, 170)
RING = QColor("#ffb300")


@dataclass
class TourStep:
    """One tour step. ``target=None`` means a centred, untargeted card.

    ``on_enter`` receives the overlay running the step, so a step can record
    state on the overlay that will actually finish it — never a stale one.
    """

    target: object | None
    title: str
    body: str
    on_enter: Callable[["TourOverlay"], None] | None = None


class TourOverlay(QWidget):
    def __init__(self, window: QWidget, steps: list[TourStep]):
        super().__init__(window)
        self._window = window
        self._steps = steps
        self.current_index = 0
        self.restore_tab: int | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.caption = QFrame(self)
        self.caption.setStyleSheet(
            "background:#fffdf7; border:1px solid #d8cfc0; border-radius:10px;")
        cap_layout = QVBoxLayout(self.caption)
        cap_layout.setContentsMargins(14, 12, 14, 12)
        self.title_label = QLabel()
        self.title_label.setFont(font(12, bold=True))
        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setFont(font(10))
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color:#7a7268;")
        cap_layout.addWidget(self.title_label)
        cap_layout.addWidget(self.body_label)
        cap_layout.addWidget(self.progress_label)

        buttons = QDialogButtonBox()
        self.back_button = buttons.addButton(
            "Back", QDialogButtonBox.ButtonRole.ActionRole)
        self.next_button = buttons.addButton(
            "Next", QDialogButtonBox.ButtonRole.AcceptRole)
        self.skip_button = buttons.addButton(
            "Skip tour", QDialogButtonBox.ButtonRole.RejectRole)
        self.back_button.clicked.connect(self.back)
        self.next_button.clicked.connect(self.next)
        self.skip_button.clicked.connect(self.finish)
        cap_layout.addWidget(buttons)

        QShortcut(QKeySequence("Escape"), self).activated.connect(self.finish)

    # -- geometry ----------------------------------------------------------

    def _hole_rect(self) -> QRect | None:
        target = self._steps[self.current_index].target
        if target is None:
            return None
        rect = target.rect().translated(
            target.mapTo(self._window, target.pos()))
        rect = rect.intersected(self._window.rect())
        return rect if not rect.isEmpty() else None

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        self._place_caption()

    def _place_caption(self) -> None:
        self.caption.adjustSize()
        width = min(360, max(280, self.width() - 32))
        height = self.caption.height()
        hole = self._hole_rect()

        if hole is None:
            x = (self.width() - width) // 2
            y = max(8, (self.height() - height) // 2)
        else:
            x = min(max(8, hole.center().x() - width // 2),
                    max(8, self.width() - width - 8))
            below = hole.bottom() + 12
            if below + height > self.height() - 8:
                below = max(8, hole.top() - height - 12)
            y = below

        self.caption.setGeometry(x, y, width, height)

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        hole = self._hole_rect()
        if hole is None:
            painter.fillRect(self.rect(), DIM)
        else:
            painter.setClipRegion(QRegion(self.rect()) - QRegion(hole))
            painter.fillRect(self.rect(), DIM)
            painter.setClipRegion(QRegion(self.rect()))
            painter.setPen(QPen(RING, 3))
            painter.drawRoundedRect(hole.adjusted(-4, -4, 4, 4), 10, 10)
        painter.end()

    # -- navigation --------------------------------------------------------

    def start(self) -> None:
        self.current_index = 0
        self.restore_tab = None
        self.resize(self._window.size())
        self.raise_()
        self.show()
        self._apply_step()

    def finish(self) -> None:
        if self.restore_tab is not None:
            self._window.tabs.setCurrentIndex(self.restore_tab)
            self.restore_tab = None
        self.hide()
        self.deleteLater()

    def next(self) -> None:
        if self.current_index < len(self._steps) - 1:
            self.current_index += 1
            self._apply_step()

    def back(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._apply_step()

    def goto_step(self, index: int) -> None:
        if 0 <= index < len(self._steps):
            self.current_index = index
            self._apply_step()

    def goto_last(self) -> None:
        self.goto_step(len(self._steps) - 1)

    def _apply_step(self) -> None:
        step = self._steps[self.current_index]
        self.title_label.setText(step.title)
        self.body_label.setText(step.body)
        self.progress_label.setText(
            f"Step {self.current_index + 1} of {len(self._steps)}")
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setText(
            "Finish" if self.current_index == len(self._steps) - 1 else "Next")
        if step.on_enter is not None:
            step.on_enter(self)
        self._place_caption()
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.finish()
        elif event.key() == Qt.Key.Key_Right:
            self.next()
        elif event.key() == Qt.Key.Key_Left:
            self.back()
        else:
            super().keyPressEvent(event)


def build_tour_steps(window) -> list[TourStep]:
    """The tour content, bound to a concrete MainWindow."""
    return [
        TourStep(
            None, "Welcome to KeKar",
            "KeKar keeps your properties, listings, photos and applicant notes "
            "in one place, stored only on this device. This short tour shows "
            "you around. Your own data is not touched."),
        TourStep(
            window.drawer, "Your properties",
            "This is your property list. The search box filters as you type. "
            "Use '+ Add New Property' to add your first listing."),
        TourStep(
            window.property_form, "The details form",
            "Address, rent, deposit and the rest. Fields with a red outline "
            "are needed before a listing can be published."),
        TourStep(
            window.photo_panel, "Photos",
            "Add photos for a property and choose one as the cover. The cover "
            "is what appears in the property list."),
        TourStep(
            window.crm_tab, "Applicants",
            "Track every applicant through the pipeline, from first enquiry to "
            "approved or rejected.",
            on_enter=lambda overlay: _show_applicants(window, overlay)),
        TourStep(
            window.chat_pane, "The assistant",
            "Ask questions in plain language, or give an instruction like "
            "'draft a message to John'. It can read and update your records."),
        TourStep(
            window.menuBar(), "Settings and providers",
            "Choose your AI provider and models, manage backups, and control "
            "marketplace auto-fill."),
        TourStep(
            None, "You're in demo mode",
            "Everything you see is sample data. Your own records are safe and "
            "unchanged. Use 'Exit demo mode' in the Help menu when you're "
            "ready to work with your real data."),
    ]


def _show_applicants(window, overlay: "TourOverlay") -> None:
    """Switch to the Applicants tab for the duration of its step.

    Records the tab to restore on the overlay that is running the step.
    """
    if overlay.restore_tab is None:
        overlay.restore_tab = window.tabs.currentIndex()
    window.tabs.setCurrentIndex(1)
