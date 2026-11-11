"""Photo strip with import, cover selection and removal."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMessageBox,
                             QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ..services import image_service

SELECTED_BORDER = "border:2px solid #2e5e4e; border-radius:4px;"
PLAIN_BORDER = "border:2px solid transparent; border-radius:4px;"


class PhotoPanel(QWidget):
    photos_changed = pyqtSignal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.property_id: int | None = None
        self.paths: list[Path] = []
        self.selected: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Photos</b>"))
        self.add_btn = QPushButton("Add photos...")
        self.add_btn.clicked.connect(self.choose_photos)
        self.cover_btn = QPushButton("Set as cover")
        self.cover_btn.clicked.connect(self.set_cover)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_selected)
        for button in (self.add_btn, self.cover_btn, self.remove_btn):
            header.addWidget(button)
        header.addStretch(1)
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
        self.selected = None
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
            label.setProperty("photo_path", str(path))
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.setStyleSheet(PLAIN_BORDER)
            label.setPixmap(QPixmap(str(image_service.thumbnail(path)))
                           .scaledToHeight(150))
            label.mousePressEvent = lambda event, p=path: self._select(p)
            self.grid.addWidget(label)
        self.grid.addStretch(1)
        self._apply_selection()

    def _apply_selection(self) -> None:
        for index in range(self.grid.count()):
            widget = self.grid.itemAt(index).widget()
            if not isinstance(widget, QLabel):
                continue
            stored = widget.property("photo_path")
            widget.setStyleSheet(
                SELECTED_BORDER if stored and Path(stored) == self.selected
                else PLAIN_BORDER)

    def _select(self, path: Path) -> None:
        self.selected = path
        self._apply_selection()

    def set_cover(self) -> None:
        if self.property_id is None or self.selected is None:
            QMessageBox.information(self, "KeKar", "Choose a photo first.")
            return
        image_service.set_cover(self.property_id, self.selected)
        self.selected = None
        self.reload()
        self.photos_changed.emit()
        self.app.main_window.status("Cover photo updated.")

    def remove_selected(self) -> None:
        if self.property_id is None or self.selected is None:
            QMessageBox.information(self, "KeKar", "Choose a photo first.")
            return
        answer = QMessageBox.question(
            self, "KeKar", "Remove this photo?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        image_service.delete_photo(self.property_id, self.selected)
        self.selected = None
        self.reload()
        self.photos_changed.emit()
        self.app.main_window.status("Photo removed.")

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
