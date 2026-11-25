"""Regressions for the second batch of client notes (Lite/production)."""
from PyQt6.QtWidgets import QComboBox

from src.data.models import Property


def test_pet_policy_is_a_yes_no_dropdown(kekar_app):
    """Note 1: the form asks Yes/No, not free text."""
    form = kekar_app.main_window.property_form
    form.load_property(None)
    combo = form.pet_input
    assert isinstance(combo, QComboBox)
    assert [combo.itemText(i) for i in range(combo.count())] == ["No", "Yes"]
    combo.setCurrentText("Yes")
    form.address_input.setText("Pet Combo Way")
    form.save()
    assert kekar_app.property_repo.get(form.current_id).pet_policy == "Yes"


def test_move_dates_live_in_rental_terms(kekar_app):
    """Note 3: move dates belong with the other long-term rental terms."""
    form = kekar_app.main_window.property_form
    assert form.rental_terms.isAncestorOf(form.move_in_input)
    assert form.rental_terms.isAncestorOf(form.move_out_input)


def test_move_dates_use_calendar_popups(kekar_app):
    """Note 2: move dates are picked from a mini calendar."""
    from PyQt6.QtCore import QDate
    from PyQt6.QtWidgets import QDateEdit

    form = kekar_app.main_window.property_form
    form.load_property(None)
    for widget in (form.move_in_input, form.move_out_input):
        assert isinstance(widget, QDateEdit)
        assert widget.calendarPopup() is True

    form.address_input.setText("Date Picker Way")
    form.move_in_input.setDate(QDate(2027, 3, 4))
    form.move_out_input.setDate(QDate(2028, 3, 3))
    form.save()
    prop = kekar_app.property_repo.get(form.current_id)
    assert prop.move_in_date == "2027-03-04"
    assert prop.move_out_date == "2028-03-03"
    form.load_property(prop.id)
    assert form.move_in_input.date() == QDate(2027, 3, 4)


def test_existing_pet_text_maps_to_the_new_dropdown(kekar_app):
    form = kekar_app.main_window.property_form
    pid = kekar_app.property_repo.create(
        Property(address="Old Pets Way", pet_policy="Cats OK"))
    form.load_property(pid)
    assert form.pet_input.currentText() == "Yes"
    pid2 = kekar_app.property_repo.create(
        Property(address="Old No Pets Way", pet_policy="No pets"))
    form.load_property(pid2)
    assert form.pet_input.currentText() == "No"
