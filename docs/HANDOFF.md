# Handoff — Airbnb / short-stay support (Phases 1-3)

Written 2026-11-15, extended 2026-11-16 for the gap-closure pass.

## Where it stands

- `pytest -q` → **392 passed**, exit 0 (`.venv/bin/python -m pytest -o addopts='' -q`).
- Test modules: 40. Collected: 392.
- Version **1.2.0**, tag **v1.2.0**, release published:
  https://github.com/Ryuupyroxi/KeKar/releases/tag/v1.2.0 with
  `KeKar_Linux.zip` (282 MB) and `KeKar_Windows.zip` (152 MB) attached.
- `bash build.sh` runs green end to end (suite + PyInstaller + USB package +
  verify); the frozen `dist/KeKar/KeKar --version` prints `KeKar 1.2.0`.
- All work is pushed; `git status` is clean.

## Gap closure (2026-11-16)

Plan: `docs/superpowers/plans/2026-11-16-gap-closure-plan.md`, including an
"As built" section with the three NSIS defects the plan did not anticipate.

- **G1 closed and proven.** CI now compiles the NSIS installer and attaches it.
  A throwaway v1.2.1 release carried all three assets
  (`KeKar_Setup_1.2.0.exe`, 100,411,978 bytes); the release and tag were then
  deleted, so **v1.2.0 itself still has only the two zips**. Moved on to the
  next release, or move the v1.2.0 tag if Master wants the installer there.
- **G2 closed.** `tools/live_sync_check.py` + 3 tests; verified against the
  fixture over `file://`.
- **G3-G5 closed as procedures.** Scenario 12, Scenario 30 and a Windows
  hardware pass are written; every matrix row now says demo or real.
- **G6 closed for `~/.hermes/.env`.** `GITHUB_TOKEN` removed (it was the
  Discord bot token); `gh auth status` and `git push --dry-run` still work.
  Backup: `~/.hermes/.env.bak-20261116`. `auth.json::credential_pool.github`
  still holds the same wrong value — no reader, live store, left alone.

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

## GitHub: released

The push, tag and release all succeeded after Master corrected the credential.
`gh auth status` now shows a real `ghp_` token (keyring) with `repo` and
`workflow` scopes, and both CI runs on v1.2.0 are green.

**One latent problem worth fixing:** `~/.hermes/.env::GITHUB_TOKEN`,
`auth.json`'s top-level `github_token` and
`auth.json::credential_pool.github.token` are all the *same* value, and it is
not a GitHub token — it is byte-identical to `DISCORD_BOT_TOKEN`, and its first
dot-segment base64-decodes to the Discord user id `153314362098`. It answers
`401 Bad credentials`. The release worked because `gh`'s keyring token is
separate and valid; the mislabelled copy is still sitting in the Hermes config
and will mislead the next thing that reads it.

## Frozen-build evidence

The packaged binary, not just the source:

- `dist/KeKar/KeKar --version` → `KeKar 1.2.0`.
- Launched on the real display (`DISPLAY=:0`, throwaway data dir with one short
  stay and one booking). The drawer row reads "Short stay · Pawhuska" (new
  code), the Properties tab shows **Type = Short stay (Airbnb)**, and the
  **Stays** tab renders the calendar with the booked days marked and the
  Jordan Lee / Airbnb / 3 nights / 405 row in the table — so `stays_tab`,
  `booking_repo`, `ical_service` and `portal_sync` are all inside the bundle
  and working. Screenshots: `frozen-form-crop.png`, `frozen-stays-crop.png`.

## Still outstanding

- `docs/TEST-MATRIX.md` scenarios 1-18 and the new 26-31 need a human on real
  hardware.
- Portal sync is verified against a local calendar fixture, not a live portal
  URL.
- The NSIS installer is still a manual `makensis` step on Windows.
- Fix the mislabelled `GITHUB_TOKEN` in `~/.hermes/.env` (it is the Discord bot
  token) so the next tool that reads it does not send a Discord token to
  GitHub.
