"""Check for and install GitHub release updates."""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from ..services import updater
from . import worker


class _UpdateWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, mode: str, info: dict | None = None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.info = info

    def run(self) -> None:
        try:
            if self.mode == "check":
                self.succeeded.emit(updater.fetch_latest())
            else:
                self.succeeded.emit(updater.stage_update(self.info or {}))
        except Exception as exc:
            self.failed.emit(" ".join(str(exc).split()))


class UpdateDialog(QDialog):
    """Small dialog that checks GitHub and stages an update on request."""

    def __init__(self, app, parent: QWidget | None = None, *,
                 auto_check: bool = True):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Check for updates")
        self.resize(420, 190)
        self._info: dict | None = None
        self._thread: QThread | None = None

        layout = QVBoxLayout(self)
        self.status = QLabel("Checking GitHub for the latest release...")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

        buttons = QHBoxLayout()
        self.install_btn = QPushButton("Install update")
        self.install_btn.setEnabled(False)
        self.close_btn = QPushButton("Close")
        self.install_btn.clicked.connect(self.install)
        self.close_btn.clicked.connect(self.close)
        buttons.addStretch(1)
        buttons.addWidget(self.install_btn)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        if auto_check:
            self._start("check")

    def _start(self, mode: str, info: dict | None = None) -> None:
        thread = worker.register(_UpdateWorker(mode, info, self))
        thread.succeeded.connect(self._on_succeeded)
        thread.failed.connect(self._on_failed)
        self._thread = thread
        thread.start()

    def _reap(self) -> None:
        worker.reap(self._thread)
        self._thread = None

    def _on_succeeded(self, result) -> None:
        self._reap()
        if self._info is None:
            self._show_info(result)
        else:
            self._staged(result)

    def _on_failed(self, message: str) -> None:
        self._reap()
        self.status.setText("Could not check for updates.")
        self.detail.setText(message)

    def _show_info(self, info: dict) -> None:
        self._info = info
        current = self.app.current_theme() if hasattr(self.app, "current_theme") else None
        if current is not None:
            self.setStyleSheet(
                f"background:{current.panel}; color:{current.text};")
        if updater.is_newer(info.get("tag", "")):
            self.status.setText(f"Version {info.get('version', '')} is available.")
            self.detail.setText(
                "Downloading and staging can take a few minutes. KeKar will "
                "close and restart when the files are ready.")
            self.install_btn.setEnabled(True)
        else:
            self.status.setText("You are up to date.")
            self.detail.setText(
                f"Current version: {info.get('version', '')}.")

    def install(self) -> None:
        self.install_btn.setEnabled(False)
        self.status.setText("Downloading and staging the update...")
        self._start("stage", self._info)

    def _staged(self, script) -> None:
        self.status.setText("Update ready.")
        self.detail.setText(
            "KeKar will close for a moment and reopen with the new version.")
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
        QTimer.singleShot(700, lambda: self._finish_update(script))

    @staticmethod
    def _finish_update(script) -> None:
        from PyQt6.QtWidgets import QApplication
        updater.launch_apply_script(script)
        QApplication.quit()
