# Handoff — Airbnb / short-stay support (Phases 1-3)

Written 2026-11-15. State of the tree at the end of this working session.

## Where it stands

- `pytest -q` → **387 passed**, exit 0 (`.venv/bin/python -m pytest -o addopts='' -q`).
- Source: 64 modules, 9,266 lines (`find src -name '*.py' -not -path '*__pycache__*'`
  piped to `wc -l`, twice).
- Test modules: 39. Test functions: 359. Collected: 387.
- Nothing is committed. `git status` shows 16 modified and 6 new files.
- **4 commits are unpushed** (`43b0118`, `77269f3`, `a5f8f7d`, `4ea986b`), and
  `gh auth status` reports the token invalid, so the release step is blocked
  until Master re-authenticates.

## What was built

The approved design
(`docs/superpowers/specs/2026-11-15-airbnb-short-stay-design.md`) is implemented
end to end.

### Phase 1 — a property kind

- `properties.kind` (`rental` | `short_stay`) plus ten nullable short-stay
  columns. `Database._add_missing_columns()` runs an idempotent `ALTER TABLE`
  pass against `PRAGMA table_info`, so a v0.1.0 database gains the columns in
  place; `SCHEMA_VERSION` stays 1.
- `PropertyForm` has a **Type** selector. Rental terms and Short-stay terms are
  separate group boxes; Portals shows only for a short stay.
- `listing_channels.py` gained `airbnb`, `vrbo` and `booking_com`, each with a
  `kind` marker, a per-site title/body and a per-field list. `known_channels(kind)`
  filters the dialog's dropdown by the property's kind.
- `listing_compiler` has a short-stay generic template and a short-stay footer.

### Phase 2 — reservations

- `bookings` table, `BookingRepo` (nights derived on write, overlap rejected in
  the repository, a cancelled stay frees its dates, `booked_dates()` for the
  calendar).
- `StaysTab`: property picker, `QCalendarWidget` with booked days painted,
  bookings table, add / edit / cancel / delete.
- The drawer shows a "Short stay ·" subtitle and no status stripe for a short
  stay (its availability lives in the calendar).

### Phase 3 — two-way calendar sync

- `property_portals` and `portal_sync_log` tables, `PortalRepo`.
- `ical_service.py` writes and parses RFC 5545 by hand (no new dependency):
  `build_ical`, `parse_ical` (folds lines, handles `DATE` and `DATE-TIME`),
  `fetch_ical`, `export_ical` → `KeKarData/calendar/<slug>.ics`.
- `portal_sync.sync_portal()` fetches the portal's URL, upserts by `UID`
  (`source='ical'`), stamps `last_sync_at`, logs the attempt and returns
  counts. It never raises for a network or parse failure.
- The **Portals** group on the short-stay form: per portal an enable checkbox,
  price override, min-stay override, calendar URL, **Sync now** (on a worker
  thread) and a last-sync label, plus **Export calendar (.ics)…**.

## Two gaps found against the design, and fixed

- **The overrides were stored but never used.** The design says a short-stay
  listing shows the portal's `price_override` / `min_stay_override` when set.
  Nothing read them. `compile_channel()` now takes both, `_substitute()` and
  `_common_fields()` use the effective values, and the warnings test the
  effective values. `ListingDialog` reads them through `PortalRepo` and shows
  "Using the Airbnb override: $140 per night and a 3-night minimum."
- **The design gives a short stay a "Portal listing…" button; the code hid the
  button.** `publish_btn` now keeps one slot and relabels itself —
  "Publish to Marketplace..." for a rental, "Portal listing…" for a short stay —
  and `_publish_or_list()` branches to the listing dialog or the Marketplace
  dialog.

## Verification evidence

Real display, 1280x800, `DISPLAY=:0`, scratch copy of the data dir
(`cache/scratch/kekar-stay-data`):

- `stay-rental.png` / `stay-terms.png` / `stay-portals.png` — the Type selector
  swaps the term group, Portals shows three complete rows, no clipping.
- `stay-stays.png` — the calendar marks 1-3 December and the table lists the
  stay (Jordan Lee, Airbnb, 3 nights, 405, confirmed, manual).
- `stay-listing.png` — the dialog offers generic, Airbnb, Booking.com and Vrbo;
  with Airbnb selected the override line shows and the preview carries $140 and
  a 3-night minimum.
- `stay-theme-{light,dark,oled}[-stays].png` — all three themes render the new
  widgets with no unreadable areas.

Measured in code, not by eye: the short-stay form is 1232 px tall with a 375 px
viewport (it scrolls; that is intended), `hscroll_max=0`, and the group boxes
sit at Details 46, Short-stay terms 264, Portals 585, Amenities 922, Notes 1028.

## Re-check

```bash
cd "/home/Ryuu/Documents/kekar project"
.venv/bin/python -m pytest -o addopts='' -q          # 387 passed
.venv/bin/python -m pytest -o addopts='' -q tests/test_short_stay.py
bash build.sh                                        # rebuild + package + verify
```

Real display:

```bash
DISPLAY=:0 .venv/bin/python \
  /home/Ryuu/.hermes/profiles/fenrys/cache/scratch/shot_stays.py
DISPLAY=:0 .venv/bin/python \
  /home/Ryuu/.hermes/profiles/fenrys/cache/scratch/shot_themes.py
```

## Still outstanding

- Nothing is committed.
- The release step of the design (version, tag, push, CI attach) is not done:
  4 commits are unpushed and `gh` is unauthenticated.
- `docs/TEST-MATRIX.md` scenarios 1-18 and the new 26-31 need a human on real
  hardware.
- Portal sync is verified against a local calendar fixture, not a live portal
  URL.
- The NSIS installer is still a manual `makensis` step on Windows.
