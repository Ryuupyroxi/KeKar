"""Shared widgets: status pill, offline banner, section headings."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                             QWidget)


class StatusPill(QLabel):
    """A small rounded status badge.

    Status is conveyed by colour only in the property list; the pill is for
    the detail form, where the text is useful.
    """

    def __init__(self, text: str = "", color: str = "#2e7d32", parent=None):
        super().__init__(text, parent)
        self.set_color(color)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_color(self, color: str) -> None:
        self.setStyleSheet(
            f"background:{color}; color:white; border-radius:9px; "
            f"padding:3px 12px; font-weight:600;")


class OfflineBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(
            "Offline mode — your property data is safe and fully usable. "
            "Chat and AI features need a connection.")
        self.label.setStyleSheet("background:#fff3cd; color:#664d03; padding:8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)


class DemoBanner(QWidget):
    """Shown while demo mode is active, so it is never a surprise.

    Demo mode shares everything except the database, so a visible reminder is
    the difference between "exploring safely" and "where did my data go".
    """

    exited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(
            "Demo mode — sample data. Your own records are not shown.")
        self.label.setStyleSheet("background:#e3f2fd; color:#0d47a1; padding:8px;")
        exit_button = QPushButton("Exit demo mode")
        exit_button.clicked.connect(self.exited)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(exit_button)


class SectionLabel(QLabel):
    """A bold heading used above groups of controls."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        from .theme import font
        self.setFont(font(10, bold=True))
        self.setStyleSheet("color:#4a453e;")
