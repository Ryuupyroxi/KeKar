"""QApplication subclass + dependency container."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from .agent.client import LLMClient
from .agent.memory import MemoryStore
from .agent.runner import AgentRunner
from .agent.tools import ToolContext
from ._version import APP_NAME, APP_VERSION
from .config.settings import Settings
from .data.applicant_repo import ApplicantRepo
from .data.backup import open_with_recovery, prune_backups
from .data.chat_repo import ChatRepo
from .data.db import Database
from .data.property_repo import PropertyRepo
from ._version import APP_NAME, APP_VERSION
from .ui.main_window import MainWindow
from .ui.theme import app_font


def _stylesheet_path() -> Path | None:
    """Locate styles.qss in dev and inside a bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS",
                            Path(sys.executable).resolve().parent))
        bundled = base / "resources" / "styles.qss"
        if bundled.exists():
            return bundled
    dev = Path(__file__).resolve().parent / "resources" / "styles.qss"
    return dev if dev.exists() else None


class Application(QApplication):
    offline_changed = pyqtSignal(bool)

    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setApplicationDisplayName(f"{APP_NAME} Property Manager")
        self.setFont(app_font())
        self._load_stylesheet()

        self.settings = Settings.load()
        self.db = open_with_recovery(None)
        self.property_repo = PropertyRepo(self.db.conn)
        self.applicant_repo = ApplicantRepo(self.db.conn)
        self.chat_repo = ChatRepo(self.db.conn)
        self.memory = MemoryStore()

        self.client = LLMClient(self.settings)
        self.ctx = ToolContext(db=self.db, property_repo=self.property_repo,
                               applicant_repo=self.applicant_repo,
                               memory=self.memory, settings=self.settings)
        self.agent_runner = AgentRunner(self.client, self.settings, self.ctx)

        self.main_window = MainWindow(self)
        self.offline_changed.connect(self.main_window.show_offline)
        prune_backups(self.settings.backup_keep_days)

    def _load_stylesheet(self) -> None:
        """Apply styles.qss when present; a missing file must not break startup."""
        path = _stylesheet_path()
        if path is None:
            return
        try:
            self.setStyleSheet(path.read_text(encoding="utf-8"))
        except OSError:
            pass

    def show_main_window(self) -> None:
        self.main_window.show()

    def notify_error(self, message: str, parent=None) -> None:
        QMessageBox.warning(parent or self.main_window, "KeKar", message)
