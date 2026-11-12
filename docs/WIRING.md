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
