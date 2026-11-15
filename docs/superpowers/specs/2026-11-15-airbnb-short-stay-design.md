# Airbnb / short-stay support — design

Date: 2026-11-15. Status: approved in outline by Master ("implement all phases").
Covers Phases 1-3 below, and the v1.2 release that follows.

## Why

The collection holds two kinds of property: long-term rentals (Zillow,
apartments.com, Facebook Marketplace, leases, applicants) and Airbnb-style
short stays. Today everything is modelled as a long-term rental, so a short
stay has nowhere to put a nightly rate, a cleaning fee, a minimum stay, a
house manual or its portal calendars.

## The honest constraint on "two-way sync"

Airbnb, Vrbo and Booking.com expose no public two-way API to a small landlord.
Booking's Connectivity API and Vrbo's partner API need a signed partnership;
Airbnb has none. The one two-way channel all three offer for free is **iCal**:
each portal exports a calendar URL and accepts an imported one.

So "full channel management" is delivered as:

- KeKar owns the bookings and per-portal pricing.
- Calendars sync by `.ics` (export a file per property, import the portal's URL).
- Listing copy is a per-portal package, copied and pasted (the existing,
  accepted pattern for Zillow/apartments.com).
- Messages are copy/mailto helpers, not an API.

Anything beyond that needs a paid channel manager (OwnerRez, Hospitable,
Hostaway) and is out of scope.

## Phase 1 — a property kind

### Data

`properties.kind TEXT NOT NULL DEFAULT 'rental' CHECK (kind IN ('rental','short_stay'))`.

Short-stay columns, all nullable, all additive:

| column | type | meaning |
|---|---|---|
| `nightly_price` | REAL | per-night rate |
| `cleaning_fee` | REAL | one-off cleaning fee |
| `extra_guest_fee` | REAL | per extra guest per night |
| `min_stay_nights` | INTEGER | minimum stay |
| `max_guests` | INTEGER | occupancy limit |
| `check_in_time` | TEXT | e.g. `15:00` |
| `check_out_time` | TEXT | e.g. `11:00` |
| `instant_book` | INTEGER 0/1 | book without host approval |
| `cancellation_policy` | TEXT | e.g. `Flexible` |
| `house_rules` | TEXT | free text, shown in the listing |

`status` (`Vacant`/`Rented`) stays as-is. For a short stay it is not the
availability signal — the reservations calendar is — so the list row shows a
"Short stay" chip and no status stripe for `kind='short_stay'`.

New columns on an existing table need an idempotent `ALTER TABLE` pass, not
just `CREATE TABLE IF NOT EXISTS`. `Database._migrate` gains a column check
against `PRAGMA table_info` for `properties`.

### Listing packages

`listing_channels.py` gains three short-stay channels, each shaped like that
site's form (title, body, per-field, warnings):

- `airbnb` — title `$X/night in {city} · {address}`, body with nightly rate,
  cleaning fee, min stay, max guests, check-in/out, house rules.
- `vrbo` — similar, with the deposit replaced by the cleaning fee.
- `booking_com` — per-night price, max guests, min stay, cancellation policy.

`CHANNELS[channel]` gains a `kind` marker. `compile_channel(prop, channel)`
fills the short-stay tokens. `ListingDialog` labels the dropdown by the
property's kind and filters the list: a rental sees Zillow/apartments.com, a
short stay sees Airbnb/Vrbo/Booking.com. "Any site (generic)" stays for both,
using a short-stay generic template for short stays.

### UI

`PropertyForm` gains a **Kind** selector (Rental / Short stay). Two field
groups replace the rent/deposit/available triple inside Details:

- **Rental terms** — monthly rent, security deposit, available date. Shown for
  rentals.
- **Short-stay terms** — the nine columns above. Shown for short stays.

The Details grid keeps address, city, ZIP, bedrooms, bathrooms, sqft, pet
policy. Amenities and Notes are unchanged. `Publish to Marketplace` is rental
only; a short stay gets `Portal listing…` (the listing dialog).

## Phase 2 — reservations

### Data

```
bookings(
  id, property_id FK -> properties ON DELETE CASCADE,
  portal TEXT,                   -- airbnb | vrbo | booking_com | direct | ''
  guest_name, guest_contact,
  check_in, check_out,            -- ISO dates
  nights INTEGER, payout REAL,
  status TEXT CHECK in (confirmed, cancelled, blocked, inquiry),
  external_uid TEXT,              -- UID from an imported iCal event
  source TEXT CHECK in (manual, ical),
  notes, created_at, updated_at,
  UNIQUE(property_id, external_uid) where external_uid is not null
)
```

`nights` is derived on write (`check_out - check_in`), never trusted from a
form. Overlap is rejected in the repository, not the UI.

### UI

A **Stays** tab on the main window:

- A month calendar (`QCalendarWidget`) for the selected property, with days
  that have a booking marked.
- A bookings table: guest, portal, check-in, check-out, nights, payout,
  status, source.
- Add / edit / delete a booking; add asks for the property, guest, dates,
  portal and payout.
- A booking blocks the dates in the calendar and is what the iCal export emits.

The Applicants tab and leases are untouched; a short stay simply has no
applicants or lease.

## Phase 3 — two-way calendar sync

### Data

```
property_portals(
  id, property_id FK -> properties ON DELETE CASCADE,
  portal TEXT CHECK in (airbnb, vrbo, booking_com),
  enabled INTEGER 0/1,
  price_override REAL, min_stay_override INTEGER,
  external_ical_url TEXT, external_listing_url TEXT,
  last_sync_at TEXT,
  UNIQUE(property_id, portal)
)

portal_sync_log(
  id, property_id, portal, started_at, finished_at,
  result TEXT CHECK in (ok, failed, unchanged),
  detail TEXT
)
```

### Service: `src/services/ical_service.py`

- `build_ical(prop, bookings) -> str` — an RFC 5545 `VCALENDAR`, one `VEVENT`
  per booking (`DTSTART`/`DTEND` as `VALUE=DATE`, `UID`, `SUMMARY` =
  `Booked: <guest>`, `DESCRIPTION` with portal/payout, `STATUS` from the
  booking). Blocked bookings become `STATUS:CONFIRMED` with summary `Blocked`.
- `parse_ical(text) -> list[dict]` — handles `DATE` and `DATE-TIME` values,
  folded lines (CRLF + leading space), `VALUE=DATE`, and `STATUS`. Unknown or
  malformed events are skipped and counted, never fatal.
- `fetch_ical(url) -> str` — `urllib` with a timeout; every failure returns a
  readable message.
- `export_ical(prop, bookings) -> Path` — writes
  `KeKarData/calendar/<address-slug>.ics` and returns the path.

### Sync

`BookingRepo.sync_portal(db, prop, portal)`:

1. Fetch the portal's `external_ical_url`.
2. Parse it; upsert by `external_uid` (`source='ical'`).
3. Write `last_sync_at`, append a `portal_sync_log` row.
4. Return counts (added / updated / unchanged / skipped).

Per-portal overrides (`price_override`, `min_stay_override`) feed the listing
packages: a short-stay listing shows the override for that portal when set,
otherwise the property's own value.

### UI

A **Portals** group on the short-stay property form:

- One row per portal: enabled checkbox, price override, min-stay override,
  external iCal URL, "Sync now", last-sync label.
- An "Export calendar (.ics)" button that writes the file and reports the
  path.

## Testing

- Unit: schema/migration adds the columns and tables to an existing database;
  kind defaults to `rental`; the short-stay channels compile and warn;
  `build_ical`/`parse_ical` round-trip; overlap is rejected; sync upserts by
  UID and logs.
- GUI: a short-stay property renders the short-stay groups and hides the
  rental ones; the Stays tab shows a booking and blocks its dates; the portal
  group syncs and reports.
- Real display: screenshot a short-stay property, its listing dialog, the
  Stays tab and the Portals group in Light/Dark/OLED.

## Release

Version `1.2.0`, tag `v1.2.0`, pushed to `Ryuupyroxi/KeKar`. CI builds the
Linux and Windows packages and attaches them to the GitHub release. The
release notes name the Airbnb feature and the testers' re-check commands
(`pytest -o addopts='' -q`, `bash build.sh`, `python tools/verify_usb.py`).

## Explicitly out of scope

- Posting to Airbnb/Vrbo/Booking.com programmatically (no API; ToS).
- Two-way message sync (no API; mailto/copy only).
- A paid channel manager integration.
- Long-term rental behaviour changes beyond the additive schema.
