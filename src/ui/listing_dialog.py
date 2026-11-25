"""Listing preview and per-site copy packages.

Zillow and apartments.com have no posting API, so the dialog offers a package
shaped like each site's form: pick a site, copy, paste. The generic package
still works for any other site.
"""
from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                             QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
                             QWidget)

from .. import features
from ..data.models import (PORTALS, PORTAL_LABELS, Property,
                           SHORT_STAY_KIND)
from ..services.clipboard import copy_text
from ..services.listing_sites import (SITES, compile_site_package,
                                      known_sites, site_label)
from ..services.listing_compiler import compile_listing, validate_listing
from .theme import font


class ListingDialog(QDialog):
    """Shows exactly what "Copy listing" would put on the clipboard."""

    def __init__(self, app, prop: Property, parent=None):
        super().__init__(parent)
        self.app = app
        self.prop = prop
        self.setWindowTitle(f"Listing — {prop.address}")
        self.resize(700, 700)

        layout = QVBoxLayout(self)

        picker = QHBoxLayout()
        picker.addWidget(QLabel("<b>Site</b>"))
        self.site_combo = QComboBox()
        self.site_combo.addItem("Any site (generic)", "generic")
        for key in features.visible_sites(known_sites(prop.kind)):
            self.site_combo.addItem(SITES[key]["label"], key)
        self.site_combo.currentIndexChanged.connect(self._refresh)
        picker.addWidget(self.site_combo, 1)
        layout.addLayout(picker)

        self.note = QLabel(
            "Copy the listing and paste it into the site's form — posting "
            "stays with you."
            if features.is_lite() else
            "Zillow and apartments.com have no posting API, so KeKar builds "
            "the listing for each site's form. Copy it and paste it in — "
            "posting stays with you.")
        if prop.kind == SHORT_STAY_KIND:
            self.note.setText(
                "Short-stay sites have no posting API for an independent "
                "host. Copy the package and paste it in — posting stays "
                "with you."
                if features.is_lite() else
                "Airbnb, Vrbo and Booking.com have no posting API for an "
                "independent host, so KeKar builds the listing for each "
                "portal's form. Copy it and paste it in — posting stays "
                "with you.")
        self.note.setWordWrap(True)
        self.note.setFont(font(9))
        layout.addWidget(self.note)

        # Shown only when the selected portal has a price or min-stay
        # override, so the preview never silently disagrees with the form.
        self.override_note = QLabel("")
        self.override_note.setWordWrap(True)
        self.override_note.setFont(font(9))
        layout.addWidget(self.override_note)

        self.text = QPlainTextEdit()
        self.text.setFont(font(11))
        layout.addWidget(self.text, 1)

        self.problems = QLabel("")
        self.problems.setWordWrap(True)
        self.problems.setFont(font(9))
        layout.addWidget(self.problems)

        self.copy_note = QLabel("")
        self.copy_note.setWordWrap(True)
        layout.addWidget(self.copy_note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        copy_btn = QPushButton("Copy to clipboard")
        copy_btn.clicked.connect(self._copy)
        buttons.addButton(copy_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        layout.addWidget(buttons)

        self._refresh()

    def _current(self) -> str:
        return self.site_combo.currentData()

    def _refresh(self) -> None:
        site = self._current()
        if site == "generic":
            body = compile_listing(self.prop)
            self.text.setReadOnly(True)
            self.text.setPlainText(body)
            problems = validate_listing(body)
            self.override_note.setText("")
        else:
            settings = self._portal_settings(site)
            package = compile_site_package(
                self.prop, site,
                price_override=settings.price_override if settings else None,
                min_stay_override=(settings.min_stay_override
                                   if settings else None))
            self.text.setReadOnly(True)
            self.text.setPlainText(package.as_text())
            problems = list(package.warnings)
            self.override_note.setText(self._override_text(settings))
        self.override_note.setStyleSheet(
            f"color:{self.app.current_theme().accent};")
        self.problems.setStyleSheet(
            f"color:{self.app.current_theme().warn_text};")
        self.problems.setText("; ".join(problems) if problems else "")

    def _portal_settings(self, site: str):
        """The stored settings for this portal, or None."""
        if self.prop.id is None or site not in PORTALS:
            return None
        return self.app.portal_repo.get(self.prop.id, site)

    @staticmethod
    def _override_text(settings) -> str:
        if settings is None:
            return ""
        label = PORTAL_LABELS.get(settings.portal, settings.portal)
        parts: list[str] = []
        if settings.price_override:
            parts.append(f"${settings.price_override:,.0f} per night")
        if settings.min_stay_override:
            parts.append(f"{settings.min_stay_override}-night minimum")
        if not parts:
            return ""
        return f"Using the {label} override: " + " and ".join(parts) + "."

    def _copy(self) -> None:
        text = self.text.toPlainText()
        copy_text(text)
        label = ("listing" if self._current() == "generic"
                 else site_label(self._current()))
        self.app.main_window.status(f"{label} copied — paste it into the site.")
        # The status bar sits behind this modal dialog; keep the feedback
        # inside the dialog where the user can actually see it.
        self.copy_note.setText(f"{label} copied — paste it into the site.")
        QTimer.singleShot(3000, self.copy_note.clear)
