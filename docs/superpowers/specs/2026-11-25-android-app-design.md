# Android App Design — Full Lite Parity, Standalone-First

Date: 2026-11-25
Status: design approved in conversation; awaiting written-spec review

## Goal

Build a native Android version of KeKar Lite with every Lite feature, usable as a
complete standalone app on a phone or tablet, with optional explicit sync to the
desktop app. Neither platform owns the data by default; both work alone.

## Non-goals

- No always-on cloud account or server dependency.
- No automatic background merge of two portfolios.
- No iOS or desktop rewrite in this project.
- No direct posting to listing sites; the app produces copy packages like Lite.
- No AI key embedded in the APK.

## Key decisions

| Decision | Choice | Reason |
|---|---|---|
| Product shape | Full standalone mobile replacement | Master wants the phone to be primary, not a viewer |
| Data authority | Both apps standalone equals; sync optional | Neither device should be required for the other to work |
| Stack | Kotlin + Jetpack Compose + Room SQLite | Native device integration, no cross-platform plugin risk |
| Baseline | Android 10 / API 29, phones and tablets | Covers current hardware without legacy API burden |
| Conflict handling | Three-way field-level merge with visible conflict screen | Avoids silent overwrites of leases/applicant notes |
| Assistant key | User enters own key, stored in Android Keystore/EncryptedSharedPreferences | Nothing secret ships inside the APK |
| Photos | App-private compressed copies included in sync packages | Portable and predictable across devices |
| Distribution | Private signed APK first; Play Store later | Fast path to a usable client build, with store phase planned |
| Updates | GitHub release assets, like desktop | No private backend needed |

## Product model

Android and desktop each hold a complete local database. The user can use only
one for weeks or forever. When they choose to sync, the app exports or imports a
signed-by-checksum snapshot and resolves any conflicts explicitly. Sync never
runs silently in the background and never deletes a device's data without a
visible choice.

## Architecture

One native Android Studio project, modular by package:

- `app/` — Application class, MainActivity, navigation host, theme.
- `data/` — Room entities, DAOs, migrations, repositories mirroring desktop tables.
- `domain/` — use cases for property, applicant, lease, booking and listing operations.
- `sync/` — snapshot export/import, manifest, three-way merge, conflict UI.
- `ui/` — Compose screens and reusable components.
- `photos/` — camera/gallery capture, compression, app-private store, thumbnails.
- `listings/` — site package compiler for Zillow, apartments.com, Facebook Marketplace, Airbnb, Vrbo and Booking.com.
- `assistant/` — OpenRouter-compatible client, chat repository, tool dispatch.
- `settings/` — theme, tour state, key entry, backup retention.
- `updates/` — GitHub release check, download, verification and install.

Dependencies: Jetpack Compose, Room, Hilt, Navigation Compose, WorkManager,
DataStore, kotlinx.serialization, OkHttp, Coil, AndroidX Security. No Firebase
or cloud SDK in v1.

## Data model

Room entities mirror the desktop SQLite tables: `properties`, `applicants`,
`bookings`, `leases`, `portal_settings`, `chat_messages`, plus Android-only
`sync_state` and `photo_assets`. Legacy fields such as `amenity_parking`,
`pet_deposit_amount`, `garage_spaces` and `parking_type` are preserved so a
desktop snapshot round-trips without loss.

Room migrations are versioned and tested with the actual previous schema. A
schema version newer than the app understands causes a clear import error, not
a silent downgrade.

## Sync

A sync package is a `.kekarsync` ZIP containing:

- `database.db` — SQLite snapshot.
- `photos/<sha256>.jpg` — compressed photo assets.
- `manifest.json` — schema version, device ID, generation time, base snapshot ID,
  and SHA-256 hashes of every included file.

Transport order:

1. Android system share / Storage Access Framework for files.
2. Optional LAN or Tailscale HTTP endpoint exposed by the desktop app.
3. Manual copy through a drive or cloud storage by the user, treated as a file.

Import verifies every hash before opening the database. Merge uses the last
shared base snapshot. Clean fields auto-merge. Conflicting fields open a screen
showing both values. Delete-vs-edit offers "keep deleted", "keep edited" and
"restore both". Photos match by SHA-256 so renames do not duplicate them.

## Screens and UX

Bottom navigation: Dashboard, Properties, Calendar, Applicants, Leases, Stays,
Assistant. Settings and Help sit in the top bar.

Property detail contains Details, Rental terms (rent, deposit, pet deposit,
move-in/out date pickers), Short-stay terms, Amenities checkboxes, Pet policy
Yes/No, and Photos. Calendar shows one line per address with both move dates,
selected property bold, purple short stays, and date-tap property details.
Leases support the built-in comprehensive template and uploading a custom one.

Listings use a "Site" picker with per-site copy packages. Help contains the
calendar legend and guided tour. First run offers a demo-data tour, then leaves
the real database empty.

## Assistant

The assistant chat is available in the Android app. On first use the user
enters an OpenRouter-compatible API key in Settings; it is stored via Android
Keystore/EncryptedSharedPreferences. The key is never logged, included in a
sync package, or embedded in source. The tool set is read-only unless extended
deliberately, and any data-changing tool must be confirmed in the UI.

## Distribution and updates

Phase 1 distribution is a signed private APK installed by USB or Drive, with
updates checked from GitHub releases and verified by SHA-256, mirroring the
desktop updater. The signing keystore is kept outside the repo. Play Store
internal testing and production are a later phase requiring a privacy policy,
store listing and upload signing path.

## Delivery phases

1. Project scaffold: Gradle, Compose, Hilt, Navigation, Room schema and theme.
2. Standalone portfolio: properties, terms, amenities, pet policy, photos.
3. Calendar, applicants, leases and stays — full Lite record parity.
4. Listings, assistant, tour, settings, Help legend and update checker.
5. Sync packages, conflict UI, LAN transport and desktop-side sync support.
6. Hardening: tablets, accessibility, low-storage and permission paths, private APK.
7. Play Store internal track, then production.

Each phase ends with a runnable APK and an on-device check.

## Testing

- Unit tests for repositories, use cases, templates and sync merge.
- Room migration and schema-drift tests.
- Instrumented tests on a real Android 10+ device for compose navigation, camera
  permission flows, photo capture and SAF import/export.
- Sync round-trip tests against the real Windows and Linux desktop databases.
- Corrupt archive, checksum mismatch, schema mismatch and low-storage tests.
- Release check: install private APK, run tour, create data, sync both ways,
  check update flow.

## Risks and mitigations

- SAF and photo permissions differ by Android version — test on real API 29+ devices.
- Signing keystore loss would break upgrades — store offline and document recovery.
- Schema drift between desktop and Android — keep a shared schema version document and drift tests.
- Large photo packages — compress on capture and deduplicate by SHA-256.
- Assistant key leakage — Keystore only, never logs, sync or release artifacts.
- Play Store policy review — keep store phase separate from the private APK path.

## Success criteria

The Android app can be the only device used for a full rental portfolio: add
properties and photos, track applicants and leases, see the calendar, manage
short stays, generate every listing-site package, use the assistant with a
user-entered key, take the guided tour, and later sync with a desktop copy
without losing data or silently overwriting edits.
