"""Short-stay (Airbnb) properties: kind, listings, bookings, portal sync."""
import sqlite3

import pytest

from src.data._schema_embedded import embedded_schema
from src.data.booking_repo import BookingRepo, nights_between
from src.data.db import Database
from src.data.models import (PORTALS, Booking, PortalSettings, Property)
from src.data.portal_repo import PortalRepo
from src.data.property_repo import PropertyRepo
from src.services import ical_service, portal_sync
from src.services.listing_channels import (channel_kind, compile_channel,
                                           known_channels)
from src.services.listing_compiler import compile_listing


def _short_stay(**kw) -> Property:
    base = dict(address="1 Airbnb Way", city="Pawhuska", zip_code="74056",
                bedrooms=2, bathrooms=1.0, sqft=800, status="Vacant",
                kind="short_stay", nightly_price=120.0, cleaning_fee=45.0,
                extra_guest_fee=15.0, min_stay_nights=2, max_guests=6,
                check_in_time="15:00", check_out_time="11:00",
                instant_book=True, cancellation_policy="Flexible",
                house_rules="No parties.")
    base.update(kw)
    return Property(**base)


# -- schema ---------------------------------------------------------------

def test_migration_adds_short_stay_columns(tmp_path):
    """A database created before the feature gains the columns, not a reset."""
    path = tmp_path / "old.db"
    # The shape a v1.1 install would have: every rental column, none of the
    # short-stay ones.
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE properties ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT NOT NULL,"
        " city TEXT, zip_code TEXT, rent_price REAL, deposit_amount REAL,"
        " available_date TEXT, bedrooms INTEGER, bathrooms REAL, sqft INTEGER,"
        " pet_policy TEXT, status TEXT NOT NULL DEFAULT 'Vacant',"
        " amenity_wd INTEGER NOT NULL DEFAULT 0,"
        " amenity_ac INTEGER NOT NULL DEFAULT 0,"
        " amenity_yard INTEGER NOT NULL DEFAULT 0,"
        " amenity_dishwasher INTEGER NOT NULL DEFAULT 0,"
        " amenity_parking INTEGER NOT NULL DEFAULT 0,"
        " notes TEXT,"
        " created_at TEXT, updated_at TEXT)")
    conn.execute("INSERT INTO properties (address) VALUES ('1 Old Way')")
    conn.commit()
    conn.close()

    db = Database(path)
    columns = {row["name"]
               for row in db.conn.execute("PRAGMA table_info(properties)")}
    assert {"kind", "nightly_price", "cleaning_fee", "min_stay_nights",
            "max_guests", "instant_book", "house_rules"} <= columns
    # The existing row keeps working and reads as a long-term rental.
    prop = PropertyRepo(db).get(1)
    assert prop.kind == "rental"
    assert prop.nightly_price is None
    db.close()


def test_kind_defaults_to_rental(db):
    repo = PropertyRepo(db)
    prop_id = repo.create(Property(address="1 Plain Way"))
    assert repo.get(prop_id).kind == "rental"
    assert [p.address for p in repo.list(kind="short_stay")] == []


def test_kind_round_trips(db):
    repo = PropertyRepo(db)
    prop_id = repo.create(_short_stay())
    got = repo.get(prop_id)
    assert got.kind == "short_stay"
    assert got.nightly_price == 120.0
    assert got.cleaning_fee == 45.0
    assert got.extra_guest_fee == 15.0
    assert got.min_stay_nights == 2
    assert got.max_guests == 6
    assert got.check_in_time == "15:00"
    assert got.check_out_time == "11:00"
    assert got.instant_book is True
    assert got.cancellation_policy == "Flexible"
    assert got.house_rules == "No parties."
    assert [p.address for p in repo.list(kind="short_stay")] == ["1 Airbnb Way"]


# -- listings -------------------------------------------------------------

def test_short_stay_channels_are_marked():
    assert known_channels("short_stay") == ["airbnb", "booking_com", "vrbo"]
    assert known_channels("rental") == [
        "apartments_com", "facebook_marketplace", "zillow"]
    assert channel_kind("airbnb") == "short_stay"
    assert channel_kind("zillow") == "rental"


def test_airbnb_package_uses_nightly_terms():
    package = compile_channel(_short_stay(), "airbnb")
    assert "$120" in package.title
    assert "Cleaning fee $45" in package.body
    assert "2 night minimum" in package.body
    assert "Up to 6 guests" in package.body
    assert "No parties." in package.body
    fields = dict(package.fields)
    assert fields["Nightly rate"] == "120"
    assert fields["Minimum stay (nights)"] == "2"
    assert fields["Max guests"] == "6"
    assert package.warnings == [
        "Airbnb has no posting API, so this is a copy-and-paste package; "
        "posting stays with you.",
        "Airbnb titles are short — the preview warns when this one runs long.",
    ]


def test_short_stay_channel_warns_when_the_price_is_missing():
    package = compile_channel(_short_stay(nightly_price=None), "vrbo")
    assert any("nightly rate" in warning for warning in package.warnings)


def test_portal_overrides_feed_the_package():
    """A portal's price/min-stay override replaces the property's own value."""
    package = compile_channel(_short_stay(), "airbnb", price_override=140.0,
                              min_stay_override=3)
    assert "$140" in package.title
    assert "3 night minimum" in package.body
    fields = dict(package.fields)
    assert fields["Nightly rate"] == "140"
    assert fields["Minimum stay (nights)"] == "3"


def test_override_of_zero_means_no_override():
    """The Portals group stores 0 for "use the property's value"."""
    package = compile_channel(_short_stay(), "vrbo", price_override=0,
                              min_stay_override=0)
    assert "$120" in package.title
    assert "Minimum stay: 2 nights" in package.body


def test_override_suppresses_the_missing_price_warning():
    package = compile_channel(_short_stay(nightly_price=None), "airbnb",
                              price_override=140.0)
    assert not any("nightly rate" in warning for warning in package.warnings)


def test_generic_listing_follows_the_kind():
    rental = compile_listing(Property(address="1 Rental Way", city="Pawhuska",
                                      rent_price=900.0, bedrooms=2))
    short = compile_listing(_short_stay())
    assert "/month" in rental
    assert "/night" in short
    assert "Cleaning fee" in short
    assert "Message me to book." in short


# -- bookings -------------------------------------------------------------

def test_nights_between_rejects_a_backwards_stay():
    assert nights_between("2026-12-01", "2026-12-04") == 3
    with pytest.raises(ValueError):
        nights_between("2026-12-04", "2026-12-01")


def test_booking_round_trip_and_overlap(db):
    repo = BookingRepo(db)
    prop_id = PropertyRepo(db).create(_short_stay())
    booking_id = repo.create(Booking(
        property_id=prop_id, guest_name="Jordan Lee", portal="airbnb",
        check_in="2026-12-01", check_out="2026-12-04", payout=405.0))
    got = repo.get(booking_id)
    assert got.nights == 3
    assert got.status == "confirmed"
    assert got.source == "manual"

    with pytest.raises(ValueError, match="overlaps"):
        repo.create(Booking(property_id=prop_id, guest_name="Sam",
                            check_in="2026-12-03", check_out="2026-12-05"))

    # A cancelled stay frees its dates.
    got.status = "cancelled"
    repo.update(got)
    repo.create(Booking(property_id=prop_id, guest_name="Sam",
                        check_in="2026-12-03", check_out="2026-12-05"))

    # Another property is unaffected.
    other = PropertyRepo(db).create(_short_stay(address="2 Airbnb Way"))
    repo.create(Booking(property_id=other, check_in="2026-12-03",
                        check_out="2026-12-05"))


def test_booked_dates_cover_every_night(db):
    repo = BookingRepo(db)
    prop_id = PropertyRepo(db).create(_short_stay())
    repo.create(Booking(property_id=prop_id, check_in="2026-12-01",
                        check_out="2026-12-04"))
    days = repo.booked_dates(prop_id)
    assert len(days) == 3
    from datetime import date
    assert date(2026, 12, 1) in days
    assert date(2026, 12, 3) in days
    assert date(2026, 12, 4) not in days


# -- iCal -----------------------------------------------------------------

def test_ical_round_trip():
    prop = Property(id=1, address="1 Airbnb Way")
    bookings = [
        Booking(property_id=1, guest_name="Jordan Lee", check_in="2026-12-01",
                check_out="2026-12-04", payout=405.0, portal="airbnb"),
        Booking(property_id=1, status="blocked", check_in="2026-12-10",
                check_out="2026-12-12"),
    ]
    events = ical_service.parse_ical(ical_service.build_ical(prop, bookings))
    assert len(events) == 2
    first = next(e for e in events if e["guest_name"] == "Jordan Lee")
    assert first["check_in"] == "2026-12-01"
    assert first["check_out"] == "2026-12-04"
    assert first["status"] == "confirmed"
    blocked = next(e for e in events if e["status"] == "blocked")
    assert blocked["guest_name"] == ""


def test_ical_unfolds_long_lines():
    calendar = (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:long-line@example\r\n"
        "DTSTART;VALUE=DATE:20261201\r\n"
        "DTEND;VALUE=DATE:20261202\r\n"
        "SUMMARY:A guest with a very long name that has to be f\r\n"
        " olded over several lines\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n")
    events = ical_service.parse_ical(calendar)
    assert events[0]["guest_name"] == (
        "A guest with a very long name that has to be folded over several lines")


def test_ical_skips_events_without_dates():
    calendar = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:x\r\n"
                "SUMMARY:No dates\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    assert ical_service.parse_ical(calendar) == []


# -- portals and sync -----------------------------------------------------

def test_portal_settings_round_trip(db):
    repo = PortalRepo(db)
    prop_id = PropertyRepo(db).create(_short_stay())
    repo.save(PortalSettings(property_id=prop_id, portal="airbnb",
                             enabled=True, price_override=140.0,
                             min_stay_override=3,
                             external_ical_url="https://example/cal.ics"))
    got = repo.get(prop_id, "airbnb")
    assert got.enabled is True
    assert got.price_override == 140.0
    assert got.min_stay_override == 3
    assert repo.get(prop_id, "vrbo") is None


CALENDAR = (
    "BEGIN:VCALENDAR\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:abc123@airbnb.com\r\n"
    "DTSTART;VALUE=DATE:20261201\r\n"
    "DTEND;VALUE=DATE:20261204\r\n"
    "SUMMARY:Jordan Lee\r\n"
    "STATUS:CONFIRMED\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n")


def test_sync_imports_once_then_reports_unchanged(db, monkeypatch):
    prop_id = PropertyRepo(db).create(_short_stay())
    PortalRepo(db).save(PortalSettings(
        property_id=prop_id, portal="airbnb", enabled=True,
        external_ical_url="https://example/cal.ics"))
    monkeypatch.setattr(ical_service, "fetch_ical",
                        lambda url, timeout=20: CALENDAR)

    prop = PropertyRepo(db).get(prop_id)
    first = portal_sync.sync_portal(db, prop, "airbnb")
    assert first["status"] == "ok"
    assert first["added"] == 1

    second = portal_sync.sync_portal(db, prop, "airbnb")
    assert second["added"] == 0
    assert second["status"] == "unchanged"

    bookings = BookingRepo(db).list(property_id=prop_id)
    assert len(bookings) == 1
    assert bookings[0].external_uid == "abc123@airbnb.com"
    assert bookings[0].source == "ical"
    assert bookings[0].nights == 3


def test_sync_without_a_url_fails_cleanly(db):
    prop_id = PropertyRepo(db).create(_short_stay())
    prop = PropertyRepo(db).get(prop_id)
    result = portal_sync.sync_portal(db, prop, "vrbo")
    assert result["status"] == "failed"
    assert "calendar URL" in result["detail"]


def test_sync_records_the_attempt(db, monkeypatch):
    prop_id = PropertyRepo(db).create(_short_stay())
    PortalRepo(db).save(PortalSettings(
        property_id=prop_id, portal="airbnb", enabled=True,
        external_ical_url="https://example/cal.ics"))
    monkeypatch.setattr(ical_service, "fetch_ical",
                        lambda url, timeout=20: CALENDAR)
    prop = PropertyRepo(db).get(prop_id)
    portal_sync.sync_portal(db, prop, "airbnb")
    rows = PortalRepo(db).recent_syncs()
    assert rows[0]["portal"] == "airbnb"
    assert rows[0]["result"] == "ok"


def test_export_ical_writes_a_file(db, tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path))
    prop_id = PropertyRepo(db).create(_short_stay())
    BookingRepo(db).create(Booking(property_id=prop_id,
                                   check_in="2026-12-01",
                                   check_out="2026-12-03",
                                   guest_name="Jordan Lee"))
    path = ical_service.export_ical(PropertyRepo(db).get(prop_id),
                                    BookingRepo(db).list(property_id=prop_id))
    assert path.exists()
    assert "BEGIN:VCALENDAR" in path.read_text(encoding="utf-8")


# -- GUI ------------------------------------------------------------------

def test_kind_selector_switches_term_groups(kekar_app):
    form = kekar_app.main_window.property_form
    assert not form.rental_terms.isHidden()
    assert form.short_stay_terms.isHidden()
    assert form.portals_box.isHidden()

    index = form.kind_combo.findData("short_stay")
    form.kind_combo.setCurrentIndex(index)
    assert form.rental_terms.isHidden()
    assert not form.short_stay_terms.isHidden()
    assert not form.portals_box.isHidden()


def test_stays_tab_shows_a_booking(kekar_app):
    window = kekar_app.main_window
    prop_id = kekar_app.property_repo.create(_short_stay())
    kekar_app.booking_repo.create(Booking(
        property_id=prop_id, guest_name="Jordan Lee", portal="airbnb",
        check_in="2026-12-01", check_out="2026-12-04", payout=405.0))
    window.stays_tab.reload()
    assert window.stays_tab.table.rowCount() == 1
    assert window.stays_tab.table.item(0, 0).text() == "Jordan Lee"
    assert window.stays_tab.table.item(0, 1).text() == "Airbnb"


def test_portals_are_known():
    assert PORTALS == ("airbnb", "vrbo", "booking_com")


def test_listing_dialog_applies_the_portal_override(kekar_app):
    from src.ui.listing_dialog import ListingDialog

    prop_id = kekar_app.property_repo.create(_short_stay())
    kekar_app.portal_repo.save(PortalSettings(
        property_id=prop_id, portal="airbnb", enabled=True,
        price_override=140.0, min_stay_override=3))
    dlg = ListingDialog(kekar_app, kekar_app.property_repo.get(prop_id))
    dlg.channel.setCurrentIndex(dlg.channel.findData("airbnb"))
    assert "$140" in dlg.text.toPlainText()
    assert "3 night minimum" in dlg.text.toPlainText()
    assert "override" in dlg.override_note.text()


def test_short_stay_action_button_opens_the_portal_listing(kekar_app,
                                                           monkeypatch):
    captured: dict = {}

    class FakeDialog:
        def __init__(self, app, prop, parent=None):
            captured["prop"] = prop

        def exec(self):
            captured["shown"] = True

    monkeypatch.setattr("src.ui.property_form.ListingDialog", FakeDialog)
    form = kekar_app.main_window.property_form
    prop_id = kekar_app.property_repo.create(_short_stay())
    form.load_property(prop_id)
    assert form.publish_btn.text() == "Portal listing…"
    form._publish_or_list()
    assert captured.get("shown") is True
    assert captured["prop"].id == prop_id


def test_rental_action_button_says_marketplace(kekar_app):
    form = kekar_app.main_window.property_form
    prop_id = kekar_app.property_repo.create(
        Property(address="1 Rental Way", rent_price=900.0))
    form.load_property(prop_id)
    assert form.publish_btn.text() == "Publish to Marketplace..."


def test_saving_a_rental_writes_no_portal_rows(kekar_app):
    form = kekar_app.main_window.property_form
    prop_id = kekar_app.property_repo.create(
        Property(address="1 Rental Way", rent_price=900.0))
    form.load_property(prop_id)
    form._save_portals(kekar_app.property_repo.get(prop_id))
    assert kekar_app.portal_repo.list_for_property(prop_id) == []
