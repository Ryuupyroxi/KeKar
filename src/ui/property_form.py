"""Editable property detail form with amenity toggles and quick actions."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                             QLineEdit, QMessageBox, QPushButton, QSpinBox,
                             QVBoxLayout, QWidget)

from ..data.models import Property
from ..services.clipboard import copy_listing
from ..services.listing_compiler import compile_listing, validate_listing
from .widgets import StatusPill

AMENITY_FIELDS = [
    ("amenity_wd", "Washer & dryer in unit"),
    ("amenity_ac", "Central AC & heat"),
    ("amenity_yard", "Fenced yard"),
    ("amenity_dishwasher", "Dishwasher"),
    ("amenity_parking", "Parking spot"),
]


class PropertyForm(QWidget):
    property_saved = pyqtSignal(int)
    status_changed = pyqtSignal(int, str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.current_id: int | None = None

        layout = QVBoxLayout(self)
        self.pill = StatusPill("No property selected", "#616161", self)
        layout.addWidget(self.pill)

        form = QFormLayout()
        self.address_input = QLineEdit()
        self.city_input = QLineEdit()
        self.zip_input = QLineEdit()
        self.rent_input = QDoubleSpinBox()
        self.rent_input.setRange(0, 100000)
        self.deposit_input = QDoubleSpinBox()
        self.deposit_input.setRange(0, 100000)
        self.available_input = QLineEdit()
        self.available_input.setPlaceholderText("2026-12-01")
        self.bedrooms_input = QSpinBox()
        self.bedrooms_input.setRange(0, 20)
        self.bathrooms_input = QDoubleSpinBox()
        self.bathrooms_input.setRange(0, 20)
        self.bathrooms_input.setSingleStep(0.5)
        self.sqft_input = QSpinBox()
        self.sqft_input.setRange(0, 100000)
        self.pet_input = QLineEdit()
        self.notes_input = QLineEdit()

        form.addRow("Street address", self.address_input)
        form.addRow("City", self.city_input)
        form.addRow("ZIP", self.zip_input)
        form.addRow("Monthly rent", self.rent_input)
        form.addRow("Security deposit", self.deposit_input)
        form.addRow("Available date", self.available_input)
        form.addRow("Bedrooms", self.bedrooms_input)
        form.addRow("Bathrooms", self.bathrooms_input)
        form.addRow("Square feet", self.sqft_input)
        form.addRow("Pet policy", self.pet_input)
        form.addRow("Notes", self.notes_input)
        layout.addLayout(form)

        amenities = QHBoxLayout()
        self.amenity_boxes: dict[str, QCheckBox] = {}
        for attr, label in AMENITY_FIELDS:
            box = QCheckBox(label)
            self.amenity_boxes[attr] = box
            amenities.addWidget(box)
        layout.addLayout(amenities)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        self.copy_btn = QPushButton("Copy listing")
        self.copy_btn.clicked.connect(self.copy_listing)
        self.rented_btn = QPushButton("Mark as rented")
        self.rented_btn.clicked.connect(lambda: self._set_status("Rented"))
        self.vacant_btn = QPushButton("Mark as vacant")
        self.vacant_btn.clicked.connect(lambda: self._set_status("Vacant"))
        for btn in (self.save_btn, self.copy_btn, self.rented_btn, self.vacant_btn):
            actions.addWidget(btn)
        layout.addLayout(actions)

    def load_property(self, property_id: int | None) -> None:
        self.current_id = property_id
        if property_id is None:
            self._clear_fields()
            self.pill.setText("New property")
            self.pill.set_color("#616161")
            return
        p = self.app.property_repo.get(property_id)
        if p is None:
            return
        self._fill_fields(p)
        self.pill.setText(p.status)
        self.pill.set_color("#2e7d32" if p.status == "Vacant" else "#c62828")

    def _clear_fields(self) -> None:
        for widget in (self.address_input, self.city_input, self.zip_input,
                       self.available_input, self.pet_input, self.notes_input):
            widget.clear()
        for widget in (self.rent_input, self.deposit_input,
                       self.bedrooms_input, self.bathrooms_input, self.sqft_input):
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
        self.notes_input.setText(p.notes or "")
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
            notes=self.notes_input.text().strip() or None,
            status=self.pill.text() if self.pill.text() in ("Vacant", "Rented") else "Vacant",
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
        self.pill.set_color("#2e7d32" if prop.status == "Vacant" else "#c62828")
        self.property_saved.emit(self.current_id)

    def copy_listing(self) -> None:
        if self.current_id is None:
            QMessageBox.information(self, "KeKar", "Choose or save a property first.")
            return
        prop = self.app.property_repo.get(self.current_id)
        text = compile_listing(prop)
        problems = validate_listing(text)
        if problems:
            QMessageBox.warning(self, "KeKar",
                                "This listing is missing some details:\n- "
                                + "\n- ".join(problems))
        copy_listing(prop)
        self.app.main_window.status("Listing copied — paste it anywhere.")

    def _set_status(self, status: str) -> None:
        if self.current_id is None:
            return
        self.app.property_repo.set_status(self.current_id, status)
        self.status_changed.emit(self.current_id, status)
        self.load_property(self.current_id)
