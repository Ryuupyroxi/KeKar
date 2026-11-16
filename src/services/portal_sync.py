"""Two-way calendar sync between KeKar and a short-stay portal.

The portals have no posting API, so the calendar is the channel: import the
portal's iCal URL into KeKar's bookings, and export KeKar's bookings as an
iCal file the host uploads to the portal. Every attempt is logged.
"""
from __future__ import annotations

from ..data.booking_repo import BookingRepo
from ..data.models import PORTAL_LABELS, PORTALS, Booking, Property
from ..data.portal_repo import PortalRepo
from . import ical_service


def _empty(result: str, detail: str) -> dict:
    return {"status": result, "added": 0, "updated": 0, "skipped": 0,
            "total": 0, "detail": detail}


def sync_portal(db, prop: Property, portal: str,
                booking_repo: BookingRepo | None = None,
                portal_repo: PortalRepo | None = None) -> dict:
    """Import one portal's calendar for one property.

    Never raises for a network or parse problem: the failure is written to
    the sync log and returned, so the UI can show it.
    """
    if prop.id is None:
        return _empty("failed", "Save the property before syncing.")
    if portal not in PORTALS:
        return _empty("failed", f"Unknown portal: {portal}")
    bookings = booking_repo or BookingRepo(db)
    portals = portal_repo or PortalRepo(db)
    label = PORTAL_LABELS.get(portal, portal)

    settings = portals.get(prop.id, portal)
    url = (settings.external_ical_url if settings else None) or ""
    if not url:
        detail = f"No {label} calendar URL is set for this property."
        portals.log(prop.id, portal, "failed", detail)
        return _empty("failed", detail)

    try:
        text = ical_service.fetch_ical(url)
    except Exception as exc:
        detail = f"Could not fetch the {label} calendar: {exc}"
        portals.log(prop.id, portal, "failed", detail)
        return _empty("failed", detail)

    events = ical_service.parse_ical(text)
    added = updated = skipped = 0
    for event in events:
        uid = event.get("external_uid")
        if not uid:
            skipped += 1
            continue
        existing = bookings.by_uid(prop.id, uid)
        try:
            if existing is None:
                bookings.create(Booking(
                    property_id=prop.id, portal=portal,
                    guest_name=event["guest_name"],
                    check_in=event["check_in"], check_out=event["check_out"],
                    status=event["status"], external_uid=uid, source="ical"))
                added += 1
                continue
            changed = (existing.guest_name != event["guest_name"]
                       or existing.check_in != event["check_in"]
                       or existing.check_out != event["check_out"]
                       or existing.status != event["status"])
            existing.portal = portal
            existing.guest_name = event["guest_name"]
            existing.check_in = event["check_in"]
            existing.check_out = event["check_out"]
            existing.status = event["status"]
            bookings.update(existing)
            if changed:
                updated += 1
            else:
                skipped += 1
        except ValueError:
            # An event that overlaps a manual stay, or carries bad dates, is
            # skipped rather than aborting the whole import.
            skipped += 1

    result = "ok" if (added or updated) else "unchanged"
    detail = (f"{added} new, {updated} updated, {skipped} unchanged or "
              f"skipped, of {len(events)} events.")
    portals.mark_synced(prop.id, portal)
    portals.log(prop.id, portal, result, detail)
    return {"status": result, "added": added, "updated": updated,
            "skipped": skipped, "total": len(events), "detail": detail}


def sync_all_portals(db, prop: Property) -> list[tuple[str, dict]]:
    """Sync every portal that has a calendar URL configured."""
    if prop.id is None:
        return []
    portals = PortalRepo(db)
    results: list[tuple[str, dict]] = []
    for settings in portals.list_for_property(prop.id):
        if not settings.enabled or not settings.external_ical_url:
            continue
        results.append((settings.portal,
                        sync_portal(db, prop, settings.portal)))
    return results
