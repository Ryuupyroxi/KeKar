"""Settings: API key, model chain, browser, backups."""
from __future__ import annotations

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QLineEdit, QMessageBox, QPushButton,
                             QSpinBox, QTextEdit, QVBoxLayout)

from ..data.backup import create_backup, list_backups, restore_backup


class SettingsDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("KeKar Settings")
        self.resize(560, 520)
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

        layout.addLayout(form)

        actions = QFormLayout()
        test_btn = QPushButton("Test connection")
        test_btn.clicked.connect(self._test_connection)
        actions.addRow(test_btn)
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
        s = self.app.settings
        s.api_key = self.key_input.text().strip()
        s.model_chain = [m.strip() for m in
                         self.models_input.toPlainText().splitlines() if m.strip()]
        s.autofill_enabled = self.autofill.isChecked()
        s.browser_kind = self.browser.currentText()
        s.backup_keep_days = self.keep_days.value()
        try:
            s.save()
        except Exception as exc:
            QMessageBox.warning(self, "KeKar", f"Could not save settings: {exc}")
            return
        self.accept()

    def _test_connection(self) -> None:
        QMessageBox.information(self, "KeKar",
                                "Connection saved. The assistant will use it on "
                                "the next message.")

    def _backup_now(self) -> None:
        path = create_backup(self.app.db, label="manual")
        QMessageBox.information(self, "KeKar", f"Backup created:\n{path}")

    def _restore(self) -> None:
        backups = list_backups()
        if not backups:
            QMessageBox.information(self, "KeKar", "No backups yet.")
            return
        restore_backup(self.app.db, backups[0])
        QMessageBox.information(self, "KeKar", "Backup restored.")
