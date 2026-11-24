# KeKar — Runtime Wiring

How the pieces connect when the app is running. Read this before changing
anything that crosses a module boundary.

## Startup sequence

```
KeKar [--version|-V|--help|-h]     <- handled before Qt is imported
  └─ src/main.py::main()
       ├─ src.logging_config.configure_logging()      -> KeKarData/logs/kekar.log
       ├─ src.logging_config.install_exception_hook()
       ├─ src.app.Application(argv)                   <- the QApplication
       │    ├─ Settings.load()                         <- KeKarData/config/settings.enc
       │    ├─ open_with_recovery(None)                <- Database + integrity check
       │    │    └─ Database.__init__ -> _configure() -> _migrate()
       │    │         ├─ embedded_schema()             <- src/data/_schema_embedded.py
       │    │         └─ _add_missing_columns()        <- idempotent ALTER TABLE
       │    ├─ PropertyRepo / ApplicantRepo / LeaseRepo
       │    │    BookingRepo / PortalRepo / ChatRepo
       │    ├─ MemoryStore()                           -> KeKarData/memory/MEMORY.md
       │    ├─ LLMClient(settings)
       │    ├─ ToolContext(db, repos, memory, settings)
       │    ├─ AgentRunner(client, settings, ctx)
       │    ├─ MainWindow(self)
       │    └─ prune_backups(keep_days)
       ├─ if not settings.is_configured(): FirstRunWizard(app).exec()
       └─ app.show_main_window(); app.exec()
```

## Data flow

```
UI (src/ui/*)
  │  never contains business logic, never writes SQL
  ▼
Services (src/services/*)        Repositories (src/data/*_repo.py)
  │  listing_compiler, clipboard,   │  own all SQL, parameter-bound
  │  image_service, browser/*       │
  ▼                                ▼
            Database (src/data/db.py)  ──▶  KeKarData/database.db
                                                     │
                                              WAL mode, integrity_check
```

## Schema migrations

`embedded_schema()` is the authoritative copy; `schema.sql` is regenerated
from it and `tests/test_bundle_safety.py` proves the two are byte-identical.
`CREATE TABLE IF NOT EXISTS` covers a fresh database and a brand-new table,
but it cannot add a column to a table an existing install already has, so
`Database._add_missing_columns()` runs an idempotent `ALTER TABLE` pass
against `PRAGMA table_info` after the schema script. That is how the
short-stay columns reached databases created by v0.1.0 without a reset.
`SCHEMA_VERSION` stays at 1 — the change is additive.

## Thread safety

`Database` hands each thread its own connection (`threading.local`). sqlite3
pins a connection to the thread that created it, and the agent's tools run in a
worker `QThread` — sharing one connection made every tool call die with
"SQLite objects created in a thread can only be used in that same thread".
Per-thread connections plus WAL mode (one writer, many readers) is the fix.

Repositories resolve `self.conn` lazily through the `Database`, so the same
repo object works in the GUI thread and in the agent's worker thread. Passing a
raw connection is still accepted for tests and one-off scripts.

`Application.data_changed` is emitted by `dispatch_tool` after any tool in
`MUTATING_TOOLS` and is connected to `MainWindow.reload_all`. The agent writes
from its worker thread, so without it the sidebar kept showing stale data until
the next manual reload. The signal is queued by Qt to the GUI thread, which is
the only place widgets may be touched.

## Agent loop

```
ChatPane -> AgentRunner.run(message)
  │
  ├─ builds messages: [system soul] + [MEMORY.md] + [chat history] + user
  ├─ LLMClient.complete()  -> tries Settings.model_chain in order
  │
  └─ for each tool_call (max Settings.max_agent_steps):
       ToolContext.dispatch(name, args)
         -> whitelist lookup in TOOL_SCHEMAS
         -> calls a repository function (never raw SQL)
         -> result appended to the transcript
```

The model can only call whitelisted functions. There is no path from a tool
call to `eval`, `exec`, or a raw SQL string.

## Themes

`src/ui/palette.py` holds one `Theme` per appearance — light, dark, OLED — and
`src/ui/theme.py::build_stylesheet` renders the QSS from the active palette. The
stylesheet is generated rather than shipped as a file, so a theme is a single
switch and a stored stylesheet cannot drift from the code that paints the rest
of the UI.

`Settings.theme` is `system | light | dark | oled`, default `system`.
`system` is re-read on every launch from `QGuiApplication.styleHints()
.colorScheme()`, so following the OS needs no caching. An unrecognised value
falls back to light rather than raising.

Switching is immediate: `Application.apply_theme` sets the generated stylesheet,
emits `theme_changed`, and calls `MainWindow.apply_theme`, which pushes the
palette into every widget that paints its own colours — the painted property
rows, chat bubbles, banners, status pill, photo borders, tour caption and CRM
stage tints. Those cannot be reached by a stylesheet alone.

Status hues (vacant, rented, the pipeline stages) keep their meaning in every
theme; only their brightness moves. `required_pairs()` in palette.py encodes
the WCAG ratios each palette must meet, and `tests/test_themes.py` asserts
them, so a palette edit that breaks contrast fails the suite rather than
shipping.

### Panel cards

The three top-level regions (property list, tab area, assistant) are cards:
a two-pixel `panel_border` outline, a 10 px radius and the `panel` fill, with
the window colour left in the splitter gutters. `panel_border` is a separate
palette field from `border` — `border` is for inner hairlines (list row
separators, table gridlines, header rules) and `panel_border` is for the
outlines that separate one region from another, so it is held to a stronger
contrast floor (1.5:1 against the window) than a decorative separator.

A region opts in with `setProperty("panel", True)` plus
`setAttribute(WA_StyledBackground, True)`. The attribute matters: without it
Qt draws the card's border but not its fill, so the panel silently reverts to
the window colour. Content widgets inside a card (list, table, chat transcript,
tab pane) have their own borders switched off by descendant rules, so a region
never draws two nested outlines.

## Interface wiring

```
MainWindow (src/ui/main_window.py)
  ├─ PropertyDrawer (left)  ──property_selected──▶ PropertyForm.load_property()
  │     │                          └──────────▶ PhotoPanel.load_property()
  │     ├─ add_requested ──▶ MainWindow._new_property(): Properties tab to front,
  │     │                    form cleared, scrolled to the address field, and a
  │     │                    status-bar hint ("New property — … press Save.")
  │     └─ search box filters on PropertyDrawer.search_text(prop)
  │           (address, city, ZIP, pet policy, notes, enabled amenities)
  ├─ QTabWidget
  │     ├─ Properties tab = PropertyForm inside a QScrollArea + PhotoPanel
  │     │     ├─ kind_combo → _on_kind_changed() swaps Rental terms /
  │     │     │  Short-stay terms, shows Portals, relabels publish_btn
  │     │     └─ PhotoPanel: the "Photos" header is the collapse control;
  │     │        toggle_collapsed() hides the body (buttons + thumbnails)
  │     │        and persists settings.photos_collapsed
  │     ├─ Applicants tab = CrmTab (stage combo box, colour per stage)
  │     ├─ Leases tab = LeaseTab (template editor, preview, saved list)
  │     └─ Stays tab = StaysTab (QCalendarWidget + bookings table)
  ├─ ChatPane (bottom) ──▶ AgentRunner
  ├─ OfflineBanner + StatusPill ◀── _PingThread every 30 s
  │     └─ connectivity.provider_reachable(api_base)  (plain TCP, no API key)
  └─ menu: Settings → SettingsDialog, Help → AboutDialog

CollapsibleSplitter (sidebar | tabs) and (content | chat)
  └─ both are QSplitters; the handle paints a grip only
  └─ menuBar().setCornerWidget(holder) → sidebar_toggle + chat_toggle
        └─ CollapsibleSplitter.toggle_pane(index)  →  collapse() / is_collapsed()
              └─ _remember_layout() persists sidebar_collapsed / chat_collapsed
```

`src/ui/theme.py` is the single source of typography (`DejaVu Sans`, 11 pt);
widgets that need emphasis call `font(points, bold)`. `src/ui/widgets.py`
holds the shared `StatusPill`, `OfflineBanner` and `SectionLabel`.

The property form is wrapped in a `QScrollArea` with `setWidgetResizable(True)`
so a short window scrolls instead of squeezing the group boxes flat. Because
the form is taller than its viewport, `_new_property()` also resets the scroll
bar to the top: a click that cleared fields while the view sat on Notes looked
like nothing had happened at all.

## Property list rendering

Rows paint themselves in one `paintEvent` rather than building a child widget
tree. A tree of five widgets per row cost ~10 ms, which put 50 rows at ~460 ms;
a painted row is ~1 ms. Cover paths are resolved in a single pass by the
drawer, and thumbnails are generated on a `QThreadPool` (capped at 4 threads)
with the pixmap built on the GUI thread — `QPixmap` is not valid off the GUI
thread. See `docs/PERFORMANCE.md` for measurements.

## Worker threads

Every background operation (`_PingThread`, `_VerifyThread`, `_AutofillThread`,
`_AgentThread`) goes through `src/ui/worker.py`. The registry owns each
thread; the completion slot calls `worker.reap(thread)`, which waits for the
thread to finish *before* releasing it.

The order matters. Deleting a `QThread` whose thread is still unwinding makes
Qt call `qFatal` and abort the entire process — no Python exception hook runs,
no dialog, just a dead app. That is a race, so it passes casual testing: the
app crashed on roughly 1 in 7 launches until this was fixed.

Two rules, therefore: never drop the last reference to a running thread, and
never call `reap()` from the worker thread itself.

## AI provider detection

`src/agent/providers.py` holds the provider presets and three operations:
`detect()` (prefix match), `fetch_models()` (`GET /models`), and `probe()` (one
minimal completion). `LLMClient` wraps them as `list_models()` and
`verify_key()`.

Prefix matching takes the **longest** match only, because `sk-proj-…` also
starts with DeepSeek's generic `sk-`. Ties at the longest length are all
returned — a plain `sk-` key means OpenAI or DeepSeek, and the settings dialog
probes both rather than guessing. Guessing would send a key to the wrong host.

The default chain for OpenRouter is `openrouter/free` first. That is
OpenRouter's free-models router: it picks whichever free model is available, so
it keeps working as the free catalogue changes, and it needs no credits. The
named `:free` models behind it are fallbacks for when the router itself is rate
limited. A fresh install therefore works with a free-tier key and no top-up.

`verify_key()` deliberately makes a completion rather than calling `/models`:
on OpenRouter and OpenAI that endpoint is public and answers 200 for any key,
so it reported "Connected" for a key the chat endpoint then rejected with 401.
The probe also quotes the provider's own error message, because HTTP 429 covers
both "no credits" and "rate limited".

`migrate_default_provider()` repairs settings saved before detection existed —
a key pasted into the wizard used to leave the endpoint on the built-in default
forever. It only acts while the provider and endpoint are both still that
untouched default, so a deliberate choice or a custom proxy is never overridden.

## Demo mode

`paths.demo_database_path()` points at `<data_dir>/demo/database.db`. Everything
else — settings, memory, photos, logs — is shared with the real install.

Both database locations are resolved once in `Application.__init__` and reused.
Re-resolving on every switch would open a *different* file if the data directory
changed mid-run, silently losing the real database.

`enter_demo_mode()` closes the real database, opens the demo one, seeds it if
empty, rebuilds the repositories, reloads the views, and shows the banner.
`exit_demo_mode()` reverses it. Repositories resolve their connection lazily
through the `Database`, so rebuilding them is enough; no view is reconstructed.

Demo mode is session-only: nothing on disk records it, so a crash mid-tour
returns the user to real data. The Settings action is disabled while demo mode
is active, because settings are shared with the real install.

## Guided tour

`src/ui/tour.py` holds `TourStep`, `TourOverlay` and `build_tour_steps(window)`.

The overlay is a transparent child of the main window. `paintEvent` fills the
window with a dim colour clipped to everything *except* a hole around the
current target, then draws an amber ring around it — no composition modes, so
it cannot fail on a platform that dislikes `CompositionMode_Clear`.

The overlay is modal: it captures clicks, so the tour is a guided walkthrough
rather than free play. `Esc` exits, arrow keys navigate, and the Applicants step
switches to that tab and restores the previous one on exit.

The overlay installs an event filter on the main window for the duration of the
tour, because a child widget does not resize itself when its parent does —
without it the dim layer leaves the area exposed by a resize uncovered. It
emits `closed` before destroying itself so the window drops its reference
instead of calling into a deleted object later.

Starting a tour finishes any tour that is already running, so two overlays can
never stack.

Both starting and leaving demo mode wait for a running assistant: swapping the
database underneath an in-flight agent would make its answer describe
whichever database it lands on.

A step callback receives the overlay running it, never looked up by `findChild`
— a stale overlay left behind by an earlier tour would otherwise receive the
state and the tab would never be restored.

## Marketplace publishing

```
PropertyForm.publish_btn
  └─ MarketplaceDialog(app, prop)
       └─ _AutofillThread (QThread, so the UI never freezes)
            ├─ launcher.is_debug_port_open() -> launch_browser() if needed
            ├─ CDPClient.connect()
            └─ MarketplaceAutomation.autofill_listing(prop)
                 └─ fills title / price / description / photos, then RETURNS
       └─ _on_done(result) -> plain-language report in the dialog
```

The thread reports `autofilled`, `needs_review` or `failed`. In every case the
dialog says plainly that nothing was published and points at **Copy listing**
as the reliable fallback. Auto-fill is off unless the user enables it in
Settings, and it can never click Publish.

## Listing channels

```
PropertyForm.preview_listing_btn          ("Portal listing…" for a short stay)
  └─ ListingDialog(app, prop)
       └─ QComboBox: generic | the channels for prop.kind
            ├─ generic      → listing_compiler.compile_listing(prop)
            │                   (short_stay template for a short stay)
            └─ a channel    → listing_channels.compile_channel(
            │                    prop, channel,
            │                    price_override, min_stay_override)
            │                 └─ overrides come from PortalRepo.get(prop.id,
            │                    channel); 0/None means "use the property's"
            ├─ title  (per-site length limit)
            ├─ body   (per-site wording)
            ├─ fields (each field the site's form asks for)
            └─ warnings (title length, missing price/sqft or occupancy)
```

Zillow and apartments.com have no posting API, and Airbnb, Vrbo and
Booking.com have none for an independent host, so the dialog produces a copy
package rather than posting. Facebook Marketplace keeps its own opt-in
autofill path above.

## Short stays and portal calendars

```
PropertyForm.kind_combo ─▶ _on_kind_changed()
  ├─ rental_terms  vs  short_stay_terms + portals_box
  └─ publish_btn text: "Publish to Marketplace..." | "Portal listing…"
       └─ _publish_or_list() branches on the same flag

Portals group (per portal row)
  ├─ enabled / price_override / min_stay_override / external_ical_url
  │    └─ _save_portals() → PortalRepo.save()   (after the property is saved)
  ├─ Sync now → _PortalSyncThread → portal_sync.sync_portal(db, prop, portal)
  │    ├─ ical_service.fetch_ical(url)          (urllib, 20 s timeout)
  │    ├─ ical_service.parse_ical(text)         (folds lines, DATE/DATE-TIME)
  │    ├─ upsert by external_uid → BookingRepo.create/update(source='ical')
  │    ├─ PortalRepo.mark_synced() + PortalRepo.log()
  │    └─ done signal → GUI thread → status + reload_all()
  └─ Export calendar (.ics)… → ical_service.export_ical(prop, bookings)
       └─ KeKarData/calendar/<address-slug>.ics

StaysTab
  ├─ property_combo → _refresh() → BookingRepo.list(property_id)
  ├─ QCalendarWidget days painted from BookingRepo.booked_dates()
  └─ Add / Edit / Cancel / Delete → BookingRepo (nights derived on write,
       overlap rejected in the repository, a cancelled stay frees its dates)
```

`ical_service` parses and writes RFC 5545 by hand — no third-party dependency
in the frozen build. A cancelled booking is left out of the export; a blocked
one is emitted as `STATUS:CONFIRMED` with the summary `Blocked`.

The sync never raises for a network or parse problem: the failure is written
to `portal_sync_log` and returned, so the UI can quote it.

## Leases

```
LeaseTab
  ├─ template editor  ←  settings.lease_template, or the built-in default
  │     └─ "Load example lease…" reads a .txt/.md file; "Save as template"
  │        writes settings.lease_template (encrypted with the rest of Settings)
  ├─ Generate → lease_builder.render(template, tokens_for(prop, tenant, …))
  │     └─ {{marker}} substitution only; unknown markers are left in place
  │        and listed in the "KeKar does not fill" note
  ├─ Copy   → clipboard.copy_text
  ├─ Print  → QPrintDialog + QTextDocument.print(QPrinter)
  ├─ Email  → QDesktopServices.openUrl("mailto:?subject=…&body=…")
  │     └─ KeKar holds no SMTP credentials; the user's own mail app sends it
  └─ Save   → LeaseRepo (leases table) → saved-leases combo box
```

`LeaseRepo` resolves its connection lazily through `Database`, so it is safe
from a worker thread like every other repository.

## Branding

```
src/resources/icons/
  ├─ kekar-mark.png     the supplied mark (228x269, alpha)
  ├─ kekar-master.png   mark centred on a 256x256 transparent square
  ├─ kekar.ico          7 frames: 16 24 32 48 64 128 256
  ├─ kekar-<size>.png   hicolor sizes for Linux launchers
  └─ kekar-logo.png     the supplied wordmark + tagline (1408x768, alpha)

paths.icon_path() / paths.logo_path()  →  resource_path("icons", …)
        └─ frozen: _MEIPASS/resources/…   ·   dev: src/resources/…

Application.__init__   → self.setWindowIcon(QIcon(icon_path()))
MainWindow.__init__    → self.setWindowIcon(QIcon(icon_path()))
MainWindow             → logo_label centred in the header at HEADER_LOGO_HEIGHT
                         (96 px), _set_logo(); the strip is exactly the logo's
                         own height, so there is no empty band above or below
AboutDialog             → logo_label centred at 96 px, word-wrapped body
```

The mark is not square, so it is letterboxed onto a transparent square rather
than stretched. `_set_logo` degrades silently if the file is missing — a missing
logo must not stop the window opening.

## Accounts and login

```
File → Accounts ────────▶ UsersDialog
                          ├─ UserRepo.create / set_password / delete
                          └─ settings.require_login  (refused with 0 accounts,
                                                     and the last account cannot
                                                     be removed)

File → Lock session ────▶ MainWindow.set_locked(True)
                          ├─ parks the real central widget
                          └─ setCentralWidget(lock panel) + show()

Lock panel "Log in" ─────▶ Application.unlock_with_dialog()
                          └─ LoginDialog.exec() → Application.login()
                               ├─ UserRepo.authenticate(username, password)
                               │    └─ auth.verify_password → PBKDF2-HMAC-SHA256
                               │       (unknown username still runs one KDF)
                               ├─ UserRepo.create_session() → 7-day token
                               └─ settings.session_token saved

Application.__init__ ────▶ _restore_session()
                          └─ UserRepo.session_user(token); expired → cleared
main.py ─────────────────▶ app.maybe_require_login() before the tour offer
```

`src/services/auth.py` owns hashing, tokens and expiry; `src/data/user_repo.py`
owns the rows. Nothing here is wired to a portal — it exists so the feature that
needs a login has real accounts to check against.

Locking swaps the central widget rather than disabling the contents, so a locked
window reveals nothing. Qt hides a swapped-out central widget and does **not**
unhide it when it is swapped back, so `set_locked(False)` calls `show()`
explicitly; without that the portfolio returns invisible with no error.

## Browser automation

```
MarketplaceAutomation(cdp, selectors)
  ├─ selectors from config/marketplace_selectors.json (versioned)
  │    └─ falls back to DEFAULT_SELECTORS if the file is missing
  ├─ cdp.navigate(listing_url)
  ├─ cdp.fill(title | price | description)
  ├─ cdp.upload_files(photos, first 12)
  └─ RETURNS. It never calls cdp.click on Publish.
```

`launcher.py` starts the user's Chrome/Edge with `--remote-debugging-port` and
a dedicated `--user-data-dir` inside `KeKarData/browser_profile/`, so the
user's own browser session is never touched.

## Path resolution

`src/paths.py` is the only module that knows where data lives:

```
KEKAR_DATA_DIR env var
  -> <exe_dir>/../KeKarData      (recommended: shared drive root)
  -> <exe_dir>/KeKarData         (app-local fallback)
  -> OS app-config dir           (last resort, warns the user)
```

Every other module imports paths from here. Never construct a data path by
string concatenation elsewhere.

## Frozen vs. development

| Resource | Dev | Frozen |
|---|---|---|
| `schema.sql` | embedded Python string (authoritative) | same — the `.sql` file is intentionally not shipped |
| `config/*.json` | read from project `config/` | read from `_MEIPASS/config/` |
| `config/default_config.json` | file, falls back to `DEFAULTS` | same |
| `config/listing_templates.json` | file, falls back to `DEFAULT_TEMPLATE` | same |
| `config/marketplace_selectors.json` | file, falls back to `DEFAULT_SELECTORS` | same |
| `src/resources/styles.qss` | *removed* — the stylesheet is generated from the active palette (`src/ui/palette.py`, `src/ui/theme.py`) | n/a |

The rule: **anything read at runtime must either be declared in `KeKar.spec`
or embedded in Python.** `tests/test_bundle_safety.py` and
`tests/test_usb_packaging.py` exist to keep this true.
