"""Regressions for the client's testing notes (Lite/production build)."""
from src.data.models import Property
from src.ui.main_window import MainWindow


def _close_window(kekar_app, window):
    try:
        kekar_app.data_changed.disconnect(window.reload_all)
    except (TypeError, RuntimeError):
        pass
    window.close()


def test_lease_property_selector_is_populated_at_startup(kekar_app):
    """Note 1: Lease > Property must list the properties already in data."""
    kekar_app.property_repo.create(Property(address="99 Lease Lane"))
    window = MainWindow(kekar_app)
    try:
        labels = [window.lease_tab.property_combo.itemText(i)
                  for i in range(window.lease_tab.property_combo.count())]
        assert any("99 Lease Lane" in label for label in labels)
    finally:
        _close_window(kekar_app, window)


def test_applicant_property_cell_is_a_populated_combo(kekar_app):
    """Note 2: Applicants > Property lists the live properties."""
    pid = kekar_app.property_repo.create(Property(address="55 Applicant Way"))
    kekar_app.applicant_repo.create(
        __import__("src.data.models", fromlist=["Applicant"]).Applicant(
            applicant_name="Test Person", property_id=pid))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    combo = tab.table.cellWidget(0, 1)
    assert combo is not None
    labels = [combo.itemText(i) for i in range(combo.count())]
    assert any("55 Applicant Way" in label for label in labels)
    assert combo.currentData() == pid


def test_applicant_property_combo_saves_the_new_link(kekar_app):
    from src.data.models import Applicant

    first = kekar_app.property_repo.create(Property(address="First Rental"))
    second = kekar_app.property_repo.create(Property(address="Second Rental"))
    aid = kekar_app.applicant_repo.create(
        Applicant(applicant_name="Mover", property_id=first))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    combo = tab.table.cellWidget(0, 1)
    index = combo.findData(second)
    combo.setCurrentIndex(index)
    assert kekar_app.applicant_repo.get(aid).property_id == second


def test_garage_and_parking_round_trip(kekar_app):
    """Note 3: new amenity fields survive a repository write/read."""
    pid = kekar_app.property_repo.create(Property(
        address="21 Garage Way", garage_spaces=2,
        parking_type="Driveway"))
    saved = kekar_app.property_repo.get(pid)
    assert saved.garage_spaces == 2
    assert saved.parking_type == "Driveway"


def test_property_form_edits_garage_and_parking(kekar_app):
    form = kekar_app.main_window.property_form
    form.load_property(None)
    form.address_input.setText("22 Garage Way")
    form.garage_combo.setCurrentIndex(2)
    form.parking_combo.setCurrentText("Street parking")
    form.save()
    saved = kekar_app.property_repo.get(form.current_id)
    assert saved.garage_spaces == 2
    assert saved.parking_type == "Street parking"


def test_listing_mentions_garage_and_parking():
    from src.services.listing_compiler import amenities_line

    text = amenities_line(Property(
        address="23 Garage Way", garage_spaces=1,
        parking_type="Driveway"))
    assert "Garage: 1 car" in text
    assert "Parking: Driveway" in text


def test_lease_tokens_include_pet_deposit_when_pets_allowed():
    """Note 4: a yes-to-pets lease has a pet-deposit place and amount."""
    from src.services import lease_builder

    fields = lease_builder.tokens_for(
        Property(address="31 Pet Lane", pet_policy="Cats OK"))
    assert fields["pet_deposit"] == "300.00"
    assert "refundable pet deposit" in fields["pet_clause"]


def test_lease_tokens_omit_pet_deposit_when_no_pets():
    from src.services import lease_builder

    fields = lease_builder.tokens_for(
        Property(address="32 No Pets Lane", pet_policy="No pets"))
    assert fields["pet_deposit"] == "0.00"
    assert fields["pet_clause"] == ""


def test_default_lease_mentions_pet_deposit():
    from src.services import lease_builder

    fields = lease_builder.tokens_for(
        Property(address="33 Pet Lane", pet_policy="Dogs OK"))
    text = lease_builder.render(lease_builder.DEFAULT_TEMPLATE, fields)
    assert "$300.00" in text
    assert "Pet policy: Dogs OK" in text


def test_single_click_opens_an_editable_applicant_profile(kekar_app):
    """Note 11: one click shows the full applicant record for editing."""
    from src.data.models import Applicant

    aid = kekar_app.applicant_repo.create(Applicant(
        applicant_name="Hope Winters", contact_info="hope@example.com",
        notes="Called on Tuesday"))
    tab = kekar_app.main_window.crm_tab
    tab.reload()
    tab.table.cellClicked.emit(0, 0)
    assert tab.profile.isHidden() is False
    assert tab.profile_name.text() == "Hope Winters"
    assert tab.profile_contact.text() == "hope@example.com"
    tab.profile_name.setText("Hope W.")
    tab.profile_notes.setPlainText("Follow up Friday")
    tab.profile_save.click()
    saved = kekar_app.applicant_repo.get(aid)
    assert saved.applicant_name == "Hope W."
    assert saved.notes == "Follow up Friday"


def test_clicking_a_calendar_date_names_its_property(kekar_app):
    """Note 10: a highlighted date tells the user which property it means."""
    from PyQt6.QtCore import QDate

    kekar_app.property_repo.create(Property(
        address="70 Dated Court", move_in_date="2026-12-20"))
    window = kekar_app.main_window
    window.calendar_tab.reload()
    window.calendar_tab.calendar.setSelectedDate(QDate(2026, 12, 20))
    assert "70 Dated Court" in window.calendar_tab.date_detail.text()
    assert "Move-in" in window.calendar_tab.date_detail.text()


def test_calendar_shows_move_in_and_out_on_one_line(kekar_app):
    """Note 9: one address line carries both move dates."""
    kekar_app.property_repo.create(Property(
        address="60 Both Dates Way", move_in_date="2026-12-01",
        move_out_date="2026-12-31"))
    window = kekar_app.main_window
    window.calendar_tab.reload()
    lines = [window.calendar_tab.events.item(i).text()
             for i in range(window.calendar_tab.events.count())]
    matches = [line for line in lines if "60 Both Dates Way" in line]
    assert len(matches) == 1
    assert "2026-12-01" in matches[0]
    assert "2026-12-31" in matches[0]


def test_selecting_a_property_marks_its_calendar_dates(kekar_app):
    """Note 8: the selected property is emphasised on the calendar."""
    from PyQt6.QtCore import QDate

    first = kekar_app.property_repo.create(
        Property(address="51 Chosen Road", move_in_date="2026-12-15"))
    second = kekar_app.property_repo.create(
        Property(address="52 Other Road", move_in_date="2026-12-16"))
    window = kekar_app.main_window
    window.drawer.reload()
    window.drawer.property_selected.emit(first)
    fmt_first = window.calendar_tab.calendar.dateTextFormat(
        QDate(2026, 12, 15))
    fmt_second = window.calendar_tab.calendar.dateTextFormat(
        QDate(2026, 12, 16))
    assert fmt_first.fontWeight() >= 700
    assert fmt_second.fontWeight() < 700
    assert "51 Chosen Road" in window.calendar_tab.summary.text()
    assert second is not None


def test_stays_are_inside_the_calendar_tab(kekar_app):
    """Note 7: Stays is a panel inside Calendar, not a separate tab."""
    from src.ui.calendar_tab import SHORT_STAY_COLOUR

    window = kekar_app.main_window
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert "Stays" not in labels
    assert "Calendar" in labels
    assert window.calendar_tab.isAncestorOf(window.stays_tab)


def test_calendar_marks_short_stays_in_their_own_colour(kekar_app):
    from PyQt6.QtGui import QColor
    from src.data.models import Booking
    from src.ui.calendar_tab import SHORT_STAY_COLOUR

    prop_id = kekar_app.property_repo.create(Property(address="44 Stay Lane"))
    kekar_app.booking_repo.create(Booking(
        property_id=prop_id, guest_name="Ann", check_in="2026-12-10",
        check_out="2026-12-12"))
    window = kekar_app.main_window
    window.calendar_tab.reload()
    day = __import__("PyQt6.QtCore", fromlist=["QDate"]).QDate(2026, 12, 10)
    fmt = window.calendar_tab.calendar.dateTextFormat(day)
    assert QColor(SHORT_STAY_COLOUR) == fmt.background().color()
    assert any("Ann" in window.calendar_tab.events.item(i).text()
               for i in range(window.calendar_tab.events.count()))


def test_help_has_a_calendar_legend(kekar_app):
    legend = next((a for a in kekar_app.main_window.help_menu.actions()
                   if a.text() and "legend" in a.text().lower()), None)
    assert legend is not None, "Help needs a calendar legend"


def test_lite_sidebar_toggle_is_labelled(kekar_app):
    """Note 6: the property panel toggle must be marked in the Lite build."""
    window = kekar_app.main_window
    assert window.sidebar_toggle.text()
    assert window.sidebar_toggle.toolTip()
    assert window.sidebar_toggle.isHidden() is False


def test_dark_themes_have_no_dark_form_labels(kekar_app):
    """Note 5: muted labels must follow the dark/OLED palette."""
    from PyQt6.QtWidgets import QLabel
    from src.ui.palette import DARK, OLED

    form = kekar_app.main_window.property_form
    for theme in (DARK, OLED):
        kekar_app.apply_theme(theme.key)
        labels = [w for w in form.findChildren(QLabel)
                  if w.property("muted") is True]
        assert labels
        for label in labels:
            assert theme.text_secondary in label.styleSheet()
            assert "#4a453e" not in label.styleSheet()


def test_dark_themes_set_placeholder_text_colour(kekar_app):
    from PyQt6.QtGui import QPalette
    from PyQt6.QtWidgets import QApplication
    from src.ui.palette import DARK, OLED

    for theme in (DARK, OLED):
        kekar_app.apply_theme(theme.key)
        palette = QApplication.palette()
        assert palette.color(QPalette.ColorRole.PlaceholderText).name() \
            == theme.text_secondary


def test_lease_property_selector_refreshes_after_save(kekar_app):
    window = MainWindow(kekar_app)
    try:
        before = window.lease_tab.property_combo.count()
        kekar_app.property_repo.create(Property(address="100 New Lane"))
        window._on_property_saved(
            kekar_app.property_repo.list()[-1].id)
        labels = [window.lease_tab.property_combo.itemText(i)
                  for i in range(window.lease_tab.property_combo.count())]
        assert len(labels) == before + 1
        assert any("100 New Lane" in label for label in labels)
    finally:
        _close_window(kekar_app, window)
