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

The rule: **anything read at runtime must either be declared in `KeKar.spec`
or embedded in Python.** `tests/test_bundle_safety.py` and
`tests/test_usb_packaging.py` exist to keep this true.
