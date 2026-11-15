"""Main window: property drawer, detail/CRM tabs, chat pane, menu."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QMainWindow,
                             QMessageBox, QScrollArea, QSplitter, QTabWidget,
                             QVBoxLayout, QWidget)

from .._version import APP_NAME, APP_VERSION
from ..services import connectivity
from .chat_pane import ChatPane
from .crm_tab import CrmTab
from .photo_panel import PhotoPanel
from .property_drawer import PropertyDrawer
from .property_form import PropertyForm
from . import worker
from .settings_dialog import SettingsDialog
from .widgets import DemoBanner, OfflineBanner, StatusPill

PING_INTERVAL_MS = 30_000


class _PingThread(QThread):
    """Checks provider reachability without blocking the UI."""

    result = pyqtSignal(bool)

    def __init__(self, api_base: str):
        super().__init__()
        self.api_base = api_base

    def run(self) -> None:
        self.result.emit(connectivity.provider_reachable(self.api_base))


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.resize(440, 220)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"<h2>{APP_NAME} {APP_VERSION}</h2>"
            f"<p>A portable rental property manager.</p>"
            f"<p>Your properties, photos and applicant notes live in the "
            f"KeKarData folder next to the program. Nothing leaves this "
            f"drive except the questions you choose to send to the "
            f"assistant.</p>"
            f"<p>Data is stored locally in SQLite and backed up automatically."
            f"</p>"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.demo_mode = False
        self.setWindowTitle(f"{APP_NAME} Property Manager")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 720)

        self.offline_banner = OfflineBanner(self)
        self.offline_banner.hide()
        self.demo_banner = DemoBanner(self)
        self.demo_banner.exited.connect(self._exit_demo_mode)
        self.demo_banner.hide()
        self.status_pill = StatusPill("Online", "#2e7d32", self)
        self.statusBar().addPermanentWidget(self.status_pill)
        self._tour = None

        self._build_menu()

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.offline_banner)
        outer.addWidget(self.demo_banner)

        main_splitter = QSplitter(Qt.Orientation.Vertical)

        top = QSplitter(Qt.Orientation.Horizontal)
        self.drawer = PropertyDrawer(app)
        self.tabs = QTabWidget()

        self.property_form = PropertyForm(app)
        self.photo_panel = PhotoPanel(app)
        properties_tab = QWidget()
        pv = QVBoxLayout(properties_tab)
        pv.setContentsMargins(0, 0, 0, 0)
        # The form has more content than a short window can show. Without a
        # scroll area the group boxes were squeezed to their title bars and
        # the fields inside were clipped to zero height.
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        form_scroll.setWidget(self.property_form)
        pv.addWidget(form_scroll, 1)
        pv.addWidget(self.photo_panel)
        self.tabs.addTab(properties_tab, "Properties")
        self.crm_tab = CrmTab(app)
        self.tabs.addTab(self.crm_tab, "Applicants")

        top.addWidget(self.drawer)
        top.addWidget(self.tabs)
        top.setSizes([340, 900])
        main_splitter.addWidget(top)
        self.chat_pane = ChatPane(app)
        main_splitter.addWidget(self.chat_pane)
        main_splitter.setSizes([560, 200])

        outer.addWidget(main_splitter, 1)
        self.setCentralWidget(central)

        # wiring
        self.drawer.property_selected.connect(self._on_property_selected)
        self.drawer.add_requested.connect(self._new_property)
        self.property_form.property_saved.connect(self._on_property_saved)
        self.property_form.status_changed.connect(self._on_status_changed)
        self.property_form.property_deleted.connect(self._on_property_deleted)
        self.drawer.reload()
        self.crm_tab.reload()
        self.chat_pane.load_history()

        # offline detection
        self._ping: _PingThread | None = None
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(PING_INTERVAL_MS)
        self._ping_timer.timeout.connect(self.check_online)
        # Tests must not reach the network; conftest sets KEKAR_TESTING.
        if not os.environ.get("KEKAR_TESTING"):
            self._ping_timer.start()
            self.check_online()

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        self.settings_action = file_menu.addAction("Settings...")
        self.settings_action.triggered.connect(self._open_settings)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        view_menu = menubar.addMenu("&View")
        from PyQt6.QtGui import QActionGroup

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        self._theme_actions = {}
        for key, label in (("system", "Follow system"),
                           ("light", "Light"),
                           ("dark", "Dark"),
                           ("oled", "OLED")):
            action = view_menu.addAction(label)
            action.setCheckable(True)
            action.setActionGroup(theme_group)
            action.triggered.connect(
                lambda _=False, chosen=key: self._set_theme(chosen))
            self._theme_actions[key] = action
        self._refresh_theme_actions()

        help_menu = menubar.addMenu("&Help")
        tour_action = help_menu.addAction("Guided tour...")
        tour_action.triggered.connect(self._start_tour)
        self.exit_demo_action = help_menu.addAction("Exit demo mode")
        self.exit_demo_action.triggered.connect(self._exit_demo_mode)
        self.exit_demo_action.setVisible(False)
        help_menu.addSeparator()
        about_action = help_menu.addAction("About...")
        about_action.triggered.connect(lambda: AboutDialog(self).exec())

    def _open_settings(self) -> None:
        SettingsDialog(self.app, self).exec()

    # -- property wiring ---------------------------------------------------

    def _on_property_selected(self, property_id: int) -> None:
        self.property_form.load_property(property_id)
        self.photo_panel.load_property(property_id)

    def _new_property(self) -> None:
        self.property_form.load_property(None)
        self.photo_panel.load_property(None)
        self.property_form.address_input.setFocus()

    def _on_property_saved(self, property_id: int) -> None:
        self.drawer.reload()
        self.crm_tab.reload()
        self.photo_panel.load_property(property_id)
        prop = self.app.property_repo.get(property_id)
        self.status(f"Saved {prop.address if prop else property_id}")

    def _on_property_deleted(self) -> None:
        self.drawer.reload()
        self.crm_tab.reload()
        self.photo_panel.load_property(None)
        self.status("Property deleted.")

    def _on_status_changed(self, property_id: int, status: str) -> None:
        self.drawer.reload()
        self.status(f"Marked as {status}.")

    def reload_all(self) -> None:
        """Refresh every view — used after a backup restore."""
        self.drawer.reload()
        self.crm_tab.reload()
        current = self.property_form.current_id
        if current is None:
            return
        if self.app.property_repo.get(current) is None:
            self.property_form.load_property(None)
            self.photo_panel.load_property(None)
        else:
            self.property_form.load_property(current)
            self.photo_panel.load_property(current)

    def set_demo_mode(self, active: bool) -> None:
        """Reflect demo mode in the UI.

        Settings are shared with the real install, so the Settings dialog is
        disabled while demo mode is on — otherwise a tour could change the
        user's real API key.
        """
        self.demo_mode = active
        self.demo_banner.setVisible(active)
        self.settings_action.setEnabled(not active)
        self.exit_demo_action.setVisible(active)

    def _agent_busy(self) -> bool:
        return self.chat_pane._thread is not None

    def _start_tour(self) -> None:
        # Never stack two overlays: finish any tour that is already running.
        self._finish_tour()
        # Swapping the database under a running agent would make its answer
        # describe whichever database it lands on, so wait for it instead.
        if self._agent_busy():
            QMessageBox.information(
                self, APP_NAME,
                "The assistant is still working. Wait for its answer, then "
                "start the tour.")
            return
        if not self.app.demo_mode:
            answer = QMessageBox.question(
                self, APP_NAME,
                "The tour uses sample data, so you can see everything working.\n\n"
                "Your own records are never touched.\n\n"
                "Start the tour?")
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.app.enter_demo_mode()
        from .tour import TourOverlay, build_tour_steps
        overlay = TourOverlay(self, build_tour_steps(self))
        overlay.closed.connect(lambda: self._on_tour_closed(overlay))
        overlay.apply_theme(self.app.current_theme())
        self._tour = overlay
        overlay.resize(self.size())
        overlay.start()

    def _finish_tour(self) -> None:
        tour = self._tour
        self._tour = None
        if tour is not None:
            tour.finish()

    def _on_tour_closed(self, overlay) -> None:
        # The overlay destroys itself; drop the window's reference to it so a
        # later exit does not call into a deleted object.
        if self._tour is overlay:
            self._tour = None

    def _exit_demo_mode(self) -> None:
        if self._agent_busy():
            QMessageBox.information(
                self, APP_NAME,
                "The assistant is still working. Wait for its answer before "
                "leaving demo mode.")
            return
        self._finish_tour()
        self.app.exit_demo_mode()

    # -- connectivity ------------------------------------------------------

    def check_online(self) -> None:
        if self._ping is not None:
            return
        self._ping = worker.register(
            _PingThread(self.app.settings.api_base))
        self._ping.result.connect(self._on_ping_result)
        self._ping.start()

    def _on_ping_result(self, reachable: bool) -> None:
        # Wait for the thread before releasing it: destroying a QThread whose
        # thread is still unwinding aborts the whole process.
        worker.reap(self._ping)
        self._ping = None
        self.show_offline(not reachable)

    def show_offline(self, offline: bool) -> None:
        self.offline_banner.setVisible(offline)
        theme = self.app.current_theme()
        self.status_pill.setText("Offline" if offline else "Online")
        self.status_pill.set_color(theme.offline if offline else theme.online)

    def _set_theme(self, key: str) -> None:
        self.app.apply_theme(key)
        self._refresh_theme_actions()

    def _refresh_theme_actions(self) -> None:
        """Tick the View menu entry matching the stored preference."""
        current = self.app.settings.theme
        for key, action in self._theme_actions.items():
            action.setChecked(key == current)

    def apply_theme(self, theme) -> None:
        """Push the palette into every widget that paints its own colours.

        The generated stylesheet covers the standard widgets; these are the
        ones that set colours in code and would otherwise stay light.
        """
        self.offline_banner.apply_theme(theme)
        self.demo_banner.apply_theme(theme)
        self.status_pill.apply_theme(theme)
        self.drawer.apply_theme(theme)
        self.property_form.apply_theme(theme)
        self.photo_panel.apply_theme(theme)
        self.crm_tab.apply_theme(theme)
        self.chat_pane.apply_theme(theme)
        if getattr(self, "_tour", None) is not None:
            self._tour.apply_theme(theme)
        self._refresh_theme_actions()

    def status(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)
