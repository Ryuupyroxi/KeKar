# KeKar Property Manager

One folder for everything KeKar. No stray files, no scattered repos, no
"where did I put that" — if it belongs to KeKar, it lives here.

## Where things are

| Path | What it is |
|---|---|
| `docs/KeKar-Build-Plan.md` | **Master build plan — start here.** 36 tasks, 8 phases, full code for the foundations. |
| `docs/SECURITY.md` | Security gates, redaction rules and permission checks. |
| `docs/TEST-MATRIX.md` | Cross-platform end-to-end test matrix (human run). |
| `docs/WIRING.md` | How the pieces connect at runtime — startup, data flow, agent loop, browser automation. |
| `docs/SPEC-COVERAGE.md` | Every spec requirement traced to the code and the test that proves it. |
| `src/` | Application source — Python 3.12, PyQt6, SQLite. |
| `tests/` | pytest suite (39 test modules). |
| `config/` | Listing templates, default config, Marketplace selectors. |
| `tools/` | Build, packaging, and USB copy/verify tools. |
| `packaging/` | NSIS installer (Windows) and AppImage builder (Linux). |
| `assets/` | Launchers and icons. |

## What we are building

A portable, self-contained desktop app that runs straight from a USB flash
drive on **both Windows 10/11 and Linux x86_64**, for a non-technical landlord.

One codebase, two PyInstaller builds, one shared `KeKarData/` portfolio on the
drive. All data stays local; only the AI chat needs the network.

## Download

The current release is
[v1.2.0](https://github.com/Ryuupyroxi/KeKar/releases/tag/v1.2.0) — Airbnb-style
short stays. Pre-built packages are attached to every
[GitHub release](https://github.com/Ryuupyroxi/KeKar/releases):

- **Windows** — `KeKar_Windows.zip`: unzip, then double-click `KeKar.bat`.
  SmartScreen may warn on first run because the build is not code-signed;
  click **More info → Run anyway**. From the release after v1.2.0 the job also
  attaches `KeKar_Setup_<version>.exe`, which copies the package to
  `%LOCALAPPDATA%\KeKar` and adds Desktop and Start-menu shortcuts; the zip
  stays the no-install path.
- **Linux** — `KeKar_Linux.zip`: unzip, then double-click `KeKar.sh`, or run
  `./install_linux.py --desktop` for a menu entry and a Desktop shortcut.

Your data lives in the `KeKarData` folder next to the program, so the whole
package can be copied to any PC or USB drive.

## Status

Implementation complete through Phase 7. **387 tests passing** (`pytest -q`).
Source: 64 modules, 9,266 lines.

| Phase | State |
|---|---|
| 0 — Scaffold, paths, config, build pipeline | done |
| 1 — Data layer (SQLite, repos, backup/recovery) | done |
| 2 — Offline services (listing compiler, clipboard, images) | done |
| 3 — In-app agent (soul, memory, LLM client, tools, loop) | done |
| 4 — GUI (shell, drawer, form, photos, CRM, chat, wizard, settings) | done |
| 5 — Browser automation (launcher, CDP, Marketplace autofill) | done |
| 6 — Packaging and USB deployment | done |
| 7 — Hardening, testing, release | in progress — human test matrix pending |

### Phase 7 progress

- Task 7.1 logging + exception hook — done (`src/logging_config.py`, wired in
  `src/main.py`; log rotates at 2 MB, keys redacted).
- Task 7.2 security review — done (`docs/SECURITY.md`, all boxes verified).
- Task 7.3 performance pass — done. All three targets measured and met;
  see `docs/PERFORMANCE.md`. Property list render went 463 ms → 69 ms for
  50 rows.
- Task 7.4 end-to-end test matrix — written, awaiting a human on real hardware.
- Task 7.5 release checklist — pending.

## Running KeKar

The zero-setup path is the launcher script:

- Windows: double-click `KeKar.bat`
- Linux: double-click `KeKar.sh`

For a real one-click icon on Linux (application menu plus a Desktop shortcut),
run the installer that ships in the package:

```bash
./install_linux.py --desktop
```

It writes `~/.local/share/applications/kekar.desktop` with the correct absolute
path, installs the icon into the hicolor theme, and marks the Desktop copy as
trusted so GTK will run it. Pass `--uninstall` to remove it.

The entry records an absolute path, so if the USB drive's mount point changes,
run the installer again after plugging it in.

## AI providers

The assistant talks to any OpenAI-compatible endpoint. The provider is detected
from the key's format, so pasting a key usually configures everything:

| Key starts with | Provider | Endpoint |
|---|---|---|
| `sk-or-` | OpenRouter | `https://openrouter.ai/api/v1` |
| `sk-proj-`, `sk-svcacct-` | OpenAI | `https://api.openai.com/v1` |
| `gsk_` | Groq | `https://api.groq.com/openai/v1` |
| `csk-` | Cerebras | `https://api.cerebras.ai/v1` |
| `xai-` | xAI | `https://api.x.ai/v1` |
| `sk-` (generic) | OpenAI **or** DeepSeek | probed to decide |

To switch providers, open **File → Settings**:

- **Provider** — pick one; the endpoint and its default models fill in.
- **Detect from key** — identify the provider from the key, confirm it works,
  and apply it.
- **Fetch the provider's model list** — list what the provider actually
  offers, filter it, and tick the models to use. Models are tried in order.
- **Test connection** — a real one-token completion. It quotes the provider's
  own error, so "no credits remaining" is distinguishable from "bad key".

A key is never sent to a provider its format does not match. Google AI Studio
and Anthropic are detected but not usable directly, because their chat APIs are
not OpenAI-compatible; the app says so rather than guessing.

See `docs/WIRING.md` for how detection and model discovery are wired.

## Demo mode and guided tour

A new install offers a tour right after setup, and **Help → Guided tour...**
runs it any time. The walkthrough calls out the visible feedback after
**+ Add New Property**, the collapsible Photos section, and the centred header
logo.

The tour runs in **demo mode**: KeKar opens a separate demo database
(`KeKarData/demo/database.db`) seeded with four sample properties and four
applicants, so every panel has something to show. Your real database is closed
and never touched — not read, not written, not seeded. A blue banner under the
menu bar stays visible for as long as demo mode is on, and **Exit demo mode**
is in the Help menu and on the banner.

Demo mode is session-only. Nothing on disk records it, so closing the app
mid-tour brings you back to your real data on the next launch.

Settings are shared with the real install, so **File → Settings is disabled
while demo mode is active** — otherwise a tour could change your real API key.

See `docs/WIRING.md` for how the switch and the overlay are wired.

## Themes

**View → Follow system / Light / Dark / OLED** switches immediately, and the
choice is remembered in Settings (the same preference is in the Settings
dialog's Theme dropdown).

`system` follows your operating system's light/dark setting. `OLED` is pure
black for OLED screens and night use. Every palette must clear the WCAG contrast
ratios encoded in `src/ui/palette.py::required_pairs`, and the test suite
enforces it.

## The interface

The window is three regions: a property list on the left, tabs on the right,
and the assistant along the bottom. Each region is drawn as a card — a
two-pixel outline in the theme's `panel_border` colour, rounded corners and
its own fill — with the window colour showing through the splitter gutters, so
the three panels stay visually separate at any window size.

- **Property list** — each row is a cover thumbnail, the address as the title,
  and the city/ZIP underneath. Status is a coloured stripe on the left edge
  (green = Vacant, red = Rented), so the address is never crowded out by a
  badge. The search box is deliberately inclusive: it matches address, city,
  ZIP, pet policy, free-form notes **and every enabled amenity**, so
  "dishwasher" or "fenced yard" finds the right properties.
- **Properties tab** — a two-column form (Details, Amenities, Notes) that
  scrolls when the window is short, so no field is ever squeezed to nothing.
  **Type** switches the unit between a long-term rental and a short stay; the
  term group below Details swaps to match. Quick actions: Save, Copy listing,
  Preview listing, Publish to Marketplace, Mark as rented / vacant, Delete.
- **Photos** — import, thumbnail, set cover, delete. The cover becomes the
  row's thumbnail in the list. The section collapses from its own header and
  remembers the choice between runs.
- **Applicants tab** — a table of applicants with a colour-coded screening
  stage (Inquiry Received → Questionnaire Sent → Background Check →
  Approved / Rejected). Adding an applicant asks which property they are
  applying for. Pre-screening questions copy to the clipboard in one click.
- **Leases tab** — draw up a lease from the example lease your client provided.
  Load it once (paste it, or open the file) and it becomes the template;
  `{{address}}`, `{{rent}}`, `{{tenant}}` and the rest are filled in for the
  selected property and tenant. Generate, then **copy**, **print** or **email**
  the result, or save it to the lease list. KeKar never sends mail itself —
  the email button opens your own mail app with the lease pre-filled.
- **Stays tab** — reservations for Airbnb-style units: a month calendar with
  the booked days marked, a table (guest, portal, dates, nights, payout,
  status, source), and add / edit / cancel / delete. A stay cannot overlap
  another one on the same property; a cancelled stay frees its dates.
- **Panels** — the property list and the assistant collapse to the edge. Two
  buttons at the right end of the menu bar toggle them (their arrows show
  which way the panel will move), and **View** lists the same two actions.
  Both are 32 px tall, so they work as pointer targets rather than menu-bar
  crumbs.
  The layout is remembered between runs.
- **Assistant** — the chat pane talks to the in-app agent, which can only call
  whitelisted tools (never raw SQL, never `eval`). Offline is handled with a
  banner and a status pill rather than a crash.

## Listing channels

The Properties tab's **Preview listing** dialog picks a channel. The list
follows the property's **Type**: a rental sees the long-term sites, a short stay
sees the portals.

- **Any site (generic)** — the template from `config/listing_templates.json`;
  a short stay gets its own generic template.
- **Zillow** and **apartments.com** — a package shaped like that site's form:
  a title, a body, and every field the site asks for separately, plus the
  warnings that matter (title length, missing rent or square footage).
- **Airbnb**, **Vrbo** and **Booking.com** — the short-stay equivalent: a
  per-night title, a body carrying the cleaning fee, extra-guest fee, minimum
  stay, occupancy and check-in/out times, and each of those as a separate field.

Neither Zillow nor apartments.com offers an API for creating a rental listing,
and the three portals offer none for an independent host; all of them sit behind
a logged-in session, so KeKar builds the listing and the user pastes it. Posting
always stays with the person. Facebook Marketplace keeps its opt-in browser
auto-fill, which fills a draft and stops before Publish.

## Short stays and portal calendars

A property with **Type → Short stay (Airbnb)** carries its own terms (nightly
rate, cleaning fee, extra-guest fee, minimum stay, occupancy, check-in/out
times, Instant Book, cancellation policy, house rules) and a **Portals** group
with one row per portal: enable it, override the price or the minimum stay for
that portal only, paste the portal's own iCal URL, and **Sync now** to import
its calendar. **Export calendar (.ics)…** writes the property's bookings as an
iCal file to upload to a portal.

KeKar owns the bookings and the per-portal pricing; the calendar is the only
two-way channel the portals offer without a partner agreement. Every import
upserts by the event's `UID` (so a re-sync updates rather than duplicates) and
writes a `portal_sync_log` row; a network or parse failure is reported with its
own message rather than raised. Blocked dates and bookings are the same thing —
the calendar marks both, and the export emits both.

Posting to a portal, two-way message sync and a paid channel manager are
deliberately out of scope; `docs/superpowers/specs/2026-11-15-airbnb-short-stay-design.md`
records the reasoning.

## Branding

Two supplied assets are used, and each has its own job:

- **`kekar-mark.png`** (the house/"A" mark) → the **icon**. Centred on a
  transparent square so the proportions survive, then written as
  `kekar.ico` with 7 frames (16, 24, 32, 48, 64, 128, 256) and expanded into
  the hicolor PNGs Linux launchers look for. `Application` and `MainWindow` both
  set it as the window icon, so the title bar, taskbar and start menu all show
  it.
- **`kekar-logo.png`** (the wordmark with the tagline) → the **logo**. It has a
  real alpha channel, so it composites onto any theme. It appears left-aligned
  in a slim strip at the top of the window and centred in the About dialog.

`tools/build_icon_assets.py` rebuilds the square master and the `.ico` from the
mark; `tools/make_icons.py` then regenerates the hicolor PNGs. `KeKar.spec`
already ships `src/resources`, so the frozen build picks all of it up. The
stretching alternative was rejected — the mark is 228x269, and squashing it to a
square would visibly distort the house.

The same art reaches the packages. `KeKar.spec` sets `kekar.ico` as the Windows
executable icon; `tools/make_usb_package.py` stages it at the Windows package
root, where the NSIS installer and its Desktop/Start-menu shortcuts read it;
and `packaging/linux/` carries `kekar.png` beside a `.desktop` entry whose
`Icon=kekar` gives the AppImage a real launcher icon instead of a placeholder.

## Accounts and login

**File → Accounts** manages the accounts, and **File → Lock session** hides the
portfolio. This is the plumbing for the client-facing feature that needs a
login; the portal itself is not built yet.

- Passwords are PBKDF2-HMAC-SHA256, 310,000 iterations, a fresh 16-byte salt per
  password, via `cryptography` (already a dependency — nothing new to install).
  A password is never stored in plaintext or in a reversible form.
- Sessions are random 32-byte tokens with a 7-day expiry, stored in a `sessions`
  table and re-checked on every launch. An expired token is dropped and purged.
- Wrong usernames are answered without running the KDF, so a failed guess costs
  the same whether or not the account exists. The dialog says only "not
  recognised", never which half was wrong.
- **Off by default.** `require_login` is false until you turn it on, so nothing
  about the app changes — and a login can never be demanded before an account
  exists, because Accounts refuses to enable it with zero accounts.
- A minimum of one account is enforced, so the owner cannot lock themselves out.

The window is the unit of locking: `set_locked()` swaps the central widget for a
login panel, so a locked window shows nothing of the portfolio rather than a
greyed-out one.

## Verified by real execution

- `bash build.sh` produces a working Linux one-folder build (`dist/KeKar`).
- `dist/KeKar/KeKar --version` prints `KeKar 1.2.0` on a headless machine.
- The built binary starts, creates `KeKarData/`, runs the schema migration, and
  reports `PRAGMA integrity_check = ok`. Confirmed by running the binary.
- `tools/make_usb_package.py` + `tools/verify_usb.py` pass on the real build.
- `tools/copy_to_usb.sh` copied 553 files to a mock drive and verified every
  SHA-256.
- `assets/launchers/KeKar.sh` launches the built app from any working directory,
  including from a copy of the package on another path.
- `tools/install_linux.py --desktop` writes a validated `.desktop` entry plus
  icon-theme PNGs. `desktop-file-validate` reports the entry clean, and
  launching it on a real display opens the KeKar main window.
- The packaging pass was verified on a rebuild: `packaging/linux/kekar.png` is a
  square PNG, the AppImage `.desktop` names `Icon=kekar`, and the Windows
  package stages `kekar.ico` at its root (`tests/test_usb_packaging.py`).
- `bash build.sh` ran the suite and PyInstaller end to end; the rebuilt
  `out/KeKar_Linux` ships `kekar-logo.png`, `kekar-mark.png` and `kekar.ico`
  under `_internal/resources/icons/`.
- `tools/seed_first_run.py` writes an encrypted key and the resulting settings
  file loads back with `is_configured() == True`.
- The app was launched on a real display and screenshotted: the property list,
  the populated form (address, rent, bedrooms, amenities) and the photo panel
  all render with readable text at 1280x800.
- The Leases tab was run on a real display: the template editor shows the
  example lease with its `{{markers}}`, and the preview shows the generated
  lease with the address, landlord, tenant and today's date substituted.
- The listing dialog was run on a real display with Zillow selected: title,
  body and the per-field list all render, and the channel dropdown offers
  generic, Zillow and apartments.com.
- Both collapsible panels were toggled on a real display: the sidebar and the
  chat collapse to the edge, and the menu-bar buttons stay visible with their
  arrows flipped to the expand direction.
- Startup crash fixed and re-verified. A `QThread` was destroyed while its
  thread was still unwinding, which makes Qt abort the whole process. It was a
  race, so it survived casual testing: 2 of 15 launches died. After the fix
  (`src/ui/worker.py`), 25 of 25 launches survived.
- The short-stay UI was run on a real display at 1280x800 in Light, Dark and
  OLED: the **Type** selector swaps Rental terms for Short-stay terms and the
  Portals group, the Stays tab marks the booked days on the calendar and lists
  the stay, and the listing dialog offers generic, Airbnb, Booking.com and
  Vrbo with the per-portal override applied and named.
- A v1.1-shaped database (every rental column, none of the short-stay ones) was
  opened by the current code and gained the columns in place; its existing row
  still reads as a long-term rental (`tests/test_short_stay.py`).
- The **frozen** build was launched on a real display with a short-stay property
  and a booking: the drawer row reads "Short stay ·", the Type selector shows
  "Short stay (Airbnb)", and the Stays tab renders the calendar with the
  booked days and the booking row — proving the new modules are inside the
  bundle rather than only importable from source.

### Security review

See `docs/SECURITY.md`. Runtime dependencies were audited and raised:
`cryptography` 45.0.7 → 50.0.2 and `Pillow` 11.1.0 → 13.0.0, closing 53
pip-audit findings. Remaining findings are recorded with reasons.

The API key is encrypted at rest (AES-256-GCM), its key file is `0600`, and it
is redacted from every log line, dialog and crash report. It is never written
to the database.

### Known gaps before release

- `docs/TEST-MATRIX.md` scenarios 1-18 need a human on real hardware, and the
  new short-stay scenarios 26-31 with them.
- Windows artifact requires a GitHub Actions run (no Windows machine here).
- Marketplace autofill is implemented but untested against the live Facebook DOM.
- Portal sync is verified against a local calendar fixture, not against a live
  Airbnb/Vrbo/Booking.com export URL.
- Releases up to and including v1.2.0 carry the two zips only; the NSIS
  installer is built and attached by CI from the next release onward.
- Nothing has been run on real Windows hardware by us — CI builds and packages
  the Windows artifacts, and the human pass in `docs/TEST-MATRIX.md` is written
  but unrun.

## Source documents (kept outside this folder, referenced by the plan)

- Spec: `/home/Ryuu/Documents/KeKar - Digital Property Manager Specification.pdf`
- Proposal: `/home/Ryuu/Fenrys-Backup/hermes/profiles/fenrys/KeKar_Rental_Properties_Proposal.pdf`
