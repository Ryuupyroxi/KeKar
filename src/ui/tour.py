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

from PyQt6.QtCore import QEvent, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (QColor, QKeyEvent, QKeySequence, QPainter, QPen,
                         QRegion, QShortcut)
from PyQt6.QtWidgets import (QDialogButtonBox, QFrame, QLabel,
                             QVBoxLayout, QWidget)

from .. import features
from .theme import font

DIM = QColor(20, 16, 12, 170)


def _ring_colour(theme) -> QColor:
    return QColor(theme.accent) if theme is not None else QColor("#ffb300")


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
    #: Emitted just before the overlay destroys itself, so whoever created it
    #: can drop its reference instead of holding a deleted object.
    closed = pyqtSignal()

    def __init__(self, window: QWidget, steps: list[TourStep]):
        super().__init__(window)
        self._window = window
        self._steps = steps
        self.current_index = 0
        self.restore_tab: int | None = None
        # Default to the app's theme so a caller that does not call
        # apply_theme explicitly still paints with the right palette.
        app = getattr(window, "app", None)
        self._theme = app.current_theme() if app is not None else None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.caption = QFrame(self)
        cap_layout = QVBoxLayout(self.caption)
        cap_layout.setContentsMargins(14, 12, 14, 12)
        self.title_label = QLabel()
        self.title_label.setFont(font(12, bold=True))
        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setFont(font(10))
        self.progress_label = QLabel()
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

    def apply_theme(self, theme: "Theme") -> None:
        """Restyle the caption card and the highlight ring."""
        self._theme = theme
        self.caption.setStyleSheet(
            f"background:{theme.panel}; border:1px solid {theme.border}; "
            f"border-radius:10px; color:{theme.text};")
        self.progress_label.setStyleSheet(f"color:{theme.text_secondary};")
        self.update()

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
        # Width must be set before the height is measured: a word-wrapped
        # QLabel reports a taller sizeHint at 280 px than at 360 px. Measuring
        # first and only then forcing the width clipped the ends of long steps.
        width = min(360, max(280, self.width() - 32))
        self.caption.resize(width, self.caption.height())
        self.caption.layout().activate()
        # QLabel.sizeHint() ignores heightForWidth in this layout, so the
        # body was given the one-line hint and long steps lost their last
        # lines. Pin it to the wrapped height before measuring the card.
        wrapped = self.body_label.heightForWidth(self.body_label.width())
        self.body_label.setMinimumHeight(wrapped if wrapped and wrapped > 0 else 0)
        self.caption.adjustSize()
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
            painter.setPen(QPen(_ring_colour(self._theme), 3))
            painter.drawRoundedRect(hole.adjusted(-4, -4, 4, 4), 10, 10)
        painter.end()

    # -- navigation --------------------------------------------------------

    def start(self) -> None:
        self.current_index = 0
        self.restore_tab = None
        # Follow the window for the whole tour, not just for the opening size:
        # a child widget does not resize itself when its parent does, so the
        # dim layer would otherwise leave the newly exposed area undimmed.
        self._window.installEventFilter(self)
        self.resize(self._window.size())
        self.raise_()
        self.show()
        self._apply_step()

    def eventFilter(self, obj, event: QEvent) -> bool:
        if obj is self._window and event.type() == QEvent.Type.Resize:
            self.resize(self._window.size())
        return super().eventFilter(obj, event)

    def finish(self) -> None:
        self._window.removeEventFilter(self)
        if self.restore_tab is not None:
            self._window.tabs.setCurrentIndex(self.restore_tab)
            self.restore_tab = None
        self.hide()
        self.closed.emit()
        self.deleteLater()

    def next(self) -> None:
        if self.current_index < len(self._steps) - 1:
            self.current_index += 1
            self._apply_step()
        else:
            # The button reads "Finish" on the last step, so it must actually
            # close the tour instead of doing nothing.
            self.finish()

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
    """The tour content, bound to a concrete MainWindow.

    Every step names a feature the app actually has. When a feature is added,
    the tour is part of the change — a tour that describes an older app is
    worse than none.
    """
    steps = [
        TourStep(
            None, "Welcome to KeKar",
            "KeKar keeps your properties, listings, photos, applicant notes "
            "and leases in one place, stored only on this device. This short "
            "tour shows you around. Your own data is not touched."),
        TourStep(
            window.drawer, "Your properties",
            "This is your property list. The search box filters as you type — "
            "it matches the address, city, ZIP, pet policy, notes and every "
            "enabled amenity. Click a property here to load it in the form "
            "and emphasise its dates on the calendar. '+ Add New Property' "
            "brings these details to the "
            "front, focuses the address field and leaves a hint in the status "
            "bar, so you can always see that it worked."),
        TourStep(
            window.property_form, "The details form",
            "Address, rent, deposit and the rest. Use Type to switch a unit "
            "to a short stay, which brings its own nightly rate, fees and "
            "minimum stay. In Amenities you can record a one- or two-car "
            "garage and Street parking or Driveway, and the Pet policy field "
            "feeds the lease. 'Preview listing' builds a copy package you can "
            "paste into Zillow for a rental, or Booking.com for a short "
            "stay. 'Copy listing' copies the generic version for any site."
            if features.is_lite() else
            "Address, rent, deposit and the rest. Use Type to switch a unit "
            "to a short stay, which brings its own nightly rate, fees, "
            "minimum stay and portal calendars. In Amenities you can record "
            "a one- or two-car garage and Street parking or Driveway, and the "
            "Pet policy field feeds the lease. 'Preview listing' builds a "
            "copy package — Zillow and apartments.com for a rental, Airbnb, "
            "Vrbo and Booking.com for a short stay — and the action button "
            "reads 'Publish to Marketplace' (the opt-in Facebook auto-fill) "
            "for a rental, or 'Portal listing…' for a short stay."),
        TourStep(
            window.photo_panel, "Photos",
            "Add photos for a property and choose one as the cover — that is "
            "the image shown in the property list. Click the Photos heading to "
            "collapse this section; it remembers your choice next time."),
        TourStep(
            window.crm_tab, "Applicants",
            "Track every applicant through the pipeline, from first enquiry "
            "to approved or rejected. The Property column is a live dropdown "
            "of your saved properties. Click any row to open the full profile "
            "below — edit the name, property, contact, stage and notes, then "
            "press Save profile.",
            on_enter=lambda overlay: _show_tab(window, overlay, 1)),
        TourStep(
            window.lease_tab, "Leases",
            "Draw up a lease from a template: upload your own example lease or "
            "use the one provided. Generate a filled-in copy for any "
            "property and tenant — the Property dropdown is filled from your "
            "saved properties. A property that allows pets adds a refundable "
            "pet deposit clause automatically; custom templates can use the "
            "{{pet_deposit}} marker. Then copy, print, email or save the "
            "result.",
            on_enter=lambda overlay: _show_tab(window, overlay, 2)),
        TourStep(
            window.calendar_tab, "Calendar and short stays",
            "Move-in and move-out dates you enter on a property appear here "
            "automatically: green for move-in, red for move-out, purple for "
            "a short-stay reservation. Each address takes one line with both "
            "its move-in and move-out dates; the property you selected in the "
            "list is shown in bold. Click any highlighted date to see which "
            "property and event it belongs to. The Short stays panel below "
            "manages every booking — guest, dates and payout"
            + ("" if features.is_lite() else
               ", with the portal and import from the property form")
            + ". Everything stays on this device.",
            on_enter=lambda overlay: _show_tab(window, overlay, 3)),
        TourStep(
            window.chat_pane, "The assistant",
            "Ask questions in plain language, or give an instruction like "
            "'draft a message to John'. It can read and update your records."),
        TourStep(
            window.menuBar(), "Panels, themes and accounts",
            ("The labelled button at the right end of this bar collapses or "
             "expands the property list. View switches between Light, Dark "
             "and OLED; text stays readable in every theme. Help → Calendar "
             "legend explains the date colours, and Check for updates pulls "
             "new releases from GitHub. File → Accounts sets up a "
             "login and decides whether KeKar asks for one when it starts.")
            if features.is_lite() else
            ("The two buttons at the right end of this bar collapse the "
             "property list and the chat, and View switches between Light, "
             "Dark and OLED; text stays readable in every theme. Help → "
             "Calendar legend explains the date colours, Check for updates "
             "pulls new releases from GitHub, and File → Accounts sets up a login and decides whether KeKar asks for one when "
             "it starts.")),
        TourStep(
            window.logo_label, "The brand",
            "Click the wordmark to open the Help menu — the guided tour, "
            "Calendar legend, About and Exit demo mode all live there. The same mark is the "
            "window, taskbar and start-menu icon."),
        TourStep(
            None, "You're in demo mode",
            "Everything you see is sample data. Your own records are safe and "
            "unchanged. Use 'Exit demo mode' in the Help menu when you're "
            "ready to work with your real data."),
    ]
    if not features.chat_enabled():
        steps = [step for step in steps if step.title != "The assistant"]
    return steps


def _show_tab(window, overlay: "TourOverlay", index: int) -> None:
    """Switch to a tab for the duration of its step.

    Records the tab to restore on the overlay that is running the step. Only
    the first switch is recorded, so a tour that visits several tabs still
    returns to wherever the user started.
    """
    if overlay.restore_tab is None:
        overlay.restore_tab = window.tabs.currentIndex()
    window.tabs.setCurrentIndex(index)
