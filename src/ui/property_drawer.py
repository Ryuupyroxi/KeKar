"""Property list: cover photo, address as the title, status shown by colour.

The earlier version put a "Vacant"/"Rented" badge where the address should be,
so the list said nothing about which property was which. Now each row is a
cover thumbnail plus the address, and the status is a coloured stripe on the
left edge — colour carries the meaning, text carries the identity.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import (QObject, QRunnable, QRect, QSize, QPoint, Qt,
                          QThreadPool, pyqtSignal)
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QPushButton,
                             QVBoxLayout, QWidget)

from ..data.models import Property
from ..services import image_service
from ..services.listing_compiler import AMENITY_LABELS
from .palette import Theme
from .theme import font

VACANT_COLOR = "#2e7d32"
RENTED_COLOR = "#c62828"
COVER_SIZE = 56

#: The palette the list is painting with. Set by PropertyDrawer.apply_theme;
#: the rows repaint from it, so they follow a theme change without being
#: rebuilt.
_current_theme: Theme | None = None


def status_color(status: str) -> str:
    """The light-theme status colours, kept as a stable helper for callers."""
    return VACANT_COLOR if status == "Vacant" else RENTED_COLOR


def _status_colour(status: str) -> str:
    theme = _current_theme
    if theme is not None:
        return theme.vacant if status == "Vacant" else theme.rented
    return status_color(status)

# One shared pool for thumbnail work. Generating a thumbnail means decoding a
# JPEG and resampling it; doing that for every row on the UI thread is what
# made a long property list stutter.
_THUMB_POOL = QThreadPool.globalInstance()
_THUMB_POOL.setMaxThreadCount(max(2, min(4, _THUMB_POOL.maxThreadCount())))


def status_color(status: str) -> str:
    return VACANT_COLOR if status == "Vacant" else RENTED_COLOR


def search_text(prop: Property) -> str:
    """Everything the search box should match against.

    Deliberately inclusive: address, city, ZIP, pet policy, free-form notes
    and every enabled amenity, so "dishwasher" or "fenced yard" finds the
    properties that have them.
    """
    parts = [prop.address, prop.city, prop.zip_code, prop.pet_policy,
             prop.notes or ""]
    parts.extend(label for attr, label in AMENITY_LABELS if getattr(prop, attr))
    return " ".join(part for part in parts if part).lower()


_PLACEHOLDER_CACHE: dict[int, QPixmap] = {}


def placeholder_cover(size: int = COVER_SIZE) -> QPixmap:
    """A simple house glyph for properties that have no photo yet.

    Cached per size: painting the glyph costs ~7 ms, and every row without a
    photo was repainting an identical image.
    """
    cached = _PLACEHOLDER_CACHE.get(size)
    if cached is not None:
        return cached
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor("#e8e2d6"))
    painter.setPen(QColor("#8a7f6d"))
    painter.drawRect(int(size * .22), int(size * .45),
                     int(size * .56), int(size * .38))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#7a4834"))
    painter.drawPolygon([
        QPoint(int(size * .15), int(size * .47)),
        QPoint(int(size * .50), int(size * .22)),
        QPoint(int(size * .85), int(size * .47)),
    ])
    painter.setBrush(QColor("#5a3a28"))
    painter.drawRect(int(size * .46), int(size * .60),
                     int(size * .09), int(size * .23))
    painter.end()
    _PLACEHOLDER_CACHE[size] = pm
    return pm


def cover_pixmap(prop: Property, size: int = COVER_SIZE) -> QPixmap:
    """The property's cover photo, or a placeholder when it has none.

    Synchronous on purpose: it only reads an already-generated thumbnail file.
    Generation happens in `_ThumbLoader` on the worker pool.
    """
    photos = image_service.property_photos(prop.id) if prop.id else []
    if photos:
        try:
            return QPixmap(str(image_service.thumbnail(photos[0]))).scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
    return placeholder_cover(size)


class _ThumbSignals(QObject):
    # Carries a Path, not a QPixmap: QPixmap is only valid on the GUI thread,
    # and the loader runs on a worker pool thread.
    ready = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        # Qt does not keep QRunnable objects alive. Holding them here stops a
        # worker's signal target from being garbage-collected mid-run.
        self.loaders: list[_ThumbLoader] = []


# One process-wide hub for thumbnail results. Module-level on purpose: it must
# outlive any individual drawer, because a worker can still be running when
# the widget that requested it is rebuilt or closed.
_THUMB_SIGNALS = _ThumbSignals()


class _ThumbLoader(QRunnable):
    """Generates one property's cover thumbnail off the UI thread.

    Only file work happens here (decode + resample + write the cached
    thumbnail). Building the QPixmap is left to the GUI thread in the
    drawer's slot, because Qt GUI objects must not be touched from a worker
    thread.
    """

    def __init__(self, signals: _ThumbSignals, property_id: int, path: Path,
                 size: int):
        super().__init__()
        self.signals = signals
        self.property_id = property_id
        self.path = path
        self.size = size

    def run(self) -> None:
        try:
            thumb = image_service.thumbnail(self.path, self.size)
        except Exception:
            thumb = None
        self.signals.ready.emit(self.property_id,
                                str(thumb) if thumb else "")


class PropertyItemWidget(QWidget):
    """One row in the property list.

    Paints itself rather than building a child widget per row. A child tree of
    five widgets with stylesheets and a nested layout cost ~10 ms per row,
    which put a 50-row list at ~500 ms; a single painted widget is ~1 ms.

    The cover is drawn as a placeholder immediately and replaced when the
    worker pool finishes decoding it.
    """

    def __init__(self, prop: Property, cover_path: Path | None = None,
                 parent=None):
        super().__init__(parent)
        self.property_id = prop.id
        self._cover_path = cover_path
        self._cover: QPixmap | None = None
        self._prop = prop
        self.setFixedHeight(COVER_SIZE + 12)

    def sizeHint(self):
        # No layout anymore, so the list needs an explicit hint.
        return QSize(300, COVER_SIZE + 12)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # status stripe
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(_status_colour(self._prop.status)))
        painter.drawRoundedRect(0, 6, 5, self.height() - 12, 2, 2)

        # cover
        cover_x = 14
        cover_y = 6
        theme = _current_theme
        cover_bg = theme.panel if theme is not None else "#f0ede8"
        cover_border = theme.border if theme is not None else "#ddd8d0"
        text_colour = theme.text if theme is not None else "#2b2b28"
        sub_colour = theme.text_secondary if theme is not None else "#6b655c"
        painter.setBrush(QColor(cover_bg))
        painter.setPen(QColor(cover_border))
        painter.drawRoundedRect(cover_x, cover_y, COVER_SIZE, COVER_SIZE, 5, 5)
        cover = self._cover
        if cover is None or cover.isNull():
            cover = placeholder_cover(COVER_SIZE)
        painter.drawPixmap(cover_x, cover_y, COVER_SIZE, COVER_SIZE, cover)

        # address + city/ZIP
        text_x = cover_x + COVER_SIZE + 12
        painter.setPen(QColor(text_colour))
        f = font(11, bold=True)
        painter.setFont(f)
        painter.drawText(QRect(text_x, 8, self.width() - text_x - 8, 20),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         self._prop.address)
        painter.setPen(QColor(sub_colour))
        f2 = font(9)
        painter.setFont(f2)
        subtitle = f"{self._prop.city or ''}, {self._prop.zip_code or ''}".strip(", ")
        painter.drawText(QRect(text_x, 30, self.width() - text_x - 8, 16),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         subtitle)
        painter.end()

    def paint_cover(self, thumb_path: str) -> None:
        """Show a finished thumbnail. Called on the GUI thread only."""
        pixmap = QPixmap(thumb_path)
        if pixmap.isNull():
            return
        self._cover = pixmap.scaled(
            COVER_SIZE, COVER_SIZE,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation)
        self.update()

    def start_loading(self) -> None:
        """Queue this row's thumbnail on the shared worker pool."""
        if self._cover_path is None:
            return
        loader = _ThumbLoader(_THUMB_SIGNALS, self.property_id,
                              self._cover_path, COVER_SIZE)
        _THUMB_SIGNALS.loaders.append(loader)
        _THUMB_POOL.start(loader)

    def mousePressEvent(self, event) -> None:
        # Rows are painted, so selection is reported by the list itself; this
        # only exists so the row shows the pointing-hand affordance.
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mousePressEvent(event)


class PropertyDrawer(QWidget):
    property_selected = pyqtSignal(int)
    add_requested = pyqtSignal()

    def apply_theme(self, theme: Theme) -> None:
        """Repaint the rows in the new palette.

        The rows paint themselves, so they cannot simply inherit a stylesheet —
        the palette is stored and the viewport is asked to repaint.
        """
        global _current_theme
        _current_theme = theme
        self.list.viewport().update()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._props: list[Property] = []
        _THUMB_SIGNALS.ready.connect(self._on_thumb_ready)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Properties</b>"))
        add_btn = QPushButton("+ Add New Property")
        add_btn.clicked.connect(self.add_requested.emit)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Search address or city...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter)

        self.list = QListWidget()
        self.list.setSpacing(2)
        self.list.itemClicked.connect(self._on_click)
        layout.addWidget(self.list, 1)

    def count(self) -> int:
        return self.list.count()

    def reload(self) -> None:
        self._props = self.app.property_repo.list()
        self._apply_filter()

    def _apply_filter(self) -> None:
        needle = self.filter.text().strip().lower()
        self.list.clear()

        # Resolve cover paths in one pass. Scanning each property's photo
        # directory inside the row widget meant 50 separate directory reads on
        # the UI thread, which is what made a full list take ~460 ms.
        visible = [p for p in self._props
                   if not needle or needle in search_text(p)]
        covers: dict[int, Path] = {}
        for prop in visible:
            if prop.id is None:
                continue
            photos = image_service.property_photos(prop.id)
            if photos:
                covers[prop.id] = photos[0]

        for prop in visible:
            widget = PropertyItemWidget(prop, covers.get(prop.id))
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, prop.id)
            item.setSizeHint(widget.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)
            widget.start_loading()

    def _on_thumb_ready(self, property_id: int, thumb_path: str) -> None:
        """Paint a finished thumbnail onto whichever row currently shows it.

        Rows are rebuilt on every reload, so the widget that requested a
        thumbnail may already be gone. Looking the row up by property id keeps
        a late result from painting onto a recycled row.
        """
        if not thumb_path:
            return
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) != property_id:
                continue
            widget = self.list.itemWidget(item)
            if isinstance(widget, PropertyItemWidget):
                widget.paint_cover(thumb_path)
            return

    def _on_click(self, item: QListWidgetItem) -> None:
        self.property_selected.emit(item.data(Qt.ItemDataRole.UserRole))
