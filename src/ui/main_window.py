"""Main window: property drawer, detail/CRM tabs, chat pane, menu."""
from __future__ import annotations

import os
from functools import lru_cache

from PyQt6.QtCore import Qt, QThread, QTimer, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import (QColor, QIcon, QImage, QPainter, QPen, QPixmap,
                         QPolygon)
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton,
                             QScrollArea, QSplitter,
                             QSplitterHandle, QTabWidget, QToolButton,
                             QVBoxLayout, QWidget)

from .. import features
from .._version import APP_NAME, APP_VERSION, display_name
from ..paths import icon_path, logo_path
from ..services import connectivity
from .calendar_tab import CalendarTab
from .crm_tab import CrmTab
from .lease_tab import LeaseTab
from .photo_panel import PhotoPanel
from .property_drawer import PropertyDrawer
from .property_form import PropertyForm
from . import worker
from .settings_dialog import SettingsDialog
from .theme import font
from .users_dialog import UsersDialog
from .widgets import DemoBanner, OfflineBanner, StatusPill

PING_INTERVAL_MS = 30_000

#: Height of the logo in the window header and the About dialog.
LOGO_HEIGHT = 44
#: The header shows the wordmark at its current visible size (the source's
#: opaque 909x314 area rendered at ~40 px) with the surrounding transparent
#: canvas trimmed away. Scaling the whole 1408x768 file to 96 px left a 96 px
#: header around a 40 px mark — dead space, not a bigger logo.
HEADER_LOGO_HEIGHT = 40


@lru_cache(maxsize=4)
def _opaque_bbox(path: str) -> QRect | None:
    """Find the non-transparent rectangle of a PNG, once per process.

    The shipped wordmark is a 1408x768 canvas holding a 909x314 mark; most of
    the file is empty alpha. Scanning the alpha channel in C-level byte chunks
    keeps this cheap, and the cache means every later window reuses it.
    """
    image = QImage(path)
    if image.isNull():
        return None
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    bits = image.constBits()
    bits.setsize(image.sizeInBytes())
    alpha = memoryview(bits)[3::4]
    width, height = image.width(), image.height()
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        row = bytes(alpha[y * width:(y + 1) * width]).rstrip(b"\x00")
        if not row:
            continue
        first = width - len(row)
        last = first + len(row.lstrip(b"\x00")) - 1
        min_x = min(min_x, first)
        max_x = max(max_x, last)
        min_y = min(min_y, y)
        max_y = y
    if max_x < 0:
        return None
    return QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def _set_logo(label: QLabel, height: int = LOGO_HEIGHT,
              trim: bool = False) -> None:
    """Scale the shipped logo onto a QLabel, keeping its proportions.

    The logo has an alpha channel, so it composites onto whatever theme is
    active. ``trim`` drops the empty canvas around the wordmark so the strip
    fits the visible art rather than the source file's padding. A missing or
    unreadable file leaves the label empty rather than raising — a missing
    logo must not stop the window from opening.
    """
    label.setFixedHeight(height)
    path = logo_path()
    if not path.exists():
        return
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return
    if trim:
        bbox = _opaque_bbox(str(path))
        if bbox is not None and bbox.isValid():
            pixmap = pixmap.copy(bbox)
    label.setPixmap(pixmap.scaledToHeight(
        height, Qt.TransformationMode.SmoothTransformation))


class _PaneHandle(QSplitterHandle):
    """A splitter handle that just draws a grip.

    It paints only. QSplitter owns the handle's press, move and release, and
    overriding any of those breaks drag-to-resize; collapsing is driven by the
    panel toggles in the menu bar instead.
    """

    def __init__(self, app, splitter):
        super().__init__(splitter.orientation(), splitter)
        self._app = app

    def paintEvent(self, event) -> None:
        """Draw a grip so the boundary reads as draggable.

        Deliberately no mouse handling: QSplitter owns the handle's press,
        move and release, and overriding any of them breaks drag-to-resize.
        Collapsing is driven by the panel toggles in the menu bar instead.
        """
        theme = self._app.current_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(theme.window))
        painter.setPen(QPen(QColor(theme.text_secondary), 2))
        cx, cy = self.rect().center().x(), self.rect().center().y()
        if self.orientation() == Qt.Orientation.Horizontal:
            points = QPolygon([QPoint(cx - 2, cy - 5), QPoint(cx - 2, cy + 5),
                               QPoint(cx + 4, cy)])
        else:
            points = QPolygon([QPoint(cx - 5, cy - 2), QPoint(cx + 5, cy - 2),
                               QPoint(cx, cy + 4)])
        painter.drawPolygon(points)
        painter.end()


class CollapsibleSplitter(QSplitter):
    """A QSplitter whose panes can be collapsed to zero and brought back.

    The expanded sizes are remembered per pane, so collapsing and restoring
    returns the layout the user had rather than an arbitrary split.
    """

    def __init__(self, app, orientation, parent=None):
        super().__init__(orientation, parent)
        self._app = app
        self._expanded: dict[int, list[int]] = {}
        self.setHandleWidth(14)

    def createHandle(self):
        return _PaneHandle(self._app, self)

    def toggle_pane(self, index: int) -> None:
        sizes = list(self.sizes())
        if index < 0 or index >= len(sizes):
            return
        widget = self.widget(index)
        # Qt's own collapsible handling would collapse on press and swallow
        # drag-to-resize, so the pane is collapsed manually: relaxing the
        # minimum size lets setSizes() take the pane to zero.
        widget.setMinimumSize(0, 0)
        if sizes[index] == 0:
            restored = self._expanded.get(index)
            if not restored or len(restored) != len(sizes):
                total = sum(sizes) or 1
                restored = [total // len(sizes)] * len(sizes)
            self.setSizes(restored)
            self._expanded.pop(index, None)
        else:
            # Copy: `sizes` is about to be mutated, and storing the same list
            # would leave the remembered layout with a zero in it.
            self._expanded[index] = list(sizes)
            sizes[index] = 0
            self.setSizes(sizes)

    def is_collapsed(self, index: int) -> bool:
        return self.sizes()[index] == 0

    def collapse(self, index: int, collapsed: bool = True) -> None:
        if collapsed == self.is_collapsed(index):
            return
        self.toggle_pane(index)


class _PingThread(QThread):
    """Checks provider reachability without blocking the UI."""

    result = pyqtSignal(bool)

    def __init__(self, api_base: str):
        super().__init__()
        self.api_base = api_base

    def run(self) -> None:
        self.result.emit(connectivity.provider_reachable(self.api_base))


class _HelpLogo(QLabel):
    """The header wordmark doubles as a shortcut to the Help menu."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Open Help")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._window._open_help_menu()
        super().mousePressEvent(event)


class AboutDialog(QDialog):
    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle(f"About {display_name()}")
        self.setWindowIcon(QIcon(str(icon_path())))
        self.resize(460, 340)
        layout = QVBoxLayout(self)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_logo(self.logo_label, height=96)
        layout.addWidget(self.logo_label)

        body = QLabel(
            f"<h2>{display_name()} {APP_VERSION}</h2>"
            f"<p>A portable rental property manager.</p>"
            f"<p>Your properties, photos and applicant notes live in the "
            f"KeKarData folder next to the program. "
            + ("Nothing ever leaves this drive.</p>"
               if not features.chat_enabled() else
               "Nothing leaves this drive except the questions you choose "
               "to send to the assistant.</p>")
            + f"<p>Data is stored locally in SQLite and backed up automatically."
            f"</p>")
        # Rich-text labels do not wrap unless told to, and the paragraph was
        # running off the right edge of the dialog.
        body.setWordWrap(True)
        layout.addWidget(body)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        # A fixed height clipped the last paragraph at the dialog's bottom
        # edge. Size the dialog to the word-wrapped body's real need instead,
        # so a larger system font grows the window rather than cutting text.
        layout.activate()
        self.setMinimumSize(460, 0)
        self.resize(460, max(340, layout.totalSizeHint().height()))


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.demo_mode = False
        self.setWindowTitle(f"{display_name()} Property Manager")
        # The taskbar, the start menu and the title bar all read this.
        self.setWindowIcon(QIcon(str(icon_path())))
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
        # Set when the window is locked: the real central widget is parked
        # here so unlocking can put it back.
        self._real_central: QWidget | None = None
        self._lock_panel: QWidget | None = None

        central = QWidget()
        outer = QVBoxLayout(central)
        # A gutter around the cards: without it the panel borders sit flush
        # against the window edge and the regions stop reading as cards.
        outer.setContentsMargins(8, 4, 8, 8)
        self.logo_label = _HelpLogo(self)
        # Centred, with the source's empty canvas trimmed: the strip is now
        # as tall as the visible wordmark, not as tall as the PNG file.
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_logo(self.logo_label, height=HEADER_LOGO_HEIGHT, trim=True)
        outer.addWidget(self.logo_label)
        outer.addWidget(self.offline_banner)
        outer.addWidget(self.demo_banner)

        self.main_splitter = CollapsibleSplitter(app, Qt.Orientation.Vertical)

        self.top_splitter = CollapsibleSplitter(app, Qt.Orientation.Horizontal)
        self.drawer = PropertyDrawer(app)
        self.drawer.setProperty("panel", True)
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
        self.form_scroll = form_scroll
        pv.addWidget(form_scroll, 1)
        pv.addWidget(self.photo_panel)
        self.tabs.addTab(properties_tab, "Properties")
        self.crm_tab = CrmTab(app)
        self.tabs.addTab(self.crm_tab, "Applicants")
        self.lease_tab = LeaseTab(app)
        self.tabs.addTab(self.lease_tab, "Leases")
        self.calendar_tab = CalendarTab(app)
        self.tabs.addTab(self.calendar_tab, "Calendar")
        # Kept as an alias: client code and the tour still refer to stays_tab,
        # but the stays UI now lives inside the Calendar tab.
        self.stays_tab = self.calendar_tab.stays

        # The tab area is a card too, so the right-hand region is outlined
        # like the drawer and the chat pane. The card carries the padding;
        # QTabWidget's own pane border is switched off by the stylesheet so
        # the region does not draw two nested outlines.
        self.tabs_card = QWidget()
        self.tabs_card.setProperty("panel", True)
        self.tabs_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tabs_layout = QVBoxLayout(self.tabs_card)
        tabs_layout.setContentsMargins(10, 8, 10, 10)
        tabs_layout.setSpacing(0)
        tabs_layout.addWidget(self.tabs)

        self.top_splitter.addWidget(self.drawer)
        self.top_splitter.addWidget(self.tabs_card)
        self.top_splitter.setSizes([340, 900])
        self.main_splitter.addWidget(self.top_splitter)
        if features.chat_enabled():
            from .chat_pane import ChatPane
            self.chat_pane = ChatPane(app)
            self.chat_pane.setProperty("panel", True)
            self.main_splitter.addWidget(self.chat_pane)
            self.main_splitter.setSizes([560, 200])
        else:
            self.chat_pane = None

        outer.addWidget(self.main_splitter, 1)
        self.setCentralWidget(central)

        # wiring
        self.drawer.property_selected.connect(self._on_property_selected)
        self.drawer.add_requested.connect(self._new_property)
        self.property_form.property_saved.connect(self._on_property_saved)
        self.property_form.status_changed.connect(self._on_status_changed)
        self.property_form.property_deleted.connect(self._on_property_deleted)
        self.photo_panel.photos_changed.connect(self.drawer.reload)
        self.drawer.reload()
        self.crm_tab.reload()
        self.lease_tab.reload()
        if self.chat_pane is not None:
            self.chat_pane.load_history()

        # Offline detection exists only in the full build: Lite has no remote
        # service to reach, so it starts no timer and shows no network pill.
        self._ping: _PingThread | None = None
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(PING_INTERVAL_MS)
        self._ping_timer.timeout.connect(self.check_online)
        if features.chat_enabled() and not os.environ.get("KEKAR_TESTING"):
            self._ping_timer.start()
            self.check_online()
        else:
            self.offline_banner.hide()
            self.status_pill.hide()

        # Menu first: its panel toggles read the splitter state, and the
        # layout restore below updates their labels.
        self._build_menu()
        self._restore_layout()

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        self.settings_action = file_menu.addAction("Settings...")
        self.settings_action.triggered.connect(self._open_settings)
        accounts_action = file_menu.addAction("Accounts…")
        accounts_action.triggered.connect(self._open_accounts)
        self.lock_action = file_menu.addAction("Lock session")
        self.lock_action.triggered.connect(self._lock_session)
        self.lock_action.setVisible(False)
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

        view_menu.addSeparator()
        self.sidebar_action = view_menu.addAction("Collapse property list")
        self.sidebar_action.triggered.connect(self._toggle_sidebar)
        self.chat_action = view_menu.addAction("Collapse chat")
        self.chat_action.triggered.connect(self._toggle_chat)
        self.chat_action.setVisible(self.chat_pane is not None)

        self._build_panel_toggles(menubar)

        help_menu = menubar.addMenu("&Help")
        self.help_menu = help_menu
        tour_action = help_menu.addAction("Guided tour...")
        tour_action.triggered.connect(self._start_tour)
        self.exit_demo_action = help_menu.addAction("Exit demo mode")
        self.exit_demo_action.triggered.connect(self._exit_demo_mode)
        self.exit_demo_action.setVisible(False)
        help_menu.addAction("Calendar legend...").triggered.connect(
            self._show_calendar_legend)
        help_menu.addSeparator()
        about_action = help_menu.addAction("About...")
        about_action.triggered.connect(lambda: AboutDialog(self.app, self).exec())

    def _show_calendar_legend(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Calendar legend",
            "Green: property move-in date\n"
            "Red: property move-out date\n"
            "Purple: a short-stay reservation\n\n"
            "Short stays are managed in the 'Short stays' panel of this tab.")

    def _open_help_menu(self) -> None:
        """Pop the Help menu under the wordmark when it is clicked."""
        point = self.logo_label.mapToGlobal(
            QPoint(0, self.logo_label.height()))
        self.help_menu.popup(point)

    def _open_settings(self) -> None:
        SettingsDialog(self.app, self).exec()

    # -- property wiring ---------------------------------------------------

    def _on_property_selected(self, property_id: int) -> None:
        self.property_form.load_property(property_id)
        self.photo_panel.load_property(property_id)
        self.calendar_tab.set_selected_property(property_id)

    def _new_property(self) -> None:
        """Start a blank property.

        The form is taller than its viewport, so a click that only cleared the
        fields read as "nothing happened" whenever the view was scrolled past
        the top: both the pill and the address field were off-screen. Bring the
        Properties tab, the top of the form and the status bar into play so the
        action is visible every time.
        """
        self.tabs.setCurrentIndex(0)
        self.property_form.load_property(None)
        self.photo_panel.load_property(None)
        self.property_form.address_input.setFocus()
        self.form_scroll.verticalScrollBar().setValue(0)
        self.status("New property — fill in the details, then press Save.")

    def _on_property_saved(self, property_id: int) -> None:
        self.drawer.reload()
        self.crm_tab.reload()
        self.lease_tab.reload()
        self.calendar_tab.reload()
        self.photo_panel.load_property(property_id)
        prop = self.app.property_repo.get(property_id)
        self.status(f"Saved {prop.address if prop else property_id}")

    def _on_property_deleted(self) -> None:
        self.drawer.reload()
        self.crm_tab.reload()
        self.lease_tab.reload()
        self.calendar_tab.reload()
        self.photo_panel.load_property(None)
        self.status("Property deleted.")

    def _on_status_changed(self, property_id: int, status: str) -> None:
        self.drawer.reload()
        self.status(f"Marked as {status}.")

    def reload_all(self) -> None:
        """Refresh every view — used after a backup restore."""
        self.drawer.reload()
        self.crm_tab.reload()
        self.lease_tab.reload()
        self.stays_tab.reload()
        self.calendar_tab.reload()
        current = self.property_form.current_id
        if current is None:
            return
        if self.app.property_repo.get(current) is None:
            self.property_form.load_property(None)
            self.photo_panel.load_property(None)
        else:
            self.property_form.load_property(current)
            self.photo_panel.load_property(current)

    # -- locking -----------------------------------------------------------

    def is_locked(self) -> bool:
        """True while the login panel is covering the portfolio."""
        return self._lock_panel is not None and \
            self.centralWidget() is self._lock_panel

    def set_locked(self, locked: bool) -> None:
        """Hide the portfolio behind the login panel.

        The central widget is swapped rather than the contents disabled, so a
        locked window shows nothing of the portfolio at all.
        """
        if locked:
            if self._real_central is None:
                self._real_central = self.centralWidget()
            if self._lock_panel is None:
                self._lock_panel = self._build_lock_panel()
            self.setCentralWidget(self._lock_panel)
            self._lock_panel.show()
        elif self._real_central is not None:
            self.setCentralWidget(self._real_central)
            # Qt hides a central widget when it is swapped out and does not
            # unhide it when it is swapped back, so the restored portfolio
            # would stay invisible with no error anywhere.
            self._real_central.show()
        self.lock_action.setVisible(not locked)
        self._refresh_theme_actions()

    def _build_lock_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addStretch(1)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _set_logo(logo, height=72)
        layout.addWidget(logo)
        title = QLabel(f"{APP_NAME} is locked")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(font(16, bold=True))
        layout.addWidget(title)
        hint = QLabel("Log in to see your properties, leases and applicants.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        button = QPushButton("Log in")
        button.clicked.connect(self._unlock)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        return panel

    def _unlock(self) -> None:
        self.app.unlock_with_dialog()

    def _open_accounts(self) -> None:
        UsersDialog(self.app, self).exec()

    def _lock_session(self) -> None:
        self.app.lock()

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
        return self.chat_pane is not None and self.chat_pane._thread is not None

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

    # -- collapsible panels ------------------------------------------------

    def _toggle_sidebar(self) -> None:
        self.top_splitter.toggle_pane(0)
        self._remember_layout()

    def _toggle_chat(self) -> None:
        if self.chat_pane is None:
            return
        self.main_splitter.toggle_pane(1)
        self._remember_layout()

    def _remember_layout(self) -> None:
        self.app.settings.sidebar_collapsed = self.top_splitter.is_collapsed(0)
        self.app.settings.chat_collapsed = (self.main_splitter.is_collapsed(1)
                                            if self.chat_pane is not None
                                            else False)
        try:
            self.app.settings.save()
        except Exception:
            pass
        self._refresh_panel_actions()

    def _build_panel_toggles(self, menubar) -> None:
        """Two always-visible buttons collapsing the property list and chat.

        They live in the menu bar's corner rather than on the splitter handle:
        QSplitter owns the handle's mouse events (overriding them breaks
        drag-to-resize), and a pane collapsed to zero would hide any button
        placed inside it.
        """
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(6, 3, 8, 3)
        layout.setSpacing(4)

        self.sidebar_toggle = QToolButton(holder)
        self.sidebar_toggle.clicked.connect(self._toggle_sidebar)

        self.chat_toggle = QToolButton(holder)
        self.chat_toggle.clicked.connect(self._toggle_chat)
        self.chat_toggle.setVisible(self.chat_pane is not None)

        # These are the only always-reachable collapse controls, so they are
        # sized as real targets rather than menu-bar crumbs.
        for button in (self.sidebar_toggle, self.chat_toggle):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(32)
            button.setFont(font(10, bold=True))
            button.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        layout.addWidget(self.sidebar_toggle)
        layout.addWidget(self.chat_toggle)
        menubar.setCornerWidget(holder)
        self._refresh_panel_actions()

    def _refresh_panel_actions(self) -> None:
        sidebar_collapsed = self.top_splitter.is_collapsed(0)
        chat_collapsed = (self.main_splitter.is_collapsed(1)
                          if self.chat_pane is not None else False)

        self.sidebar_action.setText(
            "Expand property list" if sidebar_collapsed
            else "Collapse property list")
        self.chat_action.setText(
            "Expand chat" if chat_collapsed else "Collapse chat")
        # The arrows point the way the panel will move. The Lite build has no
        # chat pane, but its property toggle still needs a visible label.
        if hasattr(self, "sidebar_toggle"):
            self.sidebar_toggle.setText("▶ Properties" if sidebar_collapsed
                                        else "◀ Properties")
            self.sidebar_toggle.setToolTip(
                "Expand the property list" if sidebar_collapsed
                else "Collapse the property list")
        if self.chat_pane is None:
            return
        if hasattr(self, "chat_toggle"):
            self.chat_toggle.setText("▲ Chat" if chat_collapsed else "▼ Chat")
            self.chat_toggle.setToolTip(
                "Expand the chat" if chat_collapsed else "Collapse the chat")

    def _restore_layout(self) -> None:
        """Put back the panel layout the user left behind."""
        if self.app.settings.sidebar_collapsed:
            self.top_splitter.collapse(0, True)
        if self.chat_pane is not None and self.app.settings.chat_collapsed:
            self.main_splitter.collapse(1, True)
        self._refresh_panel_actions()

    def apply_theme(self, theme) -> None:
        """Push the palette into every widget that paints its own colours.

        The generated stylesheet covers the standard widgets; these are the
        ones that set colours in code and would otherwise stay light.
        """
        self.offline_banner.apply_theme(theme)
        self.demo_banner.apply_theme(theme)
        self.status_pill.apply_theme(theme)
        if self.chat_pane is not None:
            # StatusPill.apply_theme cannot know whether we are offline; the
            # main window can, so re-assert the meaning after recolouring.
            self.show_offline(not self.offline_banner.isHidden())
        self.drawer.apply_theme(theme)
        self.property_form.apply_theme(theme)
        self.photo_panel.apply_theme(theme)
        self.crm_tab.apply_theme(theme)
        self.lease_tab.apply_theme(theme)
        self.stays_tab.apply_theme(theme)
        if self.chat_pane is not None:
            self.chat_pane.apply_theme(theme)
        if getattr(self, "_tour", None) is not None:
            self._tour.apply_theme(theme)
        for splitter in (self.top_splitter, self.main_splitter):
            for i in range(splitter.count()):
                splitter.handle(i).update()
        self._refresh_theme_actions()

    def status(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)
