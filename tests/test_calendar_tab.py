"""Calendar tab: move-in and move-out dates come from saved properties."""
from src.data.models import Property


def test_property_keeps_move_dates(kekar_app):
    pid = kekar_app.property_repo.create(Property(
        address="1 Calendar Way", move_in_date="2026-12-01",
        move_out_date="2027-11-30"))
    saved = kekar_app.property_repo.get(pid)
    assert saved.move_in_date == "2026-12-01"
    assert saved.move_out_date == "2027-11-30"


def test_calendar_tab_lists_move_dates(kekar_app):
    from src.ui.calendar_tab import CalendarTab

    kekar_app.property_repo.create(Property(
        address="2 Calendar Way", move_in_date="2026-12-05",
        move_out_date="2027-12-05"))
    tab = CalendarTab(kekar_app)
    tab.reload()
    rows = [tab.events.item(i).text() for i in range(tab.events.count())]
    assert any("Move-in" in row and "2 Calendar Way" in row
               and "2026-12-05" in row for row in rows)
    assert any("Move-out" in row and "2 Calendar Way" in row
               and "2027-12-05" in row for row in rows)


def test_saving_a_property_refreshes_the_calendar(kekar_app):
    form = kekar_app.main_window.property_form
    form.load_property(None)
    form.address_input.setText("8 Save Way")
    form.move_in_input.setText("2026-01-15")
    form.save()
    tab = kekar_app.main_window.calendar_tab
    rows = [tab.events.item(i).text() for i in range(tab.events.count())]
    assert any("Move-in" in row and "8 Save Way" in row for row in rows)


def test_calendar_tab_ignores_invalid_dates(kekar_app):
    from src.ui.calendar_tab import CalendarTab

    kekar_app.property_repo.create(Property(
        address="3 Calendar Way", move_in_date="not-a-date"))
    tab = CalendarTab(kekar_app)
    tab.reload()
    assert tab.events.count() == 0
