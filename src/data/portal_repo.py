"""Per-portal settings and the sync log for a short-stay property."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .models import PORTALS, PortalSettings

_COLUMNS = [
    "id", "property_id", "portal", "enabled", "price_override",
    "min_stay_override", "external_ical_url", "external_listing_url",
    "last_sync_at",
]

_NOW = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def _row(row: sqlite3.Row) -> PortalSettings:
    return PortalSettings(
        id=row["id"], property_id=row["property_id"], portal=row["portal"],
        enabled=bool(row["enabled"]), price_override=row["price_override"],
        min_stay_override=row["min_stay_override"],
        external_ical_url=row["external_ical_url"],
        external_listing_url=row["external_listing_url"],
        last_sync_at=row["last_sync_at"],
    )


class PortalRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        db = self._db
        return db.conn if hasattr(db, "conn") else db

    def get(self, property_id: int, portal: str) -> PortalSettings | None:
        row = self.conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM property_portals "
            f"WHERE property_id=? AND portal=?",
            (property_id, portal)).fetchone()
        return _row(row) if row else None

    def list_for_property(self, property_id: int) -> list[PortalSettings]:
        rows = self.conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM property_portals "
            f"WHERE property_id=? ORDER BY portal", (property_id,))
        return [_row(r) for r in rows]

    def save(self, settings: PortalSettings) -> None:
        if settings.portal not in PORTALS:
            raise ValueError(f"unknown portal: {settings.portal}")
        existing = self.get(settings.property_id, settings.portal)
        if existing is None:
            self.conn.execute(
                "INSERT INTO property_portals "
                "(property_id, portal, enabled, price_override, "
                " min_stay_override, external_ical_url, "
                " external_listing_url, last_sync_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (settings.property_id, settings.portal,
                 int(settings.enabled), settings.price_override,
                 settings.min_stay_override, settings.external_ical_url,
                 settings.external_listing_url, settings.last_sync_at))
            return
        self.conn.execute(
            "UPDATE property_portals SET enabled=?, price_override=?, "
            "min_stay_override=?, external_ical_url=?, "
            "external_listing_url=?, last_sync_at=? WHERE id=?",
            (int(settings.enabled), settings.price_override,
             settings.min_stay_override, settings.external_ical_url,
             settings.external_listing_url, settings.last_sync_at,
             existing.id))

    def mark_synced(self, property_id: int, portal: str,
                    when: str | None = None) -> None:
        stamp = when or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        self.conn.execute(
            "UPDATE property_portals SET last_sync_at=? "
            "WHERE property_id=? AND portal=?",
            (stamp, property_id, portal))

    def log(self, property_id: int, portal: str, result: str,
            detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO portal_sync_log "
            "(property_id, portal, finished_at, result, detail) "
            f"VALUES (?, ?, {_NOW}, ?, ?)",
            (property_id, portal, result, detail))

    def recent_syncs(self, limit: int = 20) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT property_id, portal, started_at, finished_at, result, "
            "detail FROM portal_sync_log ORDER BY id DESC LIMIT ?",
            (limit,)))
