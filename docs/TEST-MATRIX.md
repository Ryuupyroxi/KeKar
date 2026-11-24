# KeKar End-to-End Test Matrix

Release gate for the current release. Every scenario must be run by a human on
real hardware — these cannot be automated from the build machine. Check the box
only after watching the scenario pass.

**Legend:** PASS = observed working · FAIL = observed broken · n/a = not
applicable on that platform · blank = not yet run

`Runs in` is **demo** (safe: Help → Start demo mode, nothing touches the real
portfolio), **real** (needs the real `KeKarData` — persistence across a restart,
the install or the drive itself) or **either**. Demo mode is session-only, so a
scenario that must survive a restart is always `real`. Settings are shared with
the real install even in demo mode, so a scenario that asserts a *setting*
returning after a restart is `real` too.

| # | Scenario | Runs in | Windows | Linux | Notes / evidence |
|---|---|---|---|---|---|
| 1 | First run: wizard creates `KeKarData/` and accepts a key | real | | | |
| 2 | Second run: wizard is skipped | real | | | |
| 3 | Add a property, save, restart, data persists | real | | | |
| 4 | Mark Vacant -> Rented -> Vacant | demo | | | |
| 5 | Copy listing -> paste into Notepad/text editor, content correct | demo | | | |
| 6 | Add photos, thumbnails appear, restart, photos persist | real | | | |
| 7 | Add applicant, change stage, restart, stage persists | real | | | |
| 8 | Chat: ask "which properties allow pets?" -> correct answer | demo | | | |
| 9 | Chat with no network -> friendly message, no crash | demo | | | |
| 10 | Kill the app mid-write, restart -> integrity check passes or restores | real | | | |
| 11 | Unplug and replug into a different machine -> data intact | real | | | |
| 12 | Marketplace autofill (if enabled) -> fills fields, never publishes | demo | | | |
| 13 | Drive set to read-only -> app falls back to OS config dir with a warning | real | | | |
| 14 | Corrupt the DB -> app restores the newest backup automatically | real | | | |
| 15 | Run from a drive letter other than the build machine's | real | | n/a | |
| 16 | Copy listing to clipboard, paste into Facebook Marketplace manually | demo | | | |
| 17 | Daily backup appears in `KeKarData/backups/` after 24 h | real | | | |
| 18 | Uninstall/remove the drive -> no leftover data in `%APPDATA%` or `~/.config` | real | | | |
| 19 | Leases: load the client's example lease, generate for a tenant, copy, print, email | demo | | | |
| 20 | Leases: save one, restart, it is still listed and reloads | real | | | |
| 21 | Listings: pick Zillow and apartments.com, copy, paste into a text editor | demo | | | |
| 22 | Collapse the property list and the chat from the menu bar, restart, layout returns | real | | | |
| 23 | Switch to Light, Dark and OLED, restart, the choice returns | demo | | | |
| 24 | Start menu / taskbar / title bar show the KeKar icon; the logo shows in the window header and About | real | | | |
| 25 | Accounts: add an account, turn on "Ask for a password", restart, log in, lock, unlock | real | | | |
| 26 | Short stay: set Type to Short stay, the form swaps to nightly rate, fees, minimum stay, occupancy, check-in/out, Instant Book, house rules | demo | | | |
| 27 | Short stay: the list row shows a "Short stay" subtitle and no Vacant/Rented stripe | demo | | | |
| 28 | Stays: add a stay, its days are marked on the calendar, restart, it persists | real | | | |
| 29 | Stays: adding an overlapping stay is refused with a readable message; cancelling frees the dates | demo | | | |
| 30 | Portals: run `tools/live_sync_check.py` against a real portal calendar, then Sync now in the app twice (second run reports "unchanged") | demo | | | |
| 31 | Portals: set a price/min-stay override, open Portal listing, the preview shows the override and says so; Export calendar writes an .ics | demo | | | |
| 32 | Address lookup: with a Google Maps key in Settings, type 4+ characters in Street address, the drop-down appears, pick a place; City and blank ZIP fill, a typed ZIP is kept | real | | | needs a real Maps key |

## Automated coverage

These are covered by the pytest suite (`pytest -q`, 414 tests as of this
feature) and must stay green:

- Schema creation, WAL mode, foreign keys, migration idempotency (`test_db.py`)
- Property and applicant CRUD, stage validation, document records
  (`test_property_repo.py`, `test_applicant_repo.py`)
- Backup, restore, prune, corruption recovery (`test_backup.py`)
- Listing compiler, including missing-optionals handling (`test_listing_compiler.py`)
- Versioned listing templates and the fallback when the file is missing
  (`test_listing_templates.py`)
- Image import, resize, thumbnail, cover selection, deletion (`test_image_service.py`)
- Agent tool schemas, dispatch, unknown-tool rejection (`test_agent_tools.py`)
- Agent loop: final answer, tool execution, cancellation, step limit
  (`test_agent_runner.py`)
- LLM fallback chain (`test_agent_client.py`)
- Provider key verification against `/models` (`test_agent_verify_key.py`)
- Settings encryption roundtrip, wrong-key failure, passphrase derivation
  (`test_crypto.py`, `test_settings.py`)
- Default config loader and its embedded fallback (`test_default_config.py`)
- Browser launcher flag construction, CDP connect failure handling
  (`test_launcher.py`, `test_cdp_client.py`)
- Marketplace autofill stops before Publish; missing selector -> `needs_review`
  (`test_marketplace.py`)
- GUI construction, drawer, form, photo panel, CRM, chat pane, wizard, settings
  (`test_gui_smoke.py`, headless `QT_QPA_PLATFORM=offscreen`)
- UI behaviour: typography, status stripes, inclusive search across amenities,
  listing preview/copy, marketplace dialog safeguards, applicant-property
  linking, CRM stage colours (`test_ui_behaviour.py`)
- CLI flags `--version`, `-V`, `--help` (`test_main_cli.py`)
- First-run key seeding roundtrip (`test_seed_first_run.py`)
- USB packaging: launcher sources stay in sync, package layout, reproducibility,
  Windows `.ico` staging, and the AppImage icon (`test_usb_packaging.py`)
- Frozen-bundle safety: no runtime dependency on an unshipped file
  (`test_bundle_safety.py`)
- Demo mode: the demo path is separate, entering and leaving swaps the database,
  a real property survives both, and a changed data directory mid-session does
  not lose the real database (`test_demo_mode.py`)
- Demo seed: populates an empty database, is idempotent, and produces the
  expected properties and applicant stages (`test_demo_mode.py`)
- Guided tour: step targets resolve to real widgets, the overlay paints without
  raising, navigation clamps at both ends, Esc closes, the Applicants tab is
  restored, the caption stays inside the window at two sizes, and the wording
  names the features just shipped (`test_tour.py`)
- Themes: every palette clears the WCAG contrast ratios, resolution falls back
  safely, switching recolours the painted rows, and the View menu reflects the
  stored preference (`test_themes.py`)
- Collapsible panels: collapse and restore return the remembered split, the
  collapsed flags persist, the menu-bar toggles stay reachable while a panel is
  collapsed, and the splitter handle never overrides Qt's mouse events
  (`test_layout.py`)
- Leases: marker substitution, unknown markers left intact, money formatting,
  the repository round trip, the saved-lease list, print via the system dialog,
  and the `mailto:` hand-off (`test_leases.py`)
- Listing channels: Zillow and apartments.com packages, per-field lists,
  title-length and missing-rent warnings, and the dialog's channel switching
  (`test_listing_channels.py`)
- Branding: the `.ico` carries every frame size, the hicolor PNGs exist, the
  window icon is set, and the logo renders in the header and About
  (`test_branding.py`)
- Live sync harness: `tools/live_sync_check.py` copies the portfolio, stores
  the URL it is given, syncs and reports counts without writing to the real
  `KeKarData` (`tests/test_live_sync_check.py`)
- Short stays: the migration adds the columns to an old database and defaults
  `kind` to `rental`; the kind round-trips; the Airbnb/Vrbo/Booking.com
  packages, their warnings and the per-portal overrides; booking nights derived
  on write; overlap rejected in the repository and freed by a cancellation;
  `build_ical`/`parse_ical` round-trip including folded lines; sync imports by
  `UID`, reports `unchanged`, and logs the attempt; the Stays tab and the
  listing dialog apply what the form stores (`test_short_stay.py`)
- Google Maps: autocomplete/details request construction and parsing from
  mocked HTTP responses, no-key means no request, HTTP failures quote the
  provider's message, and readable network errors (`test_maps_service.py`)
- Address UI: a real QCompleter/QStringListModel on the address field, 350 ms
  debounce, four-character minimum, no popup or request without a key,
  selection fills the address and only blank City/ZIP, the autofill switch,
  worker reaping, and Settings save/load (`test_maps_ui.py`, `test_settings.py`,
  `test_default_config.py`)

## Scenario 12 — live Marketplace autofill

Needs Facebook logged in once in KeKar's dedicated browser profile
(`KeKarData/browser_profile/`) and **Settings → Marketplace autofill** turned on.

1. File → Settings → enable Marketplace autofill. Close the dialog.
2. Select a rental property that has a photo, then **Publish to Marketplace…**
3. The KeKar browser profile opens and navigates to the Marketplace listing form.
4. Watch it fill title, price, description and photos. It then **stops**.
5. Read the report in the dialog. Expect `autofilled` or `needs_review`.
   `failed` is also a legitimate result — record the message verbatim.
6. Confirm the browser tab still shows an **unpublished draft**: no Publish click.
7. Paste the report text and a screenshot of the dialog into row 12.

If the report says `needs_review`, the selectors in
`config/marketplace_selectors.json` have drifted: update them and bump that
file's `schema_version`.

## Scenario 30 — live portal sync

Needs a real calendar export URL. Airbnb: the listing's Availability → Export
calendar. Vrbo and Booking.com expose one in the owner/extranet dashboard.

1. Copy the URL, then run the check against a **copy** of your portfolio:

   ```bash
   .venv/bin/python tools/live_sync_check.py \
     --url "<paste the portal URL>" --portal airbnb
   ```

   Expect `status: ok` with `added:` / `updated:` / `skipped:` counts and
   `dry_run: True`. The tool copies `KeKarData` to a throwaway directory, so
   your real bookings are never written. Paste the whole output into row 30.
2. Switch to KeKar, open the short-stay property's **Portals** group, paste the
   same URL into the portal's Calendar field and press **Sync now**.
   Expect the same counts and `Last sync:` to update.
3. Press **Sync now** again. Expect `unchanged` and `0` new.
4. Add one booking in KeKar, then **Export calendar (.ics)…** and open the file
   in a text editor. Expect `BEGIN:VCALENDAR` and one `VEVENT` per live booking,
   with `UID`, `DTSTART`, `DTEND` and `SUMMARY`.
5. If a portal's calendar uses a dialect the parser rejects, the tool says so
   with the provider's own message — paste it verbatim rather than paraphrasing.

## KeKar Lite scenarios (L1–L6)

| Scenario | Command | Expected observation | Result |
|---|---|---|---|
| L1 | `out/KeKarLite_Linux/KeKarLite_Linux/KeKarLite` on a real display | Window title "KeKar Lite Property Manager"; property list and tab card only, no chat pane or network pill | PASS — `scratch/lite-main.png`, `scratch/lite-view-menu.png`; title and no chat pane confirmed, View menu has "Collapse property list" but no "Collapse chat". The grey "No property selected" pill belongs to the form and exists in both builds. |
| L2 | Open a short-stay property | Type shows "Short stay"; no Portals group, no "Publish to Marketplace…" button | PASS in-process — `test_lite_ui.py` asserts `publish_btn is None`, `portals_box is None`, and the Type label is "Short stay"; no Portals group visible in `scratch/lite-main.png`. |
| L3 | Properties → Preview listing | Rental offers generic + Zillow; short stay offers generic + Booking.com; Copy works | PASS in-process — `test_lite_ui.py` asserts those channel lists; `Save`, `Preview listing` and `Copy listing` widgets are visible at y=668 in the Lite form geometry probe; they sit below the folded viewport in `scratch/lite-main.png`. |
| L4 | Open the same `KeKarData/` with full KeKar | Properties, applicants, leases, stays and chat history all still present | PARTIAL — no data-layer change; both binaries opened against `out/KeKarLite_Linux/KeKarData` and `verify_usb.py` passed. Populated-data GUI round-trip not yet driven. |
| L5 | Block outbound traffic | Every Lite feature works; no error dialogs | PASS by construction/tests — agent, provider ping, portal sync, Marketplace browser and Maps are not composed in Lite; `test_lite_ui.py::test_lite_form_never_starts_a_maps_request` proves no request with a stored key. Physical network unplug not performed. |
| L6 | `out/KeKarLite_Linux/KeKarLite_Linux/KeKarLite --version` | Prints `KeKar Lite <version>` on a headless machine | PASS — printed `KeKar Lite 1.6.0`; full build printed `KeKar 1.6.0`. |

## How to run a scenario

1. Copy the package to the drive with `tools/copy_to_usb.sh <mount> <package>`.
2. Launch with `KeKar.bat` (Windows) or `./KeKar.sh` (Linux).
3. Perform the steps in the scenario.
4. Record the result and, for anything that failed, attach the relevant lines
   from `KeKarData/logs/kekar.log`.

## Windows hardware pass

Run on the target Windows 10/11 machine, from the release zip or the installer.

1. Unzip `KeKar_Windows.zip` to a folder and double-click `KeKar.bat`.
   SmartScreen may warn because the build is not code-signed: click
   **More info → Run anyway**. Record whether the warning appeared.
2. Or run `KeKar_Setup_<version>.exe` and confirm the Start-menu and Desktop
   shortcuts, then launch from the shortcut.
3. Run rows 1-9 in order.
4. Row 11 needs a second machine or a VM.
5. Row 13: set the drive read-only (a physical switch, or a read-only bind
   mount) and confirm the app warns and falls back instead of dying.
6. Row 14: corrupt `KeKarData/database.db`, relaunch, confirm the restore path.
7. Row 24: confirm the house mark in the Start menu, Desktop, taskbar and title
   bar, and the wordmark in the window header and About.
8. Rows 26-31: the short-stay pass.
9. Paste back `KeKarData/logs/kekar.log` (`tail -40`) and one screenshot per row.

What proves it: every row marked PASS with an observation, not "looked fine".

## Known gaps

- Scenario 10 (kill mid-write) needs a manual `kill -9`; there is no automated
  test because the recovery path is exercised by `test_recovery_restores_on_corruption`
  instead.
- Scenario 13 (read-only drive) needs a physical write-protect switch or a
  read-only bind mount.
- Scenario 17 needs a 24-hour wait; the prune logic is covered by
  `test_prune`.
- Scenario 30 needs a real portal calendar URL. The automated tests use a
  local fixture (`tests/test_short_stay.py::CALENDAR`), so the live fetch and
  the portals' real iCal dialect are unverified until this row is filled.
