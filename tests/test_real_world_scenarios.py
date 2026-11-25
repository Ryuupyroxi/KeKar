"""End-to-end user journeys, not isolated widget checks.

Each scenario follows one realistic day in the life of a property manager and
asserts the result the client would actually see.
"""
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QLabel

from src.app import Application
from src.data.models import SHORT_STAY_KIND, Applicant, Booking, Property
from src.services.listing_compiler import amenities_line
from src.ui.calendar_tab import SHORT_STAY_COLOUR
from src.ui.palette import DARK, OLED


def _fill_rental(form, address, move_in, move_out):
    form.load_property(None)
    form.address_input.setText(address)
    form.city_input.setText("Pawhuska")
    form.rent_input.setValue(1250)
    form.pet_input.setCurrentText("Yes")
    form.move_in_input.setDate(QDate.fromString(move_in, Qt.DateFormat.ISODate))
    form.move_out_input.setDate(
        QDate.fromString(move_out, Qt.DateFormat.ISODate))
    form.garage_2_box.setChecked(True)
    form.driveway_box.setChecked(True)
    form.save()
    return form.current_id


def test_scenario_landlord_prepares_a_pet_friendly_rental(kekar_app):
    """New rental → lease → calendar → listing copy, in one sitting."""
    window = kekar_app.main_window
    pid = _fill_rental(window.property_form, "101 Oak Street",
                       "2027-01-05", "2027-12-31")
    prop = kekar_app.property_repo.get(pid)
    assert (prop.garage_spaces, prop.parking_type) == (2, "Driveway")

    lease = window.lease_tab
    lease.reload()
    lease.property_combo.setCurrentIndex(lease.property_combo.findData(pid))
    lease.tenant_edit.setText("Alicia Reyes")
    lease.generate()
    text = lease.preview.toPlainText()
    assert "Pet policy: Yes" in text
    assert "$300.00" in text and "refundable pet deposit" in text

    calendar = window.calendar_tab
    calendar.reload()
    lines = [calendar.events.item(i).text()
             for i in range(calendar.events.count())]
    row = next(line for line in lines if "101 Oak Street" in line)
    assert "Move-in 2027-01-05" in row
    assert "Move-out 2027-12-31" in row

    listing = amenities_line(prop)
    assert "Garage: 2 cars" in listing
    assert "Parking: Driveway" in listing


def test_scenario_agent_screens_an_applicant(kekar_app):
    """Add an applicant, open the profile from one click, edit and save."""
    window = kekar_app.main_window
    pid = kekar_app.property_repo.create(
        Property(address="202 Cedar Court"))
    aid = kekar_app.applicant_repo.create(
        Applicant(applicant_name="New applicant", property_id=pid))
    tab = window.crm_tab
    tab.reload()
    tab.table.cellClicked.emit(0, 0)
    assert tab.profile_name.text() == "New applicant"

    tab.profile_name.setText("Alicia Reyes")
    tab.profile_contact.setText("alicia@example.com")
    tab.profile_stage.setCurrentText("Background Check")
    tab.profile_notes.setPlainText("Income verified; calls Tuesday.")
    tab.profile_save.click()

    saved = kekar_app.applicant_repo.get(aid)
    assert saved.applicant_name == "Alicia Reyes"
    assert saved.contact_info == "alicia@example.com"
    assert saved.screening_stage == "Background Check"
    assert saved.property_id == pid
    assert any(tab.table.item(0, c).text() == "Alicia Reyes"
               for c in range(tab.table.columnCount()))


def test_scenario_host_books_a_short_stay_and_avoids_double_booking(kekar_app):
    """Book a stay, see it in purple, reject an overlapping request."""
    pid = kekar_app.property_repo.create(Property(
        address="303 Lake House", kind=SHORT_STAY_KIND))
    stay_id = kekar_app.booking_repo.create(Booking(
        property_id=pid, guest_name="Morgan", check_in="2027-02-10",
        check_out="2027-02-14", payout=640))
    assert stay_id > 0
    try:
        kekar_app.booking_repo.create(Booking(
            property_id=pid, guest_name="Overlap", check_in="2027-02-12",
            check_out="2027-02-16"))
    except ValueError as exc:
        assert "overlaps" in str(exc)
    else:
        raise AssertionError("overlapping booking was accepted")

    window = kekar_app.main_window
    calendar = window.calendar_tab
    calendar.reload()
    fmt = calendar.calendar.dateTextFormat(QDate(2027, 2, 11))
    assert QColor(SHORT_STAY_COLOUR) == fmt.background().color()
    calendar.calendar.setSelectedDate(QDate(2027, 2, 11))
    assert "303 Lake House" in calendar.date_detail.text()
    assert "Morgan" in calendar.date_detail.text()


def test_scenario_manager_checks_legend_and_dark_theme(kekar_app, monkeypatch):
    """Help explains the colours; OLED stays legible while working."""
    window = kekar_app.main_window
    seen = []
    monkeypatch.setattr(
        "PyQt6.QtWidgets.QMessageBox.information",
        lambda parent, title, text, *args: seen.append((title, text)))
    legend = next(a for a in window.help_menu.actions()
                  if "legend" in (a.text() or "").lower())
    legend.trigger()
    assert seen and "purple" in seen[0][1].lower()

    for theme in (DARK, OLED):
        kekar_app.apply_theme(theme.key)
        assert QApplication.palette().color(
            QPalette.ColorRole.PlaceholderText).name() == theme.text_secondary
        labels = [w for w in window.property_form.findChildren(QLabel)
                  if w.property("muted") is True]
        assert labels and all(theme.text_secondary in w.styleSheet()
                              for w in labels)
