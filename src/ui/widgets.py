"""Shared widgets: status pill, offline banner, section headings."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


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


class SectionLabel(QLabel):
    """A bold heading used above groups of controls."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        from .theme import font
        self.setFont(font(10, bold=True))
        self.setStyleSheet("color:#4a453e;")
