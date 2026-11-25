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


def test_builtin_lease_is_comprehensive_and_tutorial_wording_fits(kekar_app):
    """Note 1/9: a full base lease, and the tour speaks to the new user."""
    from src.services import lease_builder
    from src.ui.tour import build_tour_steps

    template = lease_builder.DEFAULT_TEMPLATE
    assert lease_builder.unknown_tokens(template) == []
    for clause in ("UTILITIES", "MAINTENANCE", "LANDLORD ACCESS",
                   "TERMINATION", "ENTIRE AGREEMENT"):
        assert clause in template

    text = " ".join(step.body
                    for step in build_tour_steps(kekar_app.main_window))
    assert "upload your own example lease or use the one provided" in text
    assert "your client provided" not in text


def test_preview_picker_says_site_not_channel(kekar_app):
    """Note 6: clients think in sites, not channels."""
    from PyQt6.QtWidgets import QLabel
    from src.ui.listing_dialog import ListingDialog

    dialog = ListingDialog(kekar_app, Property(address="Site Way"))
    try:
        labels = [w.text() for w in dialog.findChildren(QLabel)]
        assert any("Site" in text for text in labels)
        assert not any("Channel" in text for text in labels)
    finally:
        dialog.close()


def test_preview_does_not_repeat_before_you_post(kekar_app):
    """Note 5: the warning label should stand alone, not repeat the context."""
    from src.ui.listing_dialog import ListingDialog

    dialog = ListingDialog(kekar_app, Property(address="Sparse Way"))
    try:
        assert "Before you post" not in dialog.problems.text()
    finally:
        dialog.close()


def test_selected_property_row_moves_to_the_top(kekar_app):
    """Note 2: highlighting a property brings its address to the top."""
    first = kekar_app.property_repo.create(Property(
        address="Top Row Place", move_in_date="2027-05-20"))
    kekar_app.property_repo.create(Property(
        address="Lower Row Place", move_in_date="2027-01-05"))
    tab = kekar_app.main_window.calendar_tab
    tab.set_selected_property(first)
    rows = [tab.events.item(i).text()
            for i in range(tab.events.count())]
    assert rows
    assert "Top Row Place" in rows[0]
    tab.set_selected_property(None)
    rows = [tab.events.item(i).text()
            for i in range(tab.events.count())]
    assert "Lower Row Place" in rows[0]


def test_parking_and_garage_are_checkboxes(kekar_app):
    """Note 5: four explicit checkboxes replace the two combos."""
    from PyQt6.QtWidgets import QCheckBox

    form = kekar_app.main_window.property_form
    form.load_property(None)
    for name in ("driveway_box", "street_box", "garage_1_box",
                 "garage_2_box"):
        assert isinstance(getattr(form, name), QCheckBox)

    form.address_input.setText("Checkbox Way")
    form.driveway_box.setChecked(True)
    form.garage_2_box.setChecked(True)
    form.save()
    prop = kekar_app.property_repo.get(form.current_id)
    assert prop.parking_type == "Driveway"
    assert prop.garage_spaces == 2

    form.garage_1_box.setChecked(True)
    assert form.garage_2_box.isChecked() is False
    form.street_box.setChecked(True)
    assert form.driveway_box.isChecked() is False


def test_generic_parking_amenity_is_removed(kekar_app):
    """Note 4: 'Parking spot' is redundant with the new parking controls."""
    from src.data.models import Property
    from src.services.listing_compiler import amenities_line

    form = kekar_app.main_window.property_form
    assert "amenity_parking" not in form.amenity_boxes
    text = amenities_line(Property(address="No Spot Way",
                                   amenity_parking=True))
    assert "Parking spot" not in text


def test_pet_deposit_amount_round_trips_and_feeds_lease(kekar_app):
    """Note 4: the deposit is set in Rental terms and used by the lease."""
    from src.services import lease_builder

    form = kekar_app.main_window.property_form
    form.load_property(None)
    widget = form.pet_deposit_input
    assert form.rental_terms.isAncestorOf(widget)
    form.address_input.setText("Deposit Way")
    form.pet_input.setCurrentText("Yes")
    widget.setValue(425)
    form.save()
    prop = kekar_app.property_repo.get(form.current_id)
    assert prop.pet_deposit_amount == 425
    fields = lease_builder.tokens_for(prop)
    assert fields["pet_deposit"] == "425.00"
    assert "$425.00" in fields["pet_clause"]


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
