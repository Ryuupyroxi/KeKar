"""Shared widgets: status pill, banners, section headings.

Every colour comes from the active palette, so a theme change is a single
switch. Each widget exposes ``apply_theme(theme)`` for that purpose.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                             QWidget)

from .palette import Theme, text_on


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
            f"background:{color}; color:{text_on(color)}; border-radius:9px; "
            f"padding:3px 12px; font-weight:600;")

    def apply_theme(self, theme: Theme) -> None:
        """Keep the current meaning but re-read its colour from the palette."""
        self.set_color(theme.online)


class OfflineBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(
            "Offline mode — your property data is safe and fully usable. "
            "Chat and AI features need a connection.")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

    def apply_theme(self, theme: Theme) -> None:
        self.label.setStyleSheet(
            f"background:{theme.warn_bg}; color:{theme.warn_text}; padding:8px;")


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
        exit_button = QPushButton("Exit demo mode")
        exit_button.clicked.connect(self.exited)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(exit_button)

    def apply_theme(self, theme: Theme) -> None:
        self.label.setStyleSheet(
            f"background:{theme.info_bg}; color:{theme.info_text}; padding:8px;")


class SectionLabel(QLabel):
    """A bold heading used above groups of controls."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        from .theme import font
        self.setFont(font(10, bold=True))

    def apply_theme(self, theme: Theme) -> None:
        self.setStyleSheet(f"color:{theme.text_secondary};")
