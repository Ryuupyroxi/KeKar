"""Editable property detail form with amenity toggles and quick actions."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
                             QWidget)

from ..data.models import Property
from ..services import image_service
from ..services.listing_compiler import (AMENITY_LABELS as AMENITY_FIELDS,
                                         compile_listing, validate_listing)
from .listing_dialog import ListingDialog
from .palette import Theme
from .theme import font
from .widgets import StatusPill


class PropertyForm(QWidget):
    property_saved = pyqtSignal(int)
    status_changed = pyqtSignal(int, str)
    property_deleted = pyqtSignal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.current_id: int | None = None
        self._theme: Theme | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # --- header row: status + delete --------------------------------
        header = QHBoxLayout()
        self.pill = StatusPill("No property selected", "#616161", self)
        header.addWidget(self.pill)
        header.addStretch(1)
        delete_btn = QPushButton("Delete property")
        delete_btn.setObjectName("delete_property")
        delete_btn.clicked.connect(self.delete_property)
        header.addWidget(delete_btn)
        layout.addLayout(header)

        # --- details in two columns -------------------------------------
        details = QGroupBox("Details", self)
        grid = QGridLayout(details)
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(14)

        self.address_input = QLineEdit()
        self.city_input = QLineEdit()
        self.zip_input = QLineEdit()
        self.rent_input = QDoubleSpinBox()
        self.rent_input.setRange(0, 100000)
        self.rent_input.setPrefix("$")
        self.rent_input.setSingleStep(25)
        self.deposit_input = QDoubleSpinBox()
        self.deposit_input.setRange(0, 100000)
        self.deposit_input.setPrefix("$")
        self.deposit_input.setSingleStep(25)
        self.available_input = QLineEdit()
        self.available_input.setPlaceholderText("2026-12-01")
        self.bedrooms_input = QSpinBox()
        self.bedrooms_input.setRange(0, 20)
        self.bathrooms_input = QDoubleSpinBox()
        self.bathrooms_input.setRange(0, 20)
        self.bathrooms_input.setSingleStep(0.5)
        self.sqft_input = QSpinBox()
        self.sqft_input.setRange(0, 100000)
        self.sqft_input.setSingleStep(50)
        self.pet_input = QLineEdit()
        self.pet_input.setPlaceholderText("Cats OK")

        fields = [
            ("Street address", self.address_input),
            ("City", self.city_input),
            ("ZIP", self.zip_input),
            ("Monthly rent", self.rent_input),
            ("Security deposit", self.deposit_input),
            ("Available date", self.available_input),
            ("Bedrooms", self.bedrooms_input),
            ("Bathrooms", self.bathrooms_input),
            ("Square feet", self.sqft_input),
            ("Pet policy", self.pet_input),
        ]
        for index, (label, widget) in enumerate(fields):
            row, column = divmod(index, 2)
            grid.addWidget(_form_label(label), row, column * 2)
            grid.addWidget(widget, row, column * 2 + 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout.addWidget(details)

        # --- amenities ---------------------------------------------------
        amenities_box = QGroupBox("Amenities", self)
        amenities_layout = QHBoxLayout(amenities_box)
        self.amenity_boxes: dict[str, QCheckBox] = {}
        for attr, label in AMENITY_FIELDS:
            box = QCheckBox(label)
            self.amenity_boxes[attr] = box
            amenities_layout.addWidget(box)
        amenities_layout.addStretch(1)
        layout.addWidget(amenities_box)

        # --- notes -------------------------------------------------------
        notes_box = QGroupBox("Notes", self)
        notes_layout = QVBoxLayout(notes_box)
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(70)
        self.notes_input.setPlaceholderText(
            "Anything a prospective tenant should know.")
        notes_layout.addWidget(self.notes_input)
        layout.addWidget(notes_box)

        # --- actions -----------------------------------------------------
        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save)
        self.preview_btn = QPushButton("Preview listing")
        self.preview_btn.clicked.connect(self.preview_listing)
        self.copy_btn = QPushButton("Copy listing")
        self.copy_btn.clicked.connect(self.copy_listing)
        self.rented_btn = QPushButton("Mark as rented")
        self.rented_btn.clicked.connect(lambda: self._set_status("Rented"))
        self.vacant_btn = QPushButton("Mark as vacant")
        self.vacant_btn.clicked.connect(lambda: self._set_status("Vacant"))
        self.publish_btn = QPushButton("Publish to Marketplace...")
        self.publish_btn.clicked.connect(self.publish_to_marketplace)
        for btn in (self.save_btn, self.preview_btn, self.copy_btn,
                    self.publish_btn, self.rented_btn, self.vacant_btn):
            actions.addWidget(btn)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

    # -- loading and saving ------------------------------------------------

    def _status_colour(self, status: str) -> str:
        theme = self._theme
        if theme is None:
            return "#2e7d32" if status == "Vacant" else "#c62828"
        return theme.vacant if status == "Vacant" else theme.rented

    def _neutral_colour(self) -> str:
        return self._theme.neutral if self._theme is not None else "#616161"

    def apply_theme(self, theme: Theme) -> None:
        self._theme = theme
        current = self.app.property_repo.get(self.current_id) \
            if self.current_id is not None else None
        if current is None:
            self.pill.set_color(self._neutral_colour())
        else:
            self.pill.set_color(self._status_colour(current.status))
        self._restyle_labels()

    def _restyle_labels(self) -> None:
        colour = self._theme.text_secondary if self._theme is not None \
            else "#4a453e"
        for label in self.findChildren(QLabel):
            if label.property("muted") is True:
                label.setStyleSheet(f"color:{colour};")

    def load_property(self, property_id: int | None) -> None:
        self.current_id = property_id
        if property_id is None:
            self._clear_fields()
            self.pill.setText("New property")
            self.pill.set_color(self._neutral_colour())
            return
        prop = self.app.property_repo.get(property_id)
        if prop is None:
            return
        self._fill_fields(prop)
        self.pill.setText(prop.status)
        self.pill.set_color(self._status_colour(prop.status))

    def _clear_fields(self) -> None:
        for widget in (self.address_input, self.city_input, self.zip_input,
                       self.available_input, self.pet_input):
            widget.clear()
        self.notes_input.clear()
        for widget in (self.rent_input, self.deposit_input,
                       self.bedrooms_input, self.bathrooms_input,
                       self.sqft_input):
            widget.setValue(0)
        for box in self.amenity_boxes.values():
            box.setChecked(False)

    def _fill_fields(self, p: Property) -> None:
        self.address_input.setText(p.address or "")
        self.city_input.setText(p.city or "")
        self.zip_input.setText(p.zip_code or "")
        self.rent_input.setValue(p.rent_price or 0)
        self.deposit_input.setValue(p.deposit_amount or 0)
        self.available_input.setText(p.available_date or "")
        self.bedrooms_input.setValue(p.bedrooms or 0)
        self.bathrooms_input.setValue(p.bathrooms or 0)
        self.sqft_input.setValue(p.sqft or 0)
        self.pet_input.setText(p.pet_policy or "")
        self.notes_input.setPlainText(p.notes or "")
        for attr, box in self.amenity_boxes.items():
            box.setChecked(bool(getattr(p, attr)))

    def _collect(self) -> Property:
        return Property(
            id=self.current_id,
            address=self.address_input.text().strip(),
            city=self.city_input.text().strip() or None,
            zip_code=self.zip_input.text().strip() or None,
            rent_price=self.rent_input.value() or None,
            deposit_amount=self.deposit_input.value() or None,
            available_date=self.available_input.text().strip() or None,
            bedrooms=self.bedrooms_input.value() or None,
            bathrooms=self.bathrooms_input.value() or None,
            sqft=self.sqft_input.value() or None,
            pet_policy=self.pet_input.text().strip() or None,
            notes=self.notes_input.toPlainText().strip() or None,
            status=self.pill.text() if self.pill.text() in ("Vacant", "Rented")
            else "Vacant",
            **{attr: box.isChecked() for attr, box in self.amenity_boxes.items()},
        )

    def save(self) -> None:
        prop = self._collect()
        if not prop.address:
            QMessageBox.warning(self, "KeKar", "A street address is required.")
            return
        if prop.id is None:
            prop.status = "Vacant"
            self.current_id = self.app.property_repo.create(prop)
        else:
            self.app.property_repo.update(prop)
        self.pill.setText(prop.status)
        self.pill.set_color(self._status_colour(prop.status))
        self.property_saved.emit(self.current_id)
        self.app.main_window.status(f"Saved {prop.address}")

    def delete_property(self) -> None:
        if self.current_id is None:
            QMessageBox.information(self, "KeKar", "Choose a saved property first.")
            return
        prop = self.app.property_repo.get(self.current_id)
        if prop is None:
            return
        answer = QMessageBox.question(
            self, "KeKar",
            f"Delete {prop.address}?\n\nThis also removes its photos and cannot "
            f"be undone. A backup is kept in KeKarData/backups.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        image_service.delete_property_photos(self.current_id)
        self.app.property_repo.delete(self.current_id)
        self.current_id = None
        self._clear_fields()
        self.pill.setText("No property selected")
        self.pill.set_color(self._neutral_colour())
        self.property_deleted.emit()

    # -- listing -----------------------------------------------------------

    def _require_saved(self) -> Property | None:
        if self.current_id is None:
            QMessageBox.information(self, "KeKar",
                                    "Choose or save a property first.")
            return None
        prop = self.app.property_repo.get(self.current_id)
        if prop is None:
            return None
        problems = validate_listing(compile_listing(prop))
        if problems:
            QMessageBox.warning(
                self, "KeKar", "This listing is missing some details:\n- "
                + "\n- ".join(problems))
        return prop

    def preview_listing(self) -> None:
        prop = self._require_saved()
        if prop is None:
            return
        ListingDialog(self.app, prop, self).exec()

    def copy_listing(self) -> None:
        prop = self._require_saved()
        if prop is None:
            return
        from ..services.clipboard import copy_listing
        copy_listing(prop)
        self.app.main_window.status("Listing copied — paste it anywhere.")

    def publish_to_marketplace(self) -> None:
        prop = self._require_saved()
        if prop is None:
            return
        from .marketplace_dialog import MarketplaceDialog
        MarketplaceDialog(self.app, prop, self).exec()

    def _set_status(self, status: str) -> None:
        if self.current_id is None:
            return
        self.app.property_repo.set_status(self.current_id, status)
        self.status_changed.emit(self.current_id, status)
        self.load_property(self.current_id)


def _form_label(text: str) -> QLabel:
    """A form label with a slightly muted colour.

    The colour is applied later by PropertyForm._restyle_labels so it follows
    the theme; the ``muted`` property marks it for that pass.
    """
    label = QLabel(text)
    label.setFont(font(10))
    label.setProperty("muted", True)
    label.setStyleSheet("color:#4a453e;")
    return label
