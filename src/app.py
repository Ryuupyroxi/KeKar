"""QApplication subclass + dependency container."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from . import features
from ._version import APP_NAME, APP_VERSION, display_name
from .config.settings import Settings
from .data.applicant_repo import ApplicantRepo
from .data.backup import open_with_recovery, prune_backups
from .data.booking_repo import BookingRepo
from .data.chat_repo import ChatRepo
from .data.db import Database
from .data.demo_seed import seed_if_empty
from .data.lease_repo import LeaseRepo
from .data.portal_repo import PortalRepo
from .data.property_repo import PropertyRepo
from .data.user_repo import UserRepo
from .paths import database_path, demo_database_path, icon_path
from .ui.main_window import MainWindow
from .ui.palette import Theme, is_valid, resolve
from .ui.theme import app_font, build_stylesheet


class Application(QApplication):
    offline_changed = pyqtSignal(bool)
    #: Emitted after the assistant changes stored data, so the GUI can reload.
    data_changed = pyqtSignal()
    #: Emitted when the theme changes, so custom-painted widgets can restyle.
    theme_changed = pyqtSignal(object)

    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(APP_VERSION)
        self.setApplicationDisplayName(f"{display_name()} Property Manager")
        self.setFont(app_font())

        self.settings = Settings.load()
        # The taskbar, the start menu and the title bar all read this.
        self.setWindowIcon(QIcon(str(icon_path())))
        # Lite never talks to a provider, so it never repairs (or needs) the
        # saved provider choice. Full KeKar behaves exactly as before.
        self.provider_note = ""
        if features.chat_enabled():
            from .agent import providers
            self.provider_note = providers.migrate_default_provider(
                self.settings)
        self.demo_mode = False
        self.db = None
        # Resolve the two database locations once. Re-resolving on every switch
        # would open a *different* file if the data directory changed mid-run,
        # silently losing the real database.
        self._real_db_path = database_path()
        self._demo_db_path = demo_database_path()
        if features.chat_enabled():
            from .agent.client import LLMClient
            from .agent.memory import MemoryStore
            self.memory = MemoryStore()
            self.client = LLMClient(self.settings)
        self._open_database(self._real_db_path)

        self.main_window = MainWindow(self)
        self.offline_changed.connect(self.main_window.show_offline)
        # The agent writes from a worker thread; the signal is queued back to
        # the GUI thread, so the sidebar and CRM tab see the change.
        self.data_changed.connect(self.main_window.reload_all)
        prune_backups(self.settings.backup_keep_days)
        # Applied last so the main window and every custom-painted widget exist.
        self.apply_theme(self.settings.theme)
        # Accounts are opt-in; with require_login off this does nothing.
        self.current_user = None
        self.session_token = self.settings.session_token or None
        self._restore_session()

    # -- accounts ----------------------------------------------------------

    def _restore_session(self) -> None:
        """Pick up a saved session, dropping one that has expired."""
        if not self.session_token:
            return
        user = self.user_repo.session_user(self.session_token)
        if user is None:
            self.session_token = None
            self.settings.session_token = ""
            try:
                self.settings.save()
            except Exception:
                pass
            return
        self.current_user = user

    def login(self, username: str, password: str) -> bool:
        """Validate credentials and open a session. Returns True on success."""
        user = self.user_repo.authenticate(username, password)
        if user is None:
            return False
        self.current_user = user
        self.session_token = self.user_repo.create_session(user["id"])
        self.settings.session_token = self.session_token
        try:
            self.settings.save()
        except Exception:
            pass
        self.main_window.set_locked(False)
        self.main_window.status(f"Signed in as {user['display_name'] or user['username']}.")
        return True

    def logout(self) -> None:
        """Drop the session. The window locks if a login is required."""
        if self.session_token:
            self.user_repo.delete_session(self.session_token)
        self.session_token = None
        self.current_user = None
        self.settings.session_token = ""
        try:
            self.settings.save()
        except Exception:
            pass
        if self.settings.require_login:
            self.main_window.set_locked(True)
        self.main_window.status("Signed out.")

    def lock(self) -> None:
        """Hide the portfolio behind the login panel."""
        self.main_window.set_locked(True)
        self.main_window.status("Locked.")

    def unlock_with_dialog(self) -> bool:
        """Show the login dialog; True when the user got in."""
        from .ui.login_dialog import LoginDialog

        dialog = LoginDialog(self, self.main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        return self.current_user is not None

    def maybe_require_login(self) -> None:
        """Lock at startup when a login is required and there is no session."""
        if not self.settings.require_login:
            return
        if self.current_user is not None:
            return
        self.main_window.set_locked(True)

    def _open_database(self, path: Path | None) -> None:
        """Open a database and point the repositories at it.

        ``path=None`` means the user's real database; the demo path comes from
        ``paths.demo_database_path()`` so it can never drift.
        """
        if self.db is not None:
            try:
                self.db.close()
            except Exception:
                pass
        self.db = open_with_recovery(path)
        self._rebuild_repos()

    def _rebuild_repos(self) -> None:
        """Re-point the repositories at the current database.

        Repositories resolve their connection lazily through the Database, so
        rebuilding them is enough — no view has to be reconstructed. The agent
        and its chat history exist only in the full build; Lite composes none
        of them even though the tables are still present on disk.
        """
        self.property_repo = PropertyRepo(self.db)
        self.applicant_repo = ApplicantRepo(self.db)
        self.lease_repo = LeaseRepo(self.db)
        self.booking_repo = BookingRepo(self.db)
        self.portal_repo = PortalRepo(self.db)
        self.user_repo = UserRepo(self.db)
        self.chat_repo = ChatRepo(self.db) if features.chat_enabled() else None
        if features.chat_enabled():
            from .agent.runner import AgentRunner
            from .agent.tools import ToolContext
            self.ctx = ToolContext(db=self.db, property_repo=self.property_repo,
                                   applicant_repo=self.applicant_repo,
                                   memory=self.memory, settings=self.settings,
                                   on_change=self.data_changed.emit)
            self.agent_runner = AgentRunner(self.client, self.settings,
                                            self.ctx)

    def enter_demo_mode(self) -> None:
        """Switch to the demo database. The real one is closed untouched."""
        if self.demo_mode:
            return
        self._open_database(self._demo_db_path)
        seed_if_empty(self.db)
        self.demo_mode = True
        self.main_window.reload_all()
        self.main_window.set_demo_mode(True)

    def exit_demo_mode(self) -> None:
        """Return to the user's real database."""
        if not self.demo_mode:
            return
        self._open_database(self._real_db_path)
        self.demo_mode = False
        self.main_window.reload_all()
        self.main_window.set_demo_mode(False)

    def maybe_offer_tour(self) -> None:
        """Offer the tour once, after first-run setup.

        Either answer marks the tour as done, so the question is never asked
        twice. Choosing "Yes" enters demo mode and starts the tour.
        """
        if self.settings.tour_completed:
            return

        from PyQt6.QtWidgets import QMessageBox

        answer = QMessageBox.question(
            self.main_window, "KeKar",
            "Take a quick tour?\n\n"
            "The tour uses sample data, so you can see everything working. "
            "Your own records are never touched.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        self.settings.tour_completed = True
        try:
            self.settings.save()
        except Exception:
            pass

        if answer != QMessageBox.StandardButton.Yes:
            return
        self.enter_demo_mode()
        self.main_window._start_tour()

    def apply_theme(self, key: str) -> Theme:
        """Switch the whole application to a theme and persist the choice.

        ``system`` follows the operating system, so it is re-read every time
        rather than cached. An unrecognised value falls back to light.
        """
        key = key if is_valid(key) else "system"
        theme = resolve(key)
        self.setStyleSheet(build_stylesheet(theme))
        self._theme = theme
        if self.settings.theme != key:
            self.settings.theme = key
            try:
                self.settings.save()
            except Exception:
                pass
        self.theme_changed.emit(theme)
        self.main_window.apply_theme(theme)
        return theme

    def current_theme(self) -> Theme:
        return getattr(self, "_theme", resolve(self.settings.theme))

    def show_main_window(self) -> None:
        self.main_window.show()

    def notify_error(self, message: str, parent=None) -> None:
        QMessageBox.warning(parent or self.main_window, "KeKar", message)
