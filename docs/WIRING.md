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
       │    │         └─ embedded_schema()             <- src/data/_schema_embedded.py
       │    ├─ PropertyRepo / ApplicantRepo / ChatRepo
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

## Interface wiring

```
MainWindow (src/ui/main_window.py)
  ├─ PropertyDrawer (left)  ──property_selected──▶ PropertyForm.load_property()
  │     │                          └──────────▶ PhotoPanel.load_property()
  │     └─ search box filters on PropertyDrawer.search_text(prop)
  │           (address, city, ZIP, pet policy, notes, enabled amenities)
  ├─ QTabWidget
  │     ├─ Properties tab = PropertyForm inside a QScrollArea + PhotoPanel
  │     └─ Applicants tab = CrmTab (stage combo box, colour per stage)
  ├─ ChatPane (bottom) ──▶ AgentRunner
  ├─ OfflineBanner + StatusPill ◀── _PingThread every 30 s
  │     └─ connectivity.provider_reachable(api_base)  (plain TCP, no API key)
  └─ menu: Settings → SettingsDialog, Help → AboutDialog
```

`src/ui/theme.py` is the single source of typography (`DejaVu Sans`, 11 pt);
widgets that need emphasis call `font(points, bold)`. `src/ui/widgets.py`
holds the shared `StatusPill`, `OfflineBanner` and `SectionLabel`.

The property form is wrapped in a `QScrollArea` with `setWidgetResizable(True)`
so a short window scrolls instead of squeezing the group boxes flat.

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
| `src/resources/styles.qss` | file, falls back to no stylesheet | shipped in the bundle |

The rule: **anything read at runtime must either be declared in `KeKar.spec`
or embedded in Python.** `tests/test_bundle_safety.py` and
`tests/test_usb_packaging.py` exist to keep this true.
