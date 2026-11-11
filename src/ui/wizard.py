"""Guided first-run setup: database, API key."""
from __future__ import annotations

import os

from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QLineEdit,
                             QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

from ..paths import data_dir


class FirstRunWizard(QDialog):
    """Two-page setup: welcome, then API key.

    Uses explicit Back/Continue buttons rather than QWizard — QWizard's button
    set is fixed, and a plain QDialog keeps the flow easy to test.
    """

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Welcome to KeKar")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        self.pages.addWidget(self._welcome_page())
        self.pages.addWidget(self._api_page())

        self.button_box = QDialogButtonBox()
        self.back_button = self.button_box.addButton(
            "Back", QDialogButtonBox.ButtonRole.ActionRole)
        self.next_button = self.button_box.addButton(
            "Continue", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = self.button_box.addButton(
            "Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(self.button_box)

        self.back_button.clicked.connect(self._go_back)
        self.next_button.clicked.connect(self._go_next)
        self.cancel_button.clicked.connect(self.reject)
        self._update_buttons()

    def _welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "<h2>Welcome to KeKar</h2>"
            "<p>KeKar keeps your rental properties, listings, photos, and "
            "applicant notes in one place — stored only on this device.</p>"
            "<p>We'll set up your secure local database now. This takes a "
            "few seconds.</p>"))
        return page

    def _api_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            "<h3>Connect your assistant</h3>"
            "<p>Paste the API key for KeKar's dedicated account. "
            "It is stored encrypted on this drive only.</p>"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-or-...")
        self.key_input.setText(os.environ.get("KEKAR_API_KEY", ""))
        layout.addWidget(self.key_input)
        return page

    def _update_buttons(self) -> None:
        last = self.pages.currentIndex() == self.pages.count() - 1
        self.back_button.setEnabled(self.pages.currentIndex() > 0)
        self.next_button.setText("Get Started" if last else "Continue")

    def _go_back(self) -> None:
        self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1))
        self._update_buttons()

    def _go_next(self) -> None:
        if self.pages.currentIndex() == self.pages.count() - 1:
            ok, message = self.save_key()
            if not ok:
                QMessageBox.warning(self, "KeKar", message)
                return
            # Verify against the provider. This is a real network call, so it
            # can be slow — tell the user rather than freezing silently.
            self.next_button.setEnabled(False)
            self.next_button.setText("Checking...")
            try:
                ok, message = self._verify_connection()
            finally:
                self.next_button.setEnabled(True)
                self._update_buttons()
            if not ok:
                QMessageBox.warning(self, "KeKar", message)
                return
            self.accept()
            return
        self.pages.setCurrentIndex(self.pages.currentIndex() + 1)
        self._update_buttons()

    def save_key(self) -> tuple[bool, str]:
        """Store the pasted key. No network involved."""
        key = self.key_input.text().strip()
        if not key:
            return False, "Please paste an API key, or press Cancel to close KeKar."
        self.app.settings.api_key = key
        try:
            self.app.settings.save()
        except Exception as exc:
            return False, f"Could not save the key securely: {exc}"
        data_dir()  # ensure the data tree exists
        return True, "Saved."

    def _verify_connection(self) -> tuple[bool, str]:
        """Ask the provider whether the saved key works.

        Runs the async check on a private event loop so it cannot interfere
        with Qt's own loop.
        """
        import asyncio

        try:
            return asyncio.run(self.app.client.verify_key())
        except Exception as exc:  # never let a network glitch crash setup
            return False, f"Could not check the key: {type(exc).__name__}"

    def test_connection(self) -> tuple[bool, str]:
        """Test seam used by the test suite: save then verify."""
        ok, message = self.save_key()
        if not ok:
            return ok, message
        return self._verify_connection()
