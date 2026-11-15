"""Listing preview and per-channel copy packages.

Zillow and apartments.com have no posting API, so the dialog offers a package
shaped like each site's form: pick a channel, copy, paste. The generic package
still works for any other site.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                             QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
                             QWidget)

from ..data.models import Property
from ..services.clipboard import copy_text
from ..services.listing_channels import (CHANNELS, channel_label,
                                         compile_channel, known_channels)
from ..services.listing_compiler import compile_listing, validate_listing
from .theme import font


class ListingDialog(QDialog):
    """Shows exactly what "Copy listing" would put on the clipboard."""

    def __init__(self, app, prop: Property, parent=None):
        super().__init__(parent)
        self.app = app
        self.prop = prop
        self.setWindowTitle(f"Listing — {prop.address}")
        self.resize(700, 700)

        layout = QVBoxLayout(self)

        picker = QHBoxLayout()
        picker.addWidget(QLabel("<b>Channel</b>"))
        self.channel = QComboBox()
        self.channel.addItem("Any site (generic)", "generic")
        for key in known_channels():
            self.channel.addItem(CHANNELS[key]["label"], key)
        self.channel.currentIndexChanged.connect(self._refresh)
        picker.addWidget(self.channel, 1)
        layout.addLayout(picker)

        self.note = QLabel(
            "Zillow and apartments.com have no posting API, so KeKar builds "
            "the listing for each site's form. Copy it and paste it in — "
            "posting stays with you.")
        self.note.setWordWrap(True)
        self.note.setFont(font(9))
        layout.addWidget(self.note)

        self.text = QPlainTextEdit()
        self.text.setFont(font(11))
        layout.addWidget(self.text, 1)

        self.problems = QLabel("")
        self.problems.setWordWrap(True)
        self.problems.setFont(font(9))
        layout.addWidget(self.problems)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        copy_btn = QPushButton("Copy to clipboard")
        copy_btn.clicked.connect(self._copy)
        buttons.addButton(copy_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(buttons)

        self._refresh()

    def _current(self) -> str:
        return self.channel.currentData()

    def _refresh(self) -> None:
        channel = self._current()
        if channel == "generic":
            body = compile_listing(self.prop)
            self.text.setReadOnly(True)
            self.text.setPlainText(body)
            problems = validate_listing(body)
        else:
            package = compile_channel(self.prop, channel)
            self.text.setReadOnly(True)
            self.text.setPlainText(package.as_text())
            problems = list(package.warnings)
        self.problems.setStyleSheet(
            f"color:{self.app.current_theme().warn_text};")
        self.problems.setText("Before you post: " + "; ".join(problems)
                              if problems else "")

    def _copy(self) -> None:
        text = self.text.toPlainText()
        copy_text(text)
        label = ("listing" if self._current() == "generic"
                 else channel_label(self._current()))
        self.app.main_window.status(f"{label} copied — paste it into the site.")
