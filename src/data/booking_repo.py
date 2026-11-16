"""Reservations on a short-stay property.

A booking is a stretch of dates. Two bookings on the same property may not
overlap, and that rule lives here rather than in the UI so an import from a
portal calendar cannot walk around it.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from .models import BOOKING_SOURCES, BOOKING_STATUSES, Booking

COLUMNS = [
    "id", "property_id", "portal", "guest_name", "guest_contact",
    "check_in", "check_out", "nights", "payout", "status", "external_uid",
    "source", "notes", "created_at", "updated_at",
]

_INSERT = """
INSERT INTO bookings
 (property_id, portal, guest_name, guest_contact, check_in, check_out,
  nights, payout, status, external_uid, source, notes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE = """
UPDATE bookings SET
  property_id=?, portal=?, guest_name=?, guest_contact=?, check_in=?,
  check_out=?, nights=?, payout=?, status=?, external_uid=?, source=?,
  notes=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE id=?
"""


def _row_to_booking(row: sqlite3.Row) -> Booking:
    return Booking(
        id=row["id"], property_id=row["property_id"], portal=row["portal"],
        guest_name=row["guest_name"], guest_contact=row["guest_contact"],
        check_in=row["check_in"], check_out=row["check_out"],
        nights=row["nights"], payout=row["payout"], status=row["status"],
        external_uid=row["external_uid"], source=row["source"],
        notes=row["notes"], created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def parse_date(value: str) -> date:
    """An ISO date, or anything a portal calendar might send."""
    text = (value or "").strip()
    if text.endswith("Z"):
        text = text[:-1]
    # iCal DATE-TIME: 20261201T150000Z or 2026-12-01T15:00:00.
    for sep in ("T", " "):
        if sep in text:
            text = text.split(sep, 1)[0]
            break
    return date.fromisoformat(text[:10])


def nights_between(check_in: str, check_out: str) -> int:
    start = parse_date(check_in)
    end = parse_date(check_out)
    if end <= start:
        raise ValueError("Check-out must be after check-in.")
    return (end - start).days


class BookingRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        db = self._db
        return db.conn if hasattr(db, "conn") else db

    # -- writing -----------------------------------------------------------

    def create(self, booking: Booking) -> int:
        nights = self._checked(booking)
        cur = self.conn.execute(_INSERT, _values(booking, nights))
        return int(cur.lastrowid or 0)

    def update(self, booking: Booking) -> None:
        if booking.id is None:
            raise ValueError("cannot update a booking without an id")
        nights = self._checked(booking, exclude_id=booking.id)
        self.conn.execute(_UPDATE, _values(booking, nights) + [booking.id])

    def _checked(self, booking: Booking,
                 exclude_id: int | None = None) -> int:
        if booking.status not in BOOKING_STATUSES:
            raise ValueError(f"invalid booking status: {booking.status}")
        if booking.source not in BOOKING_SOURCES:
            raise ValueError(f"invalid booking source: {booking.source}")
        nights = nights_between(booking.check_in, booking.check_out)
        if self.overlaps(booking.property_id, booking.check_in,
                         booking.check_out, exclude_id=exclude_id):
            raise ValueError(
                f"{booking.check_in} to {booking.check_out} overlaps another "
                f"stay on this property.")
        return nights

    def delete(self, booking_id: int) -> None:
        self.conn.execute("DELETE FROM bookings WHERE id=?", (booking_id,))

    # -- reading -----------------------------------------------------------

    def get(self, booking_id: int) -> Booking | None:
        row = self.conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM bookings WHERE id=?",
            (booking_id,)).fetchone()
        return _row_to_booking(row) if row else None

    def list(self, property_id: int | None = None,
             status: str | None = None) -> list[Booking]:
        sql = f"SELECT {', '.join(COLUMNS)} FROM bookings"
        clauses: list[str] = []
        params: list = []
        if property_id is not None:
            clauses.append("property_id=?")
            params.append(property_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY check_in DESC, id DESC"
        return [_row_to_booking(r) for r in self.conn.execute(sql, params)]

    def by_uid(self, property_id: int, external_uid: str) -> Booking | None:
        row = self.conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM bookings "
            f"WHERE property_id=? AND external_uid=?",
            (property_id, external_uid)).fetchone()
        return _row_to_booking(row) if row else None

    def overlaps(self, property_id: int | None, check_in: str, check_out: str,
                 exclude_id: int | None = None) -> bool:
        """True when a live booking already covers any of these dates.

        A cancelled booking frees its dates, so it is ignored.
        """
        if property_id is None:
            return False
        sql = ("SELECT id, check_in, check_out FROM bookings "
               "WHERE property_id=? AND status!='cancelled'")
        params: list = [property_id]
        if exclude_id is not None:
            sql += " AND id!=?"
            params.append(exclude_id)
        start = parse_date(check_in)
        end = parse_date(check_out)
        for row in self.conn.execute(sql, params):
            other_start = parse_date(row["check_in"])
            other_end = parse_date(row["check_out"])
            if start < other_end and end > other_start:
                return True
        return False

    def booked_dates(self, property_id: int,
                     status: str | None = None) -> dict[date, Booking]:
        """Every date covered by a booking, for painting a calendar."""
        result: dict[date, Booking] = {}
        for booking in self.list(property_id=property_id, status=status):
            try:
                start = parse_date(booking.check_in)
                end = parse_date(booking.check_out)
            except ValueError:
                continue
            day = start
            while day < end:
                result.setdefault(day, booking)
                day = date.fromordinal(day.toordinal() + 1)
        return result


def _values(booking: Booking, nights: int) -> list:
    return [
        booking.property_id, booking.portal, booking.guest_name,
        booking.guest_contact, booking.check_in, booking.check_out, nights,
        booking.payout, booking.status, booking.external_uid, booking.source,
        booking.notes,
    ]
