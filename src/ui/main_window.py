"""Main window: property drawer, detail/CRM tabs, chat pane, menu."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QMainWindow,
                             QScrollArea, QSplitter, QTabWidget, QVBoxLayout,
                             QWidget)

from .._version import APP_NAME, APP_VERSION
from ..services import connectivity
from .chat_pane import ChatPane
from .crm_tab import CrmTab
from .photo_panel import PhotoPanel
from .property_drawer import PropertyDrawer
from .property_form import PropertyForm
from . import worker
from .settings_dialog import SettingsDialog
from .widgets import OfflineBanner, StatusPill

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
        self.setWindowTitle(f"{APP_NAME} Property Manager")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 720)

        self.offline_banner = OfflineBanner(self)
        self.offline_banner.hide()
        self.status_pill = StatusPill("Online", "#2e7d32", self)
        self.statusBar().addPermanentWidget(self.status_pill)

        self._build_menu()

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.offline_banner)

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
        settings_action = file_menu.addAction("Settings...")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu("&Help")
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
        self.status_pill.setText("Offline" if offline else "Online")
        self.status_pill.set_color("#f9a825" if offline else "#2e7d32")

    def status(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)
