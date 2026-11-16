#!/usr/bin/env python3
"""Import a real portal calendar into a COPY of the portfolio, and report.

    python tools/live_sync_check.py --url https://.../cal.ics --portal airbnb
    python tools/live_sync_check.py --url ... --portal vrbo --commit

Never writes to the real KeKarData: the portfolio is copied to a throwaway
directory first, so a live import can be inspected without touching the data
that ships on the drive. `--commit` only means "keep the copy"; the copy is
still not your real portfolio.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.db import Database
from src.data.models import (PORTALS, PORTAL_LABELS, PortalSettings,
                             Property)
from src.data.portal_repo import PortalRepo
from src.data.property_repo import PropertyRepo
from src.services.portal_sync import sync_portal


def run(url: str, portal: str, commit: bool = False,
        source_dir: Path | None = None) -> dict:
    """Sync one portal calendar for one property, on a copy of the data."""
    if portal not in PORTALS:
        raise SystemExit(f"unknown portal: {portal} (choose from {PORTALS})")
    source_dir = (source_dir or
                  Path(__file__).resolve().parent.parent / "KeKarData")
    if not (source_dir / "database.db").exists():
        raise SystemExit(f"no portfolio at {source_dir}")

    scratch = Path(tempfile.mkdtemp(prefix="kekar-live-sync-"))
    target = scratch / "KeKarData"
    shutil.copytree(source_dir, target)
    try:
        db = Database(target / "database.db")
        repo = PropertyRepo(db)
        short_stays = repo.list(kind="short_stay")
        rentals = repo.list()
        prop = (short_stays or rentals or [None])[0]
        if prop is None:
            raise SystemExit("the portfolio has no property to import into")

        # The URL is handed to this tool, so store it before syncing —
        # otherwise sync_portal answers "no calendar URL is set".
        portals = PortalRepo(db)
        settings = portals.get(prop.id, portal) or PortalSettings(
            property_id=prop.id, portal=portal)
        settings.enabled = True
        settings.external_ical_url = url
        portals.save(settings)

        result = sync_portal(db, prop, portal)
        bookings = db.conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE property_id=?",
            (prop.id,)).fetchone()[0]
        result.update({
            "dry_run": not commit,
            "portal": portal,
            "property": prop.address,
            "portal_label": PORTAL_LABELS[portal],
            "bookings_now": bookings,
        })
        # Only claim a path that still exists.
        if commit:
            result["copied_to"] = str(target)
        return result
    finally:
        # Left in place when --commit is passed, so the run can be inspected.
        if not commit:
            shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import a portal calendar into a copy of the portfolio.")
    parser.add_argument("--url", required=True, help="the portal's .ics URL")
    parser.add_argument("--portal", required=True, choices=PORTALS)
    parser.add_argument("--commit", action="store_true",
                        help="keep the throwaway copy instead of deleting it")
    parser.add_argument("--source-dir", type=Path, default=None,
                        help="portfolio to copy (default: the repo's KeKarData)")
    args = parser.parse_args(argv)

    report = run(args.url, args.portal, commit=args.commit,
                 source_dir=args.source_dir)
    for key, value in report.items():
        print(f"{key}: {value}")
    return 0 if report.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
