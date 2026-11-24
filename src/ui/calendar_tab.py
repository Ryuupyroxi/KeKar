"""Calendar tab: property move-in/move-out dates on a real calendar."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtWidgets import (QCalendarWidget, QHBoxLayout, QLabel, QListWidget,
                             QTabWidget, QVBoxLayout, QWidget)

from .stays_tab import StaysTab

MOVE_IN_COLOUR = "#2e7d32"
MOVE_OUT_COLOUR = "#b71c1c"
SHORT_STAY_COLOUR = "#6a1b9a"


class CalendarTab(QWidget):
    """Read-only month view plus a sorted list of property dates."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Calendar")
        self._marked: list[QDate] = []

        layout = QHBoxLayout(self)
        left = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        left.addWidget(self.calendar)
        layout.addLayout(left, 1)

        dates_panel = QWidget()
        right = QVBoxLayout(dates_panel)
        self.summary = QLabel("No property dates yet.")
        self.summary.setWordWrap(True)
        right.addWidget(self.summary)
        self.events = QListWidget()
        right.addWidget(self.events, 1)

        self.stays = StaysTab(app, self)
        self.panels = QTabWidget()
        self.panels.addTab(dates_panel, "Dates")
        self.panels.addTab(self.stays, "Short stays")
        layout.addWidget(self.panels, 1)
        self.reload()

    def reload(self) -> None:
        """Rebuild highlights and the event list from all saved records."""
        self.stays.reload()
        for day in self._marked:
            self.calendar.setDateTextFormat(day, QTextCharFormat())
        self._marked = []
        self.events.clear()
        rows: list[tuple[date, str]] = []
        for prop in self.app.property_repo.list():
            for label, value, colour in (
                    ("Move-in", prop.move_in_date, MOVE_IN_COLOUR),
                    ("Move-out", prop.move_out_date, MOVE_OUT_COLOUR)):
                if not value:
                    continue
                day = QDate.fromString(value, Qt.DateFormat.ISODate)
                if not day.isValid():
                    continue
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(colour))
                fmt.setForeground(QColor("white"))
                self.calendar.setDateTextFormat(day, fmt)
                self._marked.append(day)
                rows.append((date(day.year(), day.month(), day.day()),
                             f"{label} — {prop.address} ({value})"))
        for prop in self.app.property_repo.list():
            for stay in self.app.booking_repo.list(property_id=prop.id):
                try:
                    start = date.fromisoformat(stay.check_in)
                    end = date.fromisoformat(stay.check_out)
                except (ValueError, TypeError):
                    continue
                day = start
                while day < end:
                    marked = QDate(day.year, day.month, day.day)
                    fmt = QTextCharFormat()
                    fmt.setBackground(QColor(SHORT_STAY_COLOUR))
                    fmt.setForeground(QColor("white"))
                    self.calendar.setDateTextFormat(marked, fmt)
                    self._marked.append(marked)
                    day = date.fromordinal(day.toordinal() + 1)
                rows.append((start, f"Short stay — {stay.guest_name} — "
                                    f"{prop.address} ({stay.check_in})"))
        for _, text in sorted(rows):
            self.events.addItem(text)
        self.summary.setText(
            f"{len(rows)} date(s). Green = move-in, red = move-out, "
            f"purple = short stay."
            if rows else "No move-in or move-out dates in any property yet.")
