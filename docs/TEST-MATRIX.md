# KeKar End-to-End Test Matrix

Release gate for the current release. Every scenario must be run by a human on
real hardware — these cannot be automated from the build machine. Check the box
only after watching the scenario pass.

**Legend:** PASS = observed working · FAIL = observed broken · n/a = not
applicable on that platform · blank = not yet run

| # | Scenario | Windows | Linux | Notes / evidence |
|---|---|---|---|---|
| 1 | First run: wizard creates `KeKarData/` and accepts a key | | | |
| 2 | Second run: wizard is skipped | | | |
| 3 | Add a property, save, restart, data persists | | | |
| 4 | Mark Vacant -> Rented -> Vacant | | | |
| 5 | Copy listing -> paste into Notepad/text editor, content correct | | | |
| 6 | Add photos, thumbnails appear, restart, photos persist | | | |
| 7 | Add applicant, change stage, restart, stage persists | | | |
| 8 | Chat: ask "which properties allow pets?" -> correct answer | | | |
| 9 | Chat with no network -> friendly message, no crash | | | |
| 10 | Kill the app mid-write, restart -> integrity check passes or restores | | | |
| 11 | Unplug and replug into a different machine -> data intact | | | |
| 12 | Marketplace autofill (if enabled) -> fills fields, never publishes | | | |
| 13 | Drive set to read-only -> app falls back to OS config dir with a warning | | | |
| 14 | Corrupt the DB -> app restores the newest backup automatically | | | |
| 15 | Run from a drive letter other than the build machine's | | n/a | |
| 16 | Copy listing to clipboard, paste into Facebook Marketplace manually | | | |
| 17 | Daily backup appears in `KeKarData/backups/` after 24 h | | | |
| 18 | Uninstall/remove the drive -> no leftover data in `%APPDATA%` or `~/.config` | | | |
| 19 | Leases: load the client's example lease, generate for a tenant, copy, print, email | | | |
| 20 | Leases: save one, restart, it is still listed and reloads | | | |
| 21 | Listings: pick Zillow and apartments.com, copy, paste into a text editor | | | |
| 22 | Collapse the property list and the chat from the menu bar, restart, layout returns | | | |
| 23 | Switch to Light, Dark and OLED, restart, the choice returns | | | |
| 24 | Start menu / taskbar / title bar show the KeKar icon; the logo shows in the window header and About | | | |
| 25 | Accounts: add an account, turn on "Ask for a password", restart, log in, lock, unlock | | | |
| 26 | Short stay: set Type to Short stay, the form swaps to nightly rate, fees, minimum stay, occupancy, check-in/out, Instant Book, house rules | | | |
| 27 | Short stay: the list row shows a "Short stay" subtitle and no Vacant/Rented stripe | | | |
| 28 | Stays: add a stay, its days are marked on the calendar, restart, it persists | | | |
| 29 | Stays: adding an overlapping stay is refused with a readable message; cancelling frees the dates | | | |
| 30 | Portals: paste a real portal iCal URL, Sync now imports the events once and reports "unchanged" on a second sync | | | |
| 31 | Portals: set a price/min-stay override, open Portal listing, the preview shows the override and says so; Export calendar writes an .ics | | | |

## Automated coverage

These are covered by the pytest suite (`pytest -q`, 387 tests) and must stay
green:

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
  restored, and the caption stays inside the window at two sizes
  (`test_tour.py`)
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
- Short stays: the migration adds the columns to an old database and defaults
  `kind` to `rental`; the kind round-trips; the Airbnb/Vrbo/Booking.com
  packages, their warnings and the per-portal overrides; booking nights derived
  on write; overlap rejected in the repository and freed by a cancellation;
  `build_ical`/`parse_ical` round-trip including folded lines; sync imports by
  `UID`, reports `unchanged`, and logs the attempt; the Stays tab and the
  listing dialog apply what the form stores (`test_short_stay.py`)

## How to run a scenario

1. Copy the package to the drive with `tools/copy_to_usb.sh <mount> <package>`.
2. Launch with `KeKar.bat` (Windows) or `./KeKar.sh` (Linux).
3. Perform the steps in the scenario.
4. Record the result and, for anything that failed, attach the relevant lines
   from `KeKarData/logs/kekar.log`.

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
  the portals' real iCal dialect are unverified.
