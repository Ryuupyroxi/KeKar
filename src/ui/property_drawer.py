"""Property list: cover photo, address as the title, status shown by colour.

The earlier version put a "Vacant"/"Rented" badge where the address should be,
so the list said nothing about which property was which. Now each row is a
cover thumbnail plus the address, and the status is a coloured stripe on the
left edge — colour carries the meaning, text carries the identity.
"""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QPushButton,
                             QVBoxLayout, QWidget)

from ..data.models import Property
from ..services import image_service
from ..services.listing_compiler import AMENITY_LABELS
from .theme import font

VACANT_COLOR = "#2e7d32"
RENTED_COLOR = "#c62828"
COVER_SIZE = 56


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


def placeholder_cover(size: int = COVER_SIZE) -> QPixmap:
    """A simple house glyph for properties that have no photo yet."""
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
    return pm


def cover_pixmap(prop: Property, size: int = COVER_SIZE) -> QPixmap:
    """The property's cover photo, or a placeholder when it has none."""
    photos = image_service.property_photos(prop.id) if prop.id else []
    if photos:
        try:
            return QPixmap(str(image_service.thumbnail(photos[0]))).scaled(
                size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
    return placeholder_cover(size)


class PropertyItemWidget(QWidget):
    """One row in the property list."""

    def __init__(self, prop: Property, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        stripe = QFrame(self)
        stripe.setFixedWidth(5)
        stripe.setStyleSheet(
            f"background:{status_color(prop.status)}; border-radius:2px;")
        layout.addWidget(stripe)

        icon = QLabel(self)
        icon.setFixedSize(COVER_SIZE, COVER_SIZE)
        icon.setPixmap(cover_pixmap(prop))
        icon.setStyleSheet(
            "background:#f0ede8; border:1px solid #ddd8d0; border-radius:5px;")
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(2)
        address = QLabel(prop.address, self)
        address.setFont(font(11, bold=True))
        address.setStyleSheet("color:#2b2b28;")
        subtitle = QLabel(
            f"{prop.city or ''}, {prop.zip_code or ''}".strip(", "), self)
        subtitle.setFont(font(9))
        subtitle.setStyleSheet("color:#6b655c;")
        text.addWidget(address)
        text.addWidget(subtitle)
        layout.addLayout(text, 1)


class PropertyDrawer(QWidget):
    property_selected = pyqtSignal(int)
    add_requested = pyqtSignal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._props: list[Property] = []

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
        for prop in self._props:
            if needle and needle not in search_text(prop):
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, prop.id)
            item.setSizeHint(PropertyItemWidget(prop).sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, PropertyItemWidget(prop))

    def _on_click(self, item: QListWidgetItem) -> None:
        self.property_selected.emit(item.data(Qt.ItemDataRole.UserRole))
