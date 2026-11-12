"""Settings: API key, model chain, browser, backups."""
from __future__ import annotations

import asyncio

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QSpinBox, QTextEdit, QVBoxLayout)

from .._version import APP_NAME, APP_VERSION
from ..data.backup import create_backup, list_backups, restore_backup
from . import worker


class _VerifyThread(QThread):
    """Runs the provider check off the UI thread."""

    done = pyqtSignal(bool, str)

    def __init__(self, app):
        super().__init__()
        self.app = app

    def run(self):
        try:
            ok, message = asyncio.run(self.app.client.verify_key())
        except Exception as exc:
            ok, message = False, f"Could not check the key: {type(exc).__name__}"
        self.done.emit(ok, message)


class SettingsDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._verify: _VerifyThread | None = None
        self.setWindowTitle(f"{APP_NAME} Settings")
        self.resize(600, 560)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setText(app.settings.api_key)
        form.addRow("API key", self.key_input)

        self.models_input = QTextEdit()
        self.models_input.setPlainText("\n".join(app.settings.model_chain))
        self.models_input.setMaximumHeight(90)
        form.addRow("Models (one per line, tried in order)", self.models_input)

        self.autofill = QCheckBox("Auto-fill Marketplace listings (experimental)")
        self.autofill.setChecked(app.settings.autofill_enabled)
        form.addRow(self.autofill)

        self.browser = QComboBox()
        self.browser.addItems(["auto", "chrome", "edge"])
        self.browser.setCurrentText(app.settings.browser_kind)
        form.addRow("Browser", self.browser)

        self.keep_days = QSpinBox()
        self.keep_days.setRange(1, 365)
        self.keep_days.setValue(app.settings.backup_keep_days)
        form.addRow("Keep backups for (days)", self.keep_days)

        form.addRow("", QLabel(
            f"{APP_NAME} {APP_VERSION} — your data stays on this drive."))
        layout.addLayout(form)

        actions = QFormLayout()
        self.test_btn = QPushButton("Test connection")
        self.test_btn.clicked.connect(self._test_connection)
        actions.addRow(self.test_btn)

        remove_btn = QPushButton("Remove stored key")
        remove_btn.clicked.connect(self._remove_key)
        actions.addRow(remove_btn)

        backup_btn = QPushButton("Back up now")
        backup_btn.clicked.connect(self._backup_now)
        actions.addRow(backup_btn)

        restore_btn = QPushButton("Restore from backup...")
        restore_btn.clicked.connect(self._restore)
        actions.addRow(restore_btn)
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        settings = self.app.settings
        settings.api_key = self.key_input.text().strip()
        settings.model_chain = [m.strip() for m in
                                self.models_input.toPlainText().splitlines()
                                if m.strip()]
        settings.autofill_enabled = self.autofill.isChecked()
        settings.browser_kind = self.browser.currentText()
        settings.backup_keep_days = self.keep_days.value()
        try:
            settings.save()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME,
                                f"Could not save settings: {exc}")
            return
        self.accept()

    def _test_connection(self) -> None:
        """Ask the provider whether the pasted key works."""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, APP_NAME, "Paste an API key first.")
            return
        self.app.settings.api_key = key
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Checking...")
        self._verify = worker.register(_VerifyThread(self.app))
        self._verify.done.connect(self._on_test_result)
        self._verify.start()

    def _on_test_result(self, ok: bool, message: str) -> None:
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Test connection")
        worker.reap(self._verify)
        self._verify = None
        QMessageBox.information(self, APP_NAME, message)

    def _remove_key(self) -> None:
        answer = QMessageBox.question(
            self, APP_NAME,
            "Remove the stored API key from this drive?\n\n"
            "The assistant will stop working until you paste a new one.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.key_input.clear()
        self.app.settings.api_key = ""
        try:
            self.app.settings.save()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not save: {exc}")
            return
        self.app.main_window.status("API key removed.")

    def _backup_now(self) -> None:
        path = create_backup(self.app.db, label="manual")
        QMessageBox.information(self, APP_NAME, f"Backup created:\n{path}")

    def _restore(self) -> None:
        backups = list_backups()
        if not backups:
            QMessageBox.information(self, APP_NAME, "No backups yet.")
            return
        answer = QMessageBox.warning(
            self, APP_NAME,
            f"Restore the newest backup?\n\n{backups[0].name}\n\n"
            f"Current data will be replaced.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        restore_backup(self.app.db, backups[0])
        self.app.property_repo.conn.commit()
        self.app.main_window.reload_all()
        QMessageBox.information(self, APP_NAME, "Backup restored.")
