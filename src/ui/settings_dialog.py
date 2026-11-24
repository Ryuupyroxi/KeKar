"""Settings: API key, model chain, browser, backups."""
from __future__ import annotations

import asyncio

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton,
                             QSpinBox, QTextEdit, QVBoxLayout)

from .. import features
from .._version import APP_NAME, APP_VERSION
from ..data.backup import create_backup, list_backups, restore_backup
from . import worker


def _providers():
    """Imported only in the full build; Lite never loads the AI stack."""
    from ..agent import providers
    return providers


class _ProviderThread(QThread):
    """Runs a provider task off the UI thread.

    Tasks: ``verify`` (test the saved setup), ``models`` (list the provider's
    models), ``detect`` (probe candidates for a key), ``probe`` (test one
    specific endpoint and model).
    """

    done = pyqtSignal(bool, object)

    def __init__(self, app, task: str, api_base: str = "", api_key: str = "",
                 model: str = "", candidates: tuple = ()):
        super().__init__()
        self.app = app
        self.task = task
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.candidates = candidates

    async def _run(self):
        if self.task == "verify":
            return await self.app.client.verify_key()
        if self.task == "models":
            return True, await _providers().fetch_models(self.api_base,
                                                      self.api_key)
        if self.task == "probe":
            return await _providers().probe(self.api_base, self.api_key,
                                         self.model)
        if self.task == "detect":
            for prov in self.candidates:
                model = prov.default_models[0] if prov.default_models else ""
                ok, message = await _providers().probe(prov.api_base,
                                                    self.api_key, model)
                if ok:
                    return True, (prov, message)
            # Nothing worked; report the last provider's own words.
            prov = self.candidates[-1]
            model = prov.default_models[0] if prov.default_models else ""
            _, message = await _providers().probe(prov.api_base, self.api_key,
                                               model)
            return False, (prov, message)
        raise ValueError(f"unknown task {self.task!r}")

    def run(self) -> None:
        try:
            ok, payload = asyncio.run(self._run())
        except Exception as exc:
            self.done.emit(False, f"{type(exc).__name__}: {exc}")
            return
        self.done.emit(bool(ok), payload)


class ModelPickerDialog(QDialog):
    """Pick models from the provider's list, with a filter box."""

    def __init__(self, models: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose models")
        self.resize(520, 600)
        self._chosen: list[str] = []

        layout = QVBoxLayout(self)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter, e.g. 'llama' or 'free'")
        self.filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter)

        self.list = QListWidget()
        for model in models:
            item = QListWidgetItem(model)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list.addItem(item)
        layout.addWidget(self.list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(needle)
                           and needle not in item.text().lower())

    def _accept(self) -> None:
        self._chosen = [self.list.item(i).text()
                        for i in range(self.list.count())
                        if self.list.item(i).checkState()
                        == Qt.CheckState.Checked]
        self.accept()

    def selected(self) -> list[str]:
        return list(self._chosen)


class SettingsDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._thread: _ProviderThread | None = None
        self.setWindowTitle(f"{APP_NAME} Settings")
        self.resize(600, 560)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.theme = QComboBox()
        for key, label in (("system", "Follow system"),
                           ("light", "Light"),
                           ("dark", "Dark"),
                           ("oled", "OLED")):
            self.theme.addItem(label, key)
        theme_index = self.theme.findData(app.settings.theme)
        self.theme.setCurrentIndex(theme_index if theme_index >= 0 else 0)
        self.theme.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("Theme", self.theme)

        if features.chat_enabled():
            self.key_input = QLineEdit()
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_input.setText(app.settings.api_key)
            form.addRow("API key", self.key_input)

            self.provider = QComboBox()
            for prov in _providers().PROVIDERS:
                self.provider.addItem(prov.name, prov.id)
            index = self.provider.findData(app.settings.provider)
            if index >= 0:
                self.provider.setCurrentIndex(index)
            self.provider.currentIndexChanged.connect(self._on_provider_changed)
            form.addRow("Provider", self.provider)

            detect_btn = QPushButton("Detect from key")
            detect_btn.setToolTip("Identify the provider from the key's "
                                  "format, then confirm it actually works.")
            detect_btn.clicked.connect(self._detect_provider)
            form.addRow("", detect_btn)

            self.api_base = QLineEdit()
            self.api_base.setText(app.settings.api_base)
            self.api_base.setPlaceholderText("https://…/api/v1")
            form.addRow("API endpoint", self.api_base)

            self.models_input = QTextEdit()
            self.models_input.setPlainText("\n".join(app.settings.model_chain))
            self.models_input.setMaximumHeight(90)
            self.models_input.setToolTip("Tried in order until one succeeds.")
            form.addRow("Models (one per line, tried in order)",
                        self.models_input)

            fetch_btn = QPushButton("Fetch the provider's model list")
            fetch_btn.clicked.connect(self._fetch_models)
            form.addRow("", fetch_btn)

            self.autofill = QCheckBox(
                "Auto-fill Marketplace listings (experimental)")
            self.autofill.setChecked(app.settings.autofill_enabled)
            form.addRow(self.autofill)

            if features.maps_enabled():
                self.maps_key = QLineEdit()
                self.maps_key.setEchoMode(QLineEdit.EchoMode.Password)
                self.maps_key.setText(app.settings.maps_key)
                self.maps_key.setPlaceholderText(
                    "Optional — address suggestions")
                form.addRow("Google Maps key", self.maps_key)

                self.maps_autofill = QCheckBox(
                    "Auto-fill empty City and ZIP from Google Maps")
                self.maps_autofill.setToolTip(
                    "Only blank fields are filled — anything you typed "
                    "is kept.")
                self.maps_autofill.setChecked(app.settings.maps_autofill)
                form.addRow(self.maps_autofill)

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
        if features.chat_enabled():
            self.test_btn = QPushButton("Test connection")
            self.test_btn.clicked.connect(self._test_connection)
            actions.addRow(self.test_btn)

            self.remove_btn = QPushButton("Remove stored key")
            self.remove_btn.clicked.connect(self._remove_key)
            actions.addRow(self.remove_btn)

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
        if features.chat_enabled():
            settings.api_key = self.key_input.text().strip()
            settings.provider = self.provider.currentData() or "custom"
            settings.api_base = self.api_base.text().strip()
            settings.model_chain = [m.strip() for m in
                                    self.models_input.toPlainText().splitlines()
                                    if m.strip()]
            settings.autofill_enabled = self.autofill.isChecked()
            settings.browser_kind = self.browser.currentText()
        if features.maps_enabled():
            settings.maps_key = self.maps_key.text().strip()
            settings.maps_autofill = self.maps_autofill.isChecked()
        settings.backup_keep_days = self.keep_days.value()
        try:
            settings.save()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME,
                                f"Could not save settings: {exc}")
            return
        self.accept()

    # -- provider detection and model discovery -----------------------------

    def _on_theme_changed(self, index: int) -> None:
        key = self.theme.itemData(index)
        if key:
            self.app.apply_theme(key)

    def _on_provider_changed(self, index: int) -> None:
        """Fill the endpoint and default models when a provider is picked."""
        prov = _providers().by_id(self.provider.itemData(index))
        if prov is None:
            return
        if prov.api_base:
            self.api_base.setText(prov.api_base)
        current = self.models_input.toPlainText()
        if prov.default_models and (not current.strip()
                                    or self._is_default_models(current)):
            self.models_input.setPlainText("\n".join(prov.default_models))

    def _is_default_models(self, text: str) -> bool:
        """True when the box still holds a preset's untouched model list."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return any(tuple(lines) == prov.default_models
                   for prov in _providers().PROVIDERS)

    def _start_task(self, task: str, **kwargs) -> None:
        self._set_busy(True)
        self._thread = worker.register(
            _ProviderThread(self.app, task, **kwargs))
        self._thread.done.connect(self._on_task_done)
        self._thread.start()

    def _set_busy(self, busy: bool) -> None:
        if getattr(self, "test_btn", None) is None:
            return
        for widget in (self.test_btn, self.key_input, self.provider,
                       self.api_base, self.models_input):
            widget.setEnabled(not busy)

    def _on_task_done(self, ok: bool, payload) -> None:
        if getattr(self, "test_btn", None) is None:
            return
        worker.reap(self._thread)
        self._thread = None
        self._set_busy(False)

        if isinstance(payload, tuple) and payload and isinstance(payload[0],
                                                                 _providers().Provider):
            prov, message = payload
            self._apply_provider(prov)
            QMessageBox.information(self, APP_NAME, message)
            return

        if isinstance(payload, list):
            picker = ModelPickerDialog(payload, self)
            if picker.exec() == ModelPickerDialog.DialogCode.Accepted:
                chosen = picker.selected()
                if chosen:
                    self.models_input.setPlainText("\n".join(chosen))
                    self.app.main_window.status(
                        f"{len(chosen)} models selected.")
            return

        QMessageBox.information(self, APP_NAME, str(payload))

    def _apply_provider(self, prov: _providers().Provider) -> None:
        index = self.provider.findData(prov.id)
        if index >= 0:
            self.provider.setCurrentIndex(index)
        if prov.api_base:
            self.api_base.setText(prov.api_base)
        if prov.default_models:
            self.models_input.setPlainText("\n".join(prov.default_models))

    def _detect_provider(self) -> None:
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, APP_NAME, "Paste an API key first.")
            return
        matches = _providers().detect(key)
        if not matches:
            QMessageBox.information(self, APP_NAME,
                                    _providers().unrecognized_hint(key))
            return
        self._start_task("detect", api_key=key, candidates=tuple(matches))

    def _fetch_models(self) -> None:
        api_base = self.api_base.text().strip()
        api_key = self.key_input.text().strip()
        if not api_base:
            QMessageBox.warning(self, APP_NAME,
                                "Set an API endpoint first — or pick a "
                                "provider above.")
            return
        if not api_key:
            QMessageBox.warning(self, APP_NAME, "Paste an API key first.")
            return
        self._start_task("models", api_base=api_base, api_key=api_key)

    def _test_connection(self) -> None:
        """Ask the provider whether the saved setup works end to end."""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, APP_NAME, "Paste an API key first.")
            return
        if not self.models_input.toPlainText().strip():
            QMessageBox.warning(self, APP_NAME,
                                "Add at least one model first.")
            return
        self.app.settings.api_key = key
        self.app.settings.provider = self.provider.currentData() or "custom"
        self.app.settings.api_base = self.api_base.text().strip()
        self.app.settings.model_chain = [
            m.strip() for m in self.models_input.toPlainText().splitlines()
            if m.strip()]
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Checking...")
        self._start_task("verify")

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
