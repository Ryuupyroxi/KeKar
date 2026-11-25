"""Editable property detail form with amenity toggles and quick actions."""
from __future__ import annotations

from PyQt6.QtCore import (QDate, Qt, QThread, QTimer, QStringListModel,
                          pyqtSignal)
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QCompleter,
                             QDateEdit, QDoubleSpinBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
                             QWidget)

from .. import features
from ..data.models import PROPERTY_KINDS, Property, SHORT_STAY_KIND
from ..services import image_service
from ..services.listing_compiler import (AMENITY_LABELS as AMENITY_FIELDS,
                                         compile_listing, validate_listing)
from . import worker
from .listing_dialog import ListingDialog
from .palette import Theme
from .theme import font
from .widgets import StatusPill

def _kind_labels() -> tuple[tuple[str, str], ...]:
    """Lite has no portal connections, so it drops the site name."""
    stay = "Short stay" if features.is_lite() else "Short stay (Airbnb)"
    return (("Long-term rental", "rental"), (stay, SHORT_STAY_KIND))

#: Google Maps suggestions wait for a pause in typing and need a real start.
MAPS_DEBOUNCE_MS = 350
MAPS_MIN_CHARS = 4


class _MapsAutocompleteThread(QThread):
    """Fetches place predictions off the UI thread."""

    done = pyqtSignal(object, str)  # suggestions, error

    def __init__(self, key: str, text: str):
        super().__init__()
        self.key = key
        self.text = text

    def run(self) -> None:
        from ..services import maps_service
        try:
            suggestions = maps_service.autocomplete(self.key, self.text)
        except Exception as exc:
            self.done.emit(None, str(exc))
            return
        self.done.emit(suggestions, "")


class _MapsDetailsThread(QThread):
    """Fetches one place's address components off the UI thread."""

    done = pyqtSignal(object, str)  # PlaceDetails, error

    def __init__(self, key: str, place_id: str):
        super().__init__()
        self.key = key
        self.place_id = place_id

    def run(self) -> None:
        from ..services import maps_service
        try:
            details = maps_service.place_details(self.key, self.place_id)
        except Exception as exc:
            self.done.emit(None, str(exc))
            return
        self.done.emit(details, "")


class _PortalSyncThread(QThread):
    """Imports a portal calendar off the UI thread (it fetches a URL)."""

    done = pyqtSignal(str, dict)

    def __init__(self, app, property_id: int, portal: str):
        super().__init__()
        self.app = app
        self.property_id = property_id
        self.portal = portal

    def run(self) -> None:
        prop = self.app.property_repo.get(self.property_id)
        if prop is None:
            self.done.emit(self.portal, {
                "status": "failed", "detail": "Property not found."})
            return
        from ..services import portal_sync
        result = portal_sync.sync_portal(self.app.db, prop, self.portal)
        self.done.emit(self.portal, result)


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

        # --- header row: kind + status + delete -------------------------
        header = QHBoxLayout()
        header.addWidget(_form_label("Type"))
        self.kind_combo = QComboBox()
        for label, key in _kind_labels():
            self.kind_combo.addItem(label, key)
        header.addWidget(self.kind_combo)
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
        self.bedrooms_input = QSpinBox()
        self.bedrooms_input.setRange(0, 20)
        self.bathrooms_input = QDoubleSpinBox()
        self.bathrooms_input.setRange(0, 20)
        self.bathrooms_input.setSingleStep(0.5)
        self.sqft_input = QSpinBox()
        self.sqft_input.setRange(0, 100000)
        self.sqft_input.setSingleStep(50)
        self.pet_input = QComboBox()
        self.pet_input.addItems(["No", "Yes"])
        self.move_in_input = QDateEdit()
        self.move_out_input = QDateEdit()
        for widget in (self.move_in_input, self.move_out_input):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setMinimumDate(QDate(2000, 1, 1))
            widget.setSpecialValueText("Not set")

        # --- Google Maps address suggestions ---------------------------
        # With no key the model stays empty, so Qt shows no popup and no
        # request is ever made. The model is filled only from real replies.
        self.last_maps_error = ""
        self._map_suggestions: dict[str, str] = {}
        self._maps_model = QStringListModel(self)
        self._maps_completer = QCompleter(self._maps_model, self)
        self._maps_timer = QTimer(self)
        self._maps_timer.setSingleShot(True)
        if features.maps_enabled():
            self.address_input.setCompleter(self._maps_completer)
            self._maps_completer.activated.connect(self._on_address_selected)
            self._maps_timer.timeout.connect(self._start_address_search)
            self.address_input.textEdited.connect(self._on_address_edited)

        fields = [
            ("Street address", self.address_input),
            ("City", self.city_input),
            ("ZIP", self.zip_input),
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

        # --- long-term terms --------------------------------------------
        self.rental_terms = QGroupBox("Rental terms", self)
        rental_grid = QGridLayout(self.rental_terms)
        rental_grid.setVerticalSpacing(8)
        rental_grid.setHorizontalSpacing(14)
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
        self.pet_deposit_input = QDoubleSpinBox()
        self.pet_deposit_input.setRange(0, 100000)
        self.pet_deposit_input.setPrefix("$")
        self.pet_deposit_input.setSingleStep(25)
        for index, (label, widget) in enumerate((
                ("Monthly rent", self.rent_input),
                ("Security deposit", self.deposit_input),
                ("Available date", self.available_input),
                ("Pet deposit", self.pet_deposit_input),
                ("Move-in date", self.move_in_input),
                ("Move-out date", self.move_out_input))):
            rental_grid.addWidget(_form_label(label), index, 0)
            rental_grid.addWidget(widget, index, 1)
        rental_grid.setColumnStretch(1, 1)
        layout.addWidget(self.rental_terms)

        # --- short-stay terms -------------------------------------------
        self.short_stay_terms = QGroupBox("Short-stay terms", self)
        stay_grid = QGridLayout(self.short_stay_terms)
        stay_grid.setVerticalSpacing(8)
        stay_grid.setHorizontalSpacing(14)
        self.nightly_input = QDoubleSpinBox()
        self.nightly_input.setRange(0, 100000)
        self.nightly_input.setPrefix("$")
        self.nightly_input.setSingleStep(10)
        self.cleaning_input = QDoubleSpinBox()
        self.cleaning_input.setRange(0, 100000)
        self.cleaning_input.setPrefix("$")
        self.cleaning_input.setSingleStep(10)
        self.extra_guest_input = QDoubleSpinBox()
        self.extra_guest_input.setRange(0, 100000)
        self.extra_guest_input.setPrefix("$")
        self.extra_guest_input.setSingleStep(5)
        self.min_stay_input = QSpinBox()
        self.min_stay_input.setRange(0, 365)
        self.max_guests_input = QSpinBox()
        self.max_guests_input.setRange(1, 30)
        self.check_in_input = QLineEdit()
        self.check_in_input.setPlaceholderText("15:00")
        self.check_out_input = QLineEdit()
        self.check_out_input.setPlaceholderText("11:00")
        self.cancellation_input = QComboBox()
        self.cancellation_input.addItems(
            ["Flexible", "Moderate", "Firm", "Strict"])
        self.cancellation_input.setEditable(True)
        self.instant_book_box = QCheckBox("Instant Book")
        self.house_rules_input = QTextEdit()
        self.house_rules_input.setMaximumHeight(60)
        self.house_rules_input.setPlaceholderText(
            "House rules shown to guests, e.g. No parties, no smoking.")
        stay_fields = [
            ("Nightly rate", self.nightly_input),
            ("Cleaning fee", self.cleaning_input),
            ("Extra guest fee", self.extra_guest_input),
            ("Minimum stay (nights)", self.min_stay_input),
            ("Max guests", self.max_guests_input),
            ("Check-in time", self.check_in_input),
            ("Check-out time", self.check_out_input),
            ("Cancellation policy", self.cancellation_input),
        ]
        for index, (label, widget) in enumerate(stay_fields):
            row, column = divmod(index, 2)
            stay_grid.addWidget(_form_label(label), row, column * 2)
            stay_grid.addWidget(widget, row, column * 2 + 1)
        stay_grid.addWidget(self.instant_book_box, 4, 0)
        stay_grid.addWidget(_form_label("House rules"), 5, 0)
        stay_grid.addWidget(self.house_rules_input, 5, 1, 1, 3)
        stay_grid.setColumnStretch(1, 1)
        stay_grid.setColumnStretch(3, 1)
        layout.addWidget(self.short_stay_terms)

        if features.portal_sync_enabled():
            from ..data.models import PORTALS, PORTAL_LABELS, PortalSettings
            # --- portals -----------------------------------------------------
            self.portals_box = QGroupBox("Portals", self)
            self.portal_rows: dict[str, dict] = {}
            portals_layout = QVBoxLayout(self.portals_box)
            for key in PORTALS:
                row = QHBoxLayout()
                enabled = QCheckBox(PORTAL_LABELS[key])
                enabled.setToolTip(f"List this unit on {PORTAL_LABELS[key]}")
                price = QDoubleSpinBox()
                price.setRange(0, 100000)
                price.setPrefix("$")
                price.setSpecialValueText("default")
                price.setToolTip("Leave at 0 to use the property's nightly rate")
                stay = QSpinBox()
                stay.setRange(0, 365)
                stay.setSuffix(" nights")
                stay.setSpecialValueText("default")
                stay.setToolTip("Leave at 0 to use the property's minimum stay")
                sync = QPushButton("Sync now")
                sync.setProperty("portal", key)
                sync.clicked.connect(self._sync_portal)
                sync.setToolTip(f"Import the {PORTAL_LABELS[key]} calendar")
                last = QLabel("")
                last.setProperty("portal_last", key)
                last.setFont(font(9))
                row.addWidget(enabled)
                row.addWidget(QLabel("Price"))
                row.addWidget(price)
                row.addWidget(QLabel("Min stay"))
                row.addWidget(stay)
                row.addWidget(sync)
                row.addWidget(last, 1)
                portals_layout.addLayout(row)

                url_row = QHBoxLayout()
                url = QLineEdit()
                url.setPlaceholderText(
                    f"{PORTAL_LABELS[key]} calendar URL (.ics)")
                url.setToolTip("The portal's own iCal export URL")
                url_row.addWidget(QLabel("Calendar"))
                url_row.addWidget(url, 1)
                portals_layout.addLayout(url_row)
                self.portal_rows[key] = {
                    "enabled": enabled, "price": price, "stay": stay,
                    "url": url, "last": last, "sync": sync,
                }

            export_btn = QPushButton("Export calendar (.ics)…")
            export_btn.setToolTip(
                "Write an iCal file of this property's bookings, to upload to a "
                "portal")
            export_btn.clicked.connect(self.export_calendar)
            portals_layout.addWidget(export_btn)
            layout.addWidget(self.portals_box)
        else:
            self.portals_box = None
            self.portal_rows = {}


        # --- amenities ---------------------------------------------------
        amenities_box = QGroupBox("Amenities", self)
        # Three per row: five checkboxes in one row made the group box ~725 px
        # wide at its minimum, which is wider than a short window's detail pane.
        amenities_layout = QGridLayout(amenities_box)
        self.amenity_boxes: dict[str, QCheckBox] = {}
        for index, (attr, label) in enumerate(AMENITY_FIELDS):
            box = QCheckBox(label)
            self.amenity_boxes[attr] = box
            amenities_layout.addWidget(box, index // 3, index % 3)

        self.driveway_box = QCheckBox("Driveway")
        self.street_box = QCheckBox("Street parking")
        self.garage_1_box = QCheckBox("1-car garage")
        self.garage_2_box = QCheckBox("2-car garage")
        for box in (self.driveway_box, self.street_box):
            box.toggled.connect(self._on_parking_toggled)
        for box in (self.garage_1_box, self.garage_2_box):
            box.toggled.connect(self._on_garage_toggled)
        parking_row = (len(AMENITY_FIELDS) + 2) // 3
        amenities_layout.addWidget(QLabel("Parking"), parking_row, 0)
        amenities_layout.addWidget(self.driveway_box, parking_row, 1)
        amenities_layout.addWidget(self.street_box, parking_row, 2)
        amenities_layout.addWidget(QLabel("Garage"), parking_row + 1, 0)
        amenities_layout.addWidget(self.garage_1_box, parking_row + 1, 1)
        amenities_layout.addWidget(self.garage_2_box, parking_row + 1, 2)
        amenities_layout.setColumnStretch(2, 1)
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
        self.publish_btn = None
        if features.marketplace_enabled():
            self.publish_btn = QPushButton("Publish to Marketplace...")
            # The same button is the listing dialog for a short stay: the
            # design gives a short stay "Portal listing…" instead of
            # Marketplace autofill.
            self.publish_btn.clicked.connect(self._publish_or_list)
        # Two rows of three: six buttons in one row gave the form a ~900 px
        # minimum width, so the detail pane scrolled horizontally on a 1280 px
        # window and the last field was clipped by the panel edge.
        actions = QHBoxLayout()
        for btn in (self.save_btn, self.preview_btn, self.copy_btn):
            actions.addWidget(btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        actions_two = QHBoxLayout()
        for btn in (self.publish_btn, self.rented_btn, self.vacant_btn):
            if btn is not None:
                actions_two.addWidget(btn)
        actions_two.addStretch(1)
        layout.addLayout(actions_two)
        layout.addStretch(1)

        # Kind visibility is wired last: its handler reads both term groups
        # and the publish button, which do not exist while the form is built.
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        self._on_kind_changed()

    # -- loading and saving ------------------------------------------------

    def _status_colour(self, status: str) -> str:
        theme = self._theme
        if theme is None:
            return "#2e7d32" if status == "Vacant" else "#c62828"
        return theme.vacant if status == "Vacant" else theme.rented

    def _neutral_colour(self) -> str:
        return self._theme.neutral if self._theme is not None else "#616161"

    # -- Google Maps address suggestions -----------------------------------

    def _on_address_edited(self, text: str) -> None:
        """Debounce user typing; an unset key keeps this entirely offline."""
        if not features.maps_enabled():
            self._maps_timer.stop()
            return
        key = self.app.settings.maps_key.strip()
        if not key or len(text.strip()) < MAPS_MIN_CHARS:
            self._maps_timer.stop()
            self._maps_model.setStringList([])
            self._maps_completer.popup().hide()
            self._map_suggestions.clear()
            return
        self._maps_timer.start(MAPS_DEBOUNCE_MS)

    def _start_address_search(self) -> None:
        if not features.maps_enabled():
            return
        key = self.app.settings.maps_key.strip()
        text = self.address_input.text().strip()
        if not key or len(text) < MAPS_MIN_CHARS:
            self._maps_model.setStringList([])
            return
        thread = _MapsAutocompleteThread(key, text)
        thread.done.connect(
            lambda suggestions, error, q=text, t=thread:
                self._on_suggestions(suggestions, error, q, t))
        worker.register(thread)
        thread.start()

    def _on_suggestions(self, suggestions, error: str, query: str,
                        thread: QThread) -> None:
        worker.reap(thread)
        if error:
            self.last_maps_error = error
            self._maps_model.setStringList([])
            self.app.main_window.status(f"Address lookup: {error}")
            return
        if self.address_input.text().strip() != query:
            return  # A newer edit superseded this reply.
        self._map_suggestions = {
            item.description: item.place_id for item in (suggestions or [])}
        self._maps_model.setStringList(list(self._map_suggestions))
        # The model was empty when Qt handled the keystroke, so re-trigger
        # completion once the delayed reply arrives — otherwise the user
        # types again before the dropdown appears.
        if self._map_suggestions:
            self._maps_completer.complete()

    def _on_address_selected(self, description: str) -> None:
        """A pick fills the address and optionally the *empty* city/ZIP."""
        if not features.maps_enabled():
            return
        self.address_input.setText(description)
        place_id = self._map_suggestions.get(description, "")
        self._maps_model.setStringList([])
        self._map_suggestions.clear()
        key = self.app.settings.maps_key.strip()
        if not place_id or not key or not self.app.settings.maps_autofill:
            return
        thread = _MapsDetailsThread(key, place_id)
        thread.done.connect(
            lambda details, error, t=thread:
                self._on_place_details(details, error, t))
        worker.register(thread)
        thread.start()

    def _on_place_details(self, details, error: str,
                          thread: QThread) -> None:
        worker.reap(thread)
        if error:
            self.last_maps_error = error
            self.app.main_window.status(f"Address details: {error}")
            return
        self._autofill_empty(details)

    def _autofill_empty(self, details) -> None:
        """Fill City and ZIP only where the user left them blank."""
        if not self.city_input.text().strip() and details.city:
            self.city_input.setText(details.city)
        if not self.zip_input.text().strip() and details.postal_code:
            self.zip_input.setText(details.postal_code)

    # -- portals ---------------------------------------------------------

    @staticmethod
    def _last_sync_label(stamp: str | None) -> str:
        return f"Last sync: {stamp}" if stamp else "Not synced yet"

    def _load_portals(self, prop: Property) -> None:
        """Fill the portal rows from the stored settings."""
        if self.portals_box is None:
            return
        if prop.id is None:
            return
        for key, row in self.portal_rows.items():
            settings = self.app.portal_repo.get(prop.id, key)
            row["enabled"].setChecked(bool(settings and settings.enabled))
            row["price"].setValue(
                settings.price_override if settings
                and settings.price_override else 0)
            row["stay"].setValue(
                settings.min_stay_override if settings
                and settings.min_stay_override else 0)
            row["url"].setText(settings.external_ical_url or ""
                               if settings else "")
            row["last"].setText(
                self._last_sync_label(settings.last_sync_at)
                if settings else "Not synced yet")

    def _save_portals(self, prop: Property) -> None:
        """Store the portal rows. Called after the property itself is saved.

        Only a short stay has portals, so saving a rental writes nothing —
        otherwise every long-term let would accumulate three inert rows.
        """
        if self.portals_box is None:
            return
        from ..data.models import PortalSettings
        if prop.id is None or not self._is_short_stay():
            return
        for key, row in self.portal_rows.items():
            existing = self.app.portal_repo.get(prop.id, key)
            self.app.portal_repo.save(PortalSettings(
                property_id=prop.id, portal=key,
                enabled=row["enabled"].isChecked(),
                price_override=row["price"].value() or None,
                min_stay_override=row["stay"].value() or None,
                external_ical_url=row["url"].text().strip() or None,
                last_sync_at=(existing.last_sync_at if existing else None)))

    def _sync_portal(self) -> None:
        if self.portals_box is None:
            return
        if self.current_id is None:
            QMessageBox.information(self, "KeKar", "Save the property first.")
            return
        portal = self.sender().property("portal")
        row = self.portal_rows[portal]
        # A URL typed moments ago must be stored before it is fetched.
        self._save_portals(self._collect())
        row["sync"].setEnabled(False)
        row["last"].setText("Syncing…")
        thread = _PortalSyncThread(self.app, self.current_id, portal)
        thread.done.connect(
            lambda result, p=portal: self._on_sync_done(p, result))
        worker.register(thread)
        thread.start()

    def _on_sync_done(self, portal: str, result: dict) -> None:
        if self.portals_box is None:
            return
        from ..data.models import PORTAL_LABELS
        thread = self.sender()
        worker.reap(thread if isinstance(thread, QThread) else None)
        row = self.portal_rows[portal]
        row["sync"].setEnabled(True)
        settings = (self.app.portal_repo.get(self.current_id, portal)
                    if self.current_id is not None else None)
        row["last"].setText(self._last_sync_label(
            settings.last_sync_at if settings else None))
        detail = result.get("detail", "Nothing happened.")
        if result.get("status") == "failed":
            QMessageBox.warning(self, "KeKar", detail)
        else:
            self.app.main_window.status(f"{PORTAL_LABELS[portal]}: {detail}")
        self.app.main_window.reload_all()

    def export_calendar(self) -> None:
        """Write this property's bookings as an iCal file for a portal."""
        if self.portals_box is None:
            return
        from ..services import ical_service
        if self.current_id is None:
            QMessageBox.information(self, "KeKar", "Save the property first.")
            return
        prop = self.app.property_repo.get(self.current_id)
        if prop is None:
            return
        bookings = self.app.booking_repo.list(property_id=self.current_id)
        path = ical_service.export_ical(prop, bookings)
        self.app.main_window.status(f"Calendar written to {path}")
        QMessageBox.information(
            self, "KeKar",
            f"Calendar written to:\n{path}\n\n"
            f"Upload that file to the portal, or keep it for your records.")

    def _is_short_stay(self) -> bool:
        return self.kind_combo.currentData() == SHORT_STAY_KIND

    def _on_kind_changed(self) -> None:
        """Show the term group that matches the selected kind."""
        short = self._is_short_stay()
        self.rental_terms.setVisible(not short)
        self.short_stay_terms.setVisible(short)
        if self.portals_box is not None:
            self.portals_box.setVisible(short)
        # Marketplace auto-fill is a long-term listing flow; a short stay gets
        # the per-portal listing packages instead.
        if self.publish_btn is not None:
            self.publish_btn.setText("Portal listing…" if short
                                     else "Publish to Marketplace...")

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
            else "#ece7e0"
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
        self._maps_timer.stop()
        self._maps_model.setStringList([])
        self._maps_completer.popup().hide()
        self._map_suggestions.clear()
        self.last_maps_error = ""
        for widget in (self.address_input, self.city_input, self.zip_input,
                       self.available_input,
                       self.check_in_input, self.check_out_input):
            widget.clear()
        self.notes_input.clear()
        self.house_rules_input.clear()
        self.pet_input.setCurrentIndex(0)
        self.pet_deposit_input.setValue(0)
        for box in (self.driveway_box, self.street_box,
                    self.garage_1_box, self.garage_2_box):
            box.setChecked(False)
        self.move_in_input.setDate(self.move_in_input.minimumDate())
        self.move_out_input.setDate(self.move_out_input.minimumDate())
        for widget in (self.rent_input, self.deposit_input,
                       self.bedrooms_input, self.bathrooms_input,
                       self.sqft_input, self.nightly_input, self.cleaning_input,
                       self.extra_guest_input, self.min_stay_input):
            widget.setValue(0)
        self.max_guests_input.setValue(1)
        self.instant_book_box.setChecked(False)
        self.cancellation_input.setCurrentText("Flexible")
        for box in self.amenity_boxes.values():
            box.setChecked(False)
        self._on_kind_changed()

    def _fill_fields(self, p: Property) -> None:
        self.address_input.setText(p.address or "")
        self.city_input.setText(p.city or "")
        self.zip_input.setText(p.zip_code or "")
        self.rent_input.setValue(p.rent_price or 0)
        self.deposit_input.setValue(p.deposit_amount or 0)
        self.available_input.setText(p.available_date or "")
        self.pet_deposit_input.setValue(p.pet_deposit_amount or 0)
        self._load_date(self.move_in_input, p.move_in_date)
        self._load_date(self.move_out_input, p.move_out_date)
        self.nightly_input.setValue(p.nightly_price or 0)
        self.cleaning_input.setValue(p.cleaning_fee or 0)
        self.extra_guest_input.setValue(p.extra_guest_fee or 0)
        self.min_stay_input.setValue(p.min_stay_nights or 0)
        self.max_guests_input.setValue(p.max_guests or 1)
        self.check_in_input.setText(p.check_in_time or "")
        self.check_out_input.setText(p.check_out_time or "")
        self.cancellation_input.setCurrentText(p.cancellation_policy
                                               or "Flexible")
        self.instant_book_box.setChecked(bool(p.instant_book))
        self.house_rules_input.setPlainText(p.house_rules or "")
        self.bedrooms_input.setValue(p.bedrooms or 0)
        self.bathrooms_input.setValue(p.bathrooms or 0)
        self.sqft_input.setValue(p.sqft or 0)
        policy = (p.pet_policy or "").strip().lower()
        self.pet_input.setCurrentIndex(
            1 if policy and policy not in {"no", "none", "no pet", "no pets"}
            else 0)
        self.notes_input.setPlainText(p.notes or "")
        for attr, box in self.amenity_boxes.items():
            box.setChecked(bool(getattr(p, attr)))
        self.garage_1_box.setChecked(p.garage_spaces == 1)
        self.garage_2_box.setChecked(p.garage_spaces == 2)
        self.driveway_box.setChecked(p.parking_type == "Driveway")
        self.street_box.setChecked(p.parking_type == "Street parking")
        index = self.kind_combo.findData(
            p.kind if p.kind in PROPERTY_KINDS else "rental")
        if index >= 0:
            self.kind_combo.setCurrentIndex(index)
        self._on_kind_changed()
        if self.portals_box is not None:
            self._load_portals(p)

    def _on_parking_toggled(self, checked: bool) -> None:
        if not checked:
            return
        if self.sender() is self.driveway_box:
            self.street_box.setChecked(False)
        elif self.sender() is self.street_box:
            self.driveway_box.setChecked(False)

    def _on_garage_toggled(self, checked: bool) -> None:
        if not checked:
            return
        if self.sender() is self.garage_1_box:
            self.garage_2_box.setChecked(False)
        elif self.sender() is self.garage_2_box:
            self.garage_1_box.setChecked(False)

    @staticmethod
    def _load_date(widget: QDateEdit, value: str | None) -> None:
        day = QDate.fromString(value or "", Qt.DateFormat.ISODate)
        widget.setDate(day if day.isValid() else widget.minimumDate())

    @staticmethod
    def _save_date(widget: QDateEdit) -> str | None:
        if widget.date() == widget.minimumDate():
            return None
        return widget.date().toString(Qt.DateFormat.ISODate)

    def _collect(self) -> Property:
        return Property(
            id=self.current_id,
            address=self.address_input.text().strip(),
            city=self.city_input.text().strip() or None,
            zip_code=self.zip_input.text().strip() or None,
            rent_price=self.rent_input.value() or None,
            deposit_amount=self.deposit_input.value() or None,
            available_date=self.available_input.text().strip() or None,
            move_in_date=self._save_date(self.move_in_input),
            move_out_date=self._save_date(self.move_out_input),
            bedrooms=self.bedrooms_input.value() or None,
            bathrooms=self.bathrooms_input.value() or None,
            sqft=self.sqft_input.value() or None,
            pet_policy=self.pet_input.currentText(),
            pet_deposit_amount=self.pet_deposit_input.value() or None,
            garage_spaces=(2 if self.garage_2_box.isChecked()
                           else 1 if self.garage_1_box.isChecked() else 0),
            parking_type=("Driveway" if self.driveway_box.isChecked()
                          else "Street parking"
                          if self.street_box.isChecked() else None),
            notes=self.notes_input.toPlainText().strip() or None,
            status=self.pill.text() if self.pill.text() in ("Vacant", "Rented")
            else "Vacant",
            kind=self.kind_combo.currentData() or "rental",
            nightly_price=self.nightly_input.value() or None,
            cleaning_fee=self.cleaning_input.value() or None,
            extra_guest_fee=self.extra_guest_input.value() or None,
            min_stay_nights=self.min_stay_input.value() or None,
            max_guests=self.max_guests_input.value() or None,
            check_in_time=self.check_in_input.text().strip() or None,
            check_out_time=self.check_out_input.text().strip() or None,
            instant_book=self.instant_book_box.isChecked(),
            cancellation_policy=(self.cancellation_input.currentText().strip()
                                 or None),
            house_rules=self.house_rules_input.toPlainText().strip() or None,
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
        prop.id = self.current_id
        if self.portals_box is not None:
            self._save_portals(prop)
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

    def _publish_or_list(self) -> None:
        """The one action button: Marketplace for a rental, portals for a stay."""
        if self._is_short_stay():
            self.preview_listing()
        else:
            self.publish_to_marketplace()

    def _set_status(self, status: str) -> None:
        if self.current_id is None:
            QMessageBox.information(
                self, "KeKar", "Choose a saved property first.")
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
    label.setStyleSheet("")
    return label
