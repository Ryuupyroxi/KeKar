"""iCal export and import for short-stay portal calendars.

Airbnb, Vrbo and Booking.com all export a calendar URL and accept an imported
one, which is the only two-way channel they offer without a partner agreement.
This module is deliberately self-contained: it parses and writes RFC 5545 by
hand so no third-party dependency is needed in the frozen build.
"""
from __future__ import annotations

import re
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..data.booking_repo import parse_date
from ..data.models import Booking, Property
from ..paths import calendar_dir

PRODID = "-//KeKar//Short Stay//EN"
FOLD_AT = 74


def _fold(line: str) -> str:
    """Fold a long line the way RFC 5545 requires (CRLF + one leading space)."""
    encoded = line.encode("utf-8")
    parts: list[str] = []
    while len(encoded) > FOLD_AT:
        cut = FOLD_AT
        # Never split a multi-byte character.
        while cut > 0 and (encoded[cut] & 0xC0) == 0x80:
            cut -= 1
        parts.append(encoded[:cut].decode("utf-8"))
        encoded = b" " + encoded[cut:]
    parts.append(encoded.decode("utf-8"))
    return "\r\n".join(parts)


def _escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ical(prop: Property, bookings: list[Booking]) -> str:
    """A whole-property calendar. Cancelled bookings are left out."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(prop.address)}",
    ]
    for booking in bookings:
        if booking.status == "cancelled":
            continue
        start = parse_date(booking.check_in)
        end = parse_date(booking.check_out)
        summary = ("Blocked" if booking.status == "blocked"
                   else f"Booked: {booking.guest_name or 'guest'}")
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{booking.id or booking.external_uid or id(booking)}"
                     f"-{prop.id}@kekar.local")
        lines.append(f"DTSTAMP:{_stamp()}")
        lines.append(f"DTSTART;VALUE=DATE:{start:%Y%m%d}")
        lines.append(f"DTEND;VALUE=DATE:{end:%Y%m%d}")
        lines.append(f"SUMMARY:{_escape(summary)}")
        detail = f"Portal: {booking.portal or 'direct'}; " \
                 f"status: {booking.status}"
        if booking.payout:
            detail += f"; payout: {booking.payout:.2f}"
        if booking.guest_contact:
            detail += f"; contact: {booking.guest_contact}"
        if booking.notes:
            detail += f"; notes: {booking.notes}"
        lines.append(f"DESCRIPTION:{_escape(detail)}")
        lines.append("STATUS:CONFIRMED")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def _unfold(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines: list[str] = []
    for line in raw:
        if line.startswith(" ") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _iso_date(value: str) -> str | None:
    match = re.match(r"^(\d{4})(\d{2})(\d{2})", value.strip())
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def _event(raw: dict[str, str], summary: str, description: str,
           uid: str, status: str) -> dict | None:
    start = _iso_date(raw.get("DTSTART", ""))
    if start is None:
        return None
    end_value = raw.get("DTEND", "")
    end = _iso_date(end_value) if end_value else None
    try:
        end_date = parse_date(end) if end else parse_date(start)
        if end_date <= parse_date(start):
            end_date = parse_date(start) + timedelta(days=1)
    except ValueError:
        return None
    if status == "CANCELLED":
        booking_status = "cancelled"
    elif "BLOCK" in summary.upper():
        booking_status = "blocked"
    else:
        booking_status = "confirmed"
    name = summary
    if name.startswith("Booked: "):
        name = name[len("Booked: "):]
    if booking_status == "blocked":
        name = ""
    return {
        "external_uid": uid or None,
        "check_in": start,
        "check_out": end_date.isoformat(),
        "guest_name": name,
        "status": booking_status,
        "description": description,
    }


def parse_ical(text: str) -> list[dict]:
    """Every usable VEVENT in a calendar, as booking-shaped dicts."""
    events: list[dict] = []
    raw: dict[str, str] = {}
    summary = description = uid = ""
    status = "CONFIRMED"
    inside = False
    for line in _unfold(text):
        if line.strip() == "BEGIN:VEVENT":
            inside, raw, summary, description, uid = True, {}, "", "", ""
            status = "CONFIRMED"
            continue
        if line.strip() == "END:VEVENT":
            if inside:
                event = _event(raw, summary, description, uid, status)
                if event is not None:
                    events.append(event)
            inside = False
            continue
        if not inside or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.split(";")[0].strip().upper()
        raw[key] = value
        if key == "SUMMARY":
            summary = value
        elif key == "DESCRIPTION":
            description = value
        elif key == "UID":
            uid = value
        elif key == "STATUS":
            status = value.strip().upper()
    return events


def fetch_ical(url: str, timeout: int = 20) -> str:
    """Download a portal's calendar. Raises on any network failure."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "KeKar-calendar/1.2"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def ical_filename(prop: Property) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (prop.address or "property").lower())
    return f"{slug.strip('-') or 'property'}.ics"


def export_ical(prop: Property, bookings: list[Booking]) -> Path:
    """Write the property's calendar into KeKarData/calendar/."""
    directory = calendar_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ical_filename(prop)
    path.write_text(build_ical(prop, bookings), encoding="utf-8")
    return path


def calendar_window(events: list[dict]) -> tuple[date, date] | None:
    """The first and last date covered by a set of events, for tests/UI."""
    dates: list[date] = []
    for event in events:
        try:
            dates.append(parse_date(event["check_in"]))
            dates.append(parse_date(event["check_out"]))
        except ValueError:
            continue
    if not dates:
        return None
    return min(dates), max(dates)
