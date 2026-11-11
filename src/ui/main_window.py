"""Main window: property drawer, detail/CRM tabs, chat pane, menu."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QMainWindow, QSplitter, QTabWidget, QVBoxLayout,
                             QWidget)

from .chat_pane import ChatPane
from .crm_tab import CrmTab
from .photo_panel import PhotoPanel
from .property_drawer import PropertyDrawer
from .property_form import PropertyForm
from .settings_dialog import SettingsDialog
from .widgets import OfflineBanner, StatusPill


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("KeKar Property Manager")
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
        pv.addWidget(self.property_form)
        pv.addWidget(self.photo_panel)
        self.tabs.addTab(properties_tab, "Properties")
        self.crm_tab = CrmTab(app)
        self.tabs.addTab(self.crm_tab, "Applicants")

        top.addWidget(self.drawer)
        top.addWidget(self.tabs)
        top.setSizes([320, 900])
        main_splitter.addWidget(top)
        self.chat_pane = ChatPane(app)
        main_splitter.addWidget(self.chat_pane)
        main_splitter.setSizes([520, 220])

        outer.addWidget(main_splitter, 1)
        self.setCentralWidget(central)

        # wiring
        self.drawer.property_selected.connect(self._on_property_selected)
        self.drawer.add_requested.connect(self._new_property)
        self.property_form.property_saved.connect(self._on_property_saved)
        self.property_form.status_changed.connect(self._on_status_changed)
        self.drawer.reload()

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        settings_action = file_menu.addAction("Settings...")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

    def _open_settings(self) -> None:
        SettingsDialog(self.app, self).exec()

    def _on_property_selected(self, property_id: int) -> None:
        self.property_form.load_property(property_id)
        self.photo_panel.load_property(property_id)

    def _new_property(self) -> None:
        self.property_form.load_property(None)
        self.photo_panel.load_property(None)
        self.property_form.address_input.setFocus()

    def _on_property_saved(self, property_id: int) -> None:
        self.drawer.reload()
        self.photo_panel.load_property(property_id)
        self.status(f"Saved {self.app.property_repo.get(property_id).address}")

    def _on_status_changed(self, property_id: int, status: str) -> None:
        self.drawer.reload()
        self.status(f"Marked as {status}.")

    def show_offline(self, offline: bool) -> None:
        self.offline_banner.setVisible(offline)
        self.status_pill.setText("Offline" if offline else "Online")
        self.status_pill.set_color("#f9a825" if offline else "#2e7d32")

    def status(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)
