"""A read-only preview of the compiled listing, with a copy button."""
from __future__ import annotations

from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QPlainTextEdit,
                             QPushButton, QVBoxLayout)

from ..data.models import Property
from ..services.clipboard import copy_text
from ..services.listing_compiler import compile_listing, validate_listing
from .theme import font


class ListingDialog(QDialog):
    """Shows exactly what "Copy listing" would put on the clipboard."""

    def __init__(self, app, prop: Property, parent=None):
        super().__init__(parent)
        self.app = app
        self.prop = prop
        self.setWindowTitle(f"Listing preview — {prop.address}")
        self.resize(660, 660)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Preview</b> — this is what gets copied:"))
        self.text = QPlainTextEdit()
        self.text.setPlainText(compile_listing(prop))
        self.text.setReadOnly(True)
        self.text.setFont(font(11))
        layout.addWidget(self.text, 1)

        problems = validate_listing(self.text.toPlainText())
        if problems:
            note = QLabel("Missing details: " + "; ".join(problems))
            note.setFont(font(9))
            note.setStyleSheet("color:#a15c00;")
            layout.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        copy_btn = QPushButton("Copy to clipboard")
        copy_btn.clicked.connect(self._copy)
        buttons.addButton(copy_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(buttons)

    def _copy(self) -> None:
        copy_text(self.text.toPlainText())
        self.app.main_window.status("Listing copied — paste it anywhere.")
