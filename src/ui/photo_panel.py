"""Photo thumbnail grid with import and removal."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMessageBox,
                             QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ..services import image_service


class PhotoPanel(QWidget):
    photos_changed = pyqtSignal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.property_id: int | None = None
        self.paths: list[Path] = []

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Photos</b>"))
        import_btn = QPushButton("Add photos...")
        import_btn.clicked.connect(self.choose_photos)
        header.addWidget(import_btn)
        layout.addLayout(header)

        self.grid = QHBoxLayout()
        scroll = QScrollArea()
        container = QWidget()
        container.setLayout(self.grid)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(180)
        layout.addWidget(scroll)

    def load_property(self, property_id: int | None) -> None:
        self.property_id = property_id
        self.reload()

    def reload(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if self.property_id is None:
            self.paths = []
            return
        self.paths = image_service.property_photos(self.property_id)
        for path in self.paths:
            label = QLabel()
            thumb = image_service.thumbnail(path)
            label.setPixmap(QPixmap(str(thumb)).scaledToHeight(140))
            self.grid.addWidget(label)

    def choose_photos(self) -> None:
        if self.property_id is None:
            QMessageBox.information(self, "KeKar", "Save the property first.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "Choose property photos", "",
            "Images (*.jpg *.jpeg *.png *.webp)")
        if files:
            self.import_photos([Path(f) for f in files])

    def import_photos(self, paths: list[Path]) -> None:
        if self.property_id is None:
            return
        try:
            image_service.import_photos(self.property_id, paths)
        except Exception as exc:
            QMessageBox.warning(self, "KeKar",
                                f"Some photos could not be imported: {exc}")
        self.reload()
        self.photos_changed.emit()
