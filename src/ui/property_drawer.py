"""Scrollable property list with status color coding."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QVBoxLayout, QWidget)

from .widgets import StatusPill

VACANT_COLOR = "#2e7d32"
RENTED_COLOR = "#c62828"


class PropertyDrawer(QWidget):
    property_selected = pyqtSignal(int)
    add_requested = pyqtSignal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Properties</b>"))
        add_btn = QPushButton("+ Add New Property")
        add_btn.clicked.connect(self.add_requested.emit)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_click)
        layout.addWidget(self.list, 1)

    def count(self) -> int:
        return self.list.count()

    def reload(self) -> None:
        self.list.clear()
        for prop in self.app.property_repo.list():
            item = QListWidgetItem()
            item.setText(f"{prop.address}\n{prop.city or ''} {prop.zip_code or ''}".strip())
            item.setData(Qt.ItemDataRole.UserRole, prop.id)
            pill = StatusPill(prop.status,
                              VACANT_COLOR if prop.status == "Vacant" else RENTED_COLOR)
            self.list.addItem(item)
            self.list.setItemWidget(item, pill)

    def _on_click(self, item: QListWidgetItem) -> None:
        self.property_selected.emit(item.data(Qt.ItemDataRole.UserRole))
