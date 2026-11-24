"""Reservations: a month calendar and a bookings table for short stays."""
from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtWidgets import (QCalendarWidget, QComboBox, QDateEdit, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QGridLayout,
                             QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPlainTextEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ..data.models import (BOOKING_STATUSES, PORTAL_LABELS, PORTALS, Booking)
from .palette import Theme
from .theme import font


class BookingDialog(QDialog):
    """Create or edit one stay."""

    def __init__(self, app, prop, booking: Booking | None, parent=None):
        super().__init__(parent)
        self.app = app
        self.booking = booking
        self.setWindowTitle("Stay" if booking is None else "Edit stay")
        self.resize(420, 420)

        layout = QGridLayout(self)
        self.guest = QComboBox()
        self.guest.setEditable(True)
        self.guest.lineEdit().setPlaceholderText("Guest name")
        self.contact = QComboBox()
        self.contact.setEditable(True)
        self.contact.lineEdit().setPlaceholderText("Phone or email (optional)")
        self.check_in = QDateEdit()
        self.check_in.setCalendarPopup(True)
        self.check_in.setDate(QDate.currentDate())
        self.check_out = QDateEdit()
        self.check_out.setCalendarPopup(True)
        self.check_out.setDate(QDate.currentDate().addDays(2))
        self.portal = QComboBox()
        self.portal.addItem("(direct)", "")
        for key in PORTALS:
            self.portal.addItem(PORTAL_LABELS[key], key)
        self.payout = QDoubleSpinBox()
        self.payout.setRange(0, 100000)
        self.payout.setPrefix("$")
        self.payout.setSingleStep(10)
        self.status = QComboBox()
        self.status.addItems(BOOKING_STATUSES)
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(60)
        self.notes.setPlaceholderText("Optional note")

        fields = [
            ("Guest", self.guest, 0, 0, 3),
            ("Contact", self.contact, 1, 0, 3),
            ("Check-in", self.check_in, 2, 0, 1),
            ("Check-out", self.check_out, 2, 1, 1),
            ("Portal", self.portal, 3, 0, 1),
            ("Payout", self.payout, 3, 1, 1),
            ("Status", self.status, 4, 0, 1),
            ("Note", self.notes, 5, 0, 3),
        ]
        for label, widget, row, column, span in fields:
            layout.addWidget(QLabel(label), row, column * 2)
            layout.addWidget(widget, row, column * 2 + 1, 1, span)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 6, 0, 1, 4)

        if booking is not None:
            self.guest.setEditText(booking.guest_name)
            self.contact.setEditText(booking.guest_contact or "")
            self.check_in.setDate(QDate.fromString(booking.check_in,
                                                  Qt.DateFormat.ISODate))
            self.check_out.setDate(QDate.fromString(booking.check_out,
                                                   Qt.DateFormat.ISODate))
            index = self.portal.findData(booking.portal)
            self.portal.setCurrentIndex(index if index >= 0 else 0)
            self.payout.setValue(booking.payout or 0)
            self.status.setCurrentText(booking.status)
            self.notes.setPlainText(booking.notes or "")

    def _accept(self) -> None:
        if not self.guest.currentText().strip():
            QMessageBox.information(self, "KeKar", "A guest name is required.")
            return
        self.accept()

    def booking_from_form(self, prop, existing: Booking | None) -> Booking:
        start = self.check_in.date().toString(Qt.DateFormat.ISODate)
        end = self.check_out.date().toString(Qt.DateFormat.ISODate)
        base = existing or Booking(property_id=prop.id)
        base.property_id = prop.id
        base.guest_name = self.guest.currentText().strip()
        base.guest_contact = self.contact.currentText().strip() or None
        base.check_in = start
        base.check_out = end
        base.portal = self.portal.currentData() or ""
        base.payout = self.payout.value() or None
        base.status = self.status.currentText()
        base.notes = self.notes.toPlainText().strip() or None
        return base


class StaysTab(QWidget):
    """Bookings for one short-stay property, on a calendar and in a table."""

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._loading = False
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Property</b>"))
        self.property_combo = QComboBox()
        self.property_combo.currentIndexChanged.connect(self._on_property)
        add_btn = QPushButton("Add stay")
        add_btn.clicked.connect(self.add_booking)
        top.addWidget(self.property_combo, 1)
        top.addWidget(add_btn)
        layout.addLayout(top)

        self.calendar = QCalendarWidget()
        self.calendar.setMaximumHeight(230)
        self.calendar.selectionChanged.connect(self._on_selection)
        layout.addWidget(self.calendar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Guest", "Portal", "Check-in", "Check-out", "Nights", "Payout",
             "Status", "Source"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        edit_btn = QPushButton("Edit stay")
        edit_btn.clicked.connect(self.edit_booking)
        cancel_btn = QPushButton("Cancel stay")
        cancel_btn.clicked.connect(self.cancel_booking)
        delete_btn = QPushButton("Delete stay")
        delete_btn.clicked.connect(self.delete_booking)
        actions.addWidget(edit_btn)
        actions.addWidget(cancel_btn)
        actions.addStretch(1)
        actions.addWidget(delete_btn)
        layout.addLayout(actions)

        self.reload()

    # -- data --------------------------------------------------------------

    def reload(self) -> None:
        props = self.app.property_repo.list()
        previous = self.property_combo.currentData()
        self._loading = True
        self.property_combo.clear()
        for prop in props:
            self.property_combo.addItem(prop.address, prop.id)
        if previous is not None:
            index = self.property_combo.findData(previous)
            if index >= 0:
                self.property_combo.setCurrentIndex(index)
        self._loading = False
        self._refresh()

    def _refresh(self) -> None:
        pid = self.property_combo.currentData()
        bookings = (self.app.booking_repo.list(property_id=pid)
                    if pid is not None else [])
        self.table.setRowCount(0)
        for booking in bookings:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                booking.guest_name,
                PORTAL_LABELS.get(booking.portal, booking.portal
                                  or "direct"),
                booking.check_in, booking.check_out,
                str(booking.nights or ""),
                f"{booking.payout:,.0f}" if booking.payout else "",
                booking.status, booking.source,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, booking.id)
                self.table.setItem(row, column, item)
        self._paint_calendar(pid)

    def _paint_calendar(self, pid: int | None) -> None:
        default = QTextCharFormat()
        self.calendar.setDateTextFormat(QDate(), default)
        if pid is None:
            return
        theme = self.app.current_theme()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(theme.accent))
        fmt.setForeground(QColor(theme.on_accent))
        fmt.setFontWeight(700)
        for day in self.app.booking_repo.booked_dates(pid):
            self.calendar.setDateTextFormat(
                QDate(day.year, day.month, day.day), fmt)

    def _selected_booking(self) -> Booking | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        booking_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return self.app.booking_repo.get(int(booking_id))

    # -- actions -----------------------------------------------------------

    def _on_property(self) -> None:
        if not self._loading:
            self._refresh()

    def _on_selection(self) -> None:
        """Select the table row for the day the user clicked, if any."""
        pid = self.property_combo.currentData()
        if pid is None:
            return
        picked = self.calendar.selectedDate()
        day = date(picked.year(), picked.month(), picked.day())
        for booking in self.app.booking_repo.list(property_id=pid):
            try:
                start = date.fromisoformat(booking.check_in)
                end = date.fromisoformat(booking.check_out)
            except ValueError:
                continue
            if start <= day < end:
                self._select_booking(booking.id)
                return

    def _select_booking(self, booking_id: int) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item.data(Qt.ItemDataRole.UserRole) == booking_id:
                self.table.selectRow(row)
                return

    def add_booking(self) -> None:
        pid = self.property_combo.currentData()
        prop = self.app.property_repo.get(int(pid)) if pid is not None else None
        if prop is None:
            QMessageBox.information(self, "KeKar",
                                    "Choose a short-stay property first.")
            return
        dialog = BookingDialog(self.app, prop, None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.app.booking_repo.create(
                dialog.booking_from_form(prop, None))
        except ValueError as exc:
            QMessageBox.warning(self, "KeKar", str(exc))
            return
        self._refresh()

    def edit_booking(self) -> None:
        booking = self._selected_booking()
        if booking is None:
            QMessageBox.information(self, "KeKar", "Choose a stay first.")
            return
        prop = self.app.property_repo.get(booking.property_id)
        if prop is None:
            return
        dialog = BookingDialog(self.app, prop, booking, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.app.booking_repo.update(
                dialog.booking_from_form(prop, booking))
        except ValueError as exc:
            QMessageBox.warning(self, "KeKar", str(exc))
            return
        self._refresh()

    def cancel_booking(self) -> None:
        booking = self._selected_booking()
        if booking is None:
            QMessageBox.information(self, "KeKar", "Choose a stay first.")
            return
        booking.status = "cancelled"
        self.app.booking_repo.update(booking)
        self._refresh()
        self.app.main_window.status(f"Cancelled the stay for "
                                    f"{booking.guest_name or 'guest'}.")

    def delete_booking(self) -> None:
        booking = self._selected_booking()
        if booking is None:
            QMessageBox.information(self, "KeKar", "Choose a stay first.")
            return
        answer = QMessageBox.question(
            self, "KeKar",
            f"Delete the stay for {booking.guest_name or 'guest'} "
            f"({booking.check_in} to {booking.check_out})?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.app.booking_repo.delete(booking.id)
        self._refresh()
        self.app.main_window.status("Stay deleted.")

    def apply_theme(self, theme: Theme) -> None:
        pid = self.property_combo.currentData()
        self._paint_calendar(pid)
