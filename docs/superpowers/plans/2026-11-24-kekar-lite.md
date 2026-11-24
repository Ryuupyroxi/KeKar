# KeKar Lite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a stripped-down, offline-only build of KeKar ("KeKar Lite") from the same source tree that removes the non-working external connections — Facebook Marketplace autofill, the AI chat assistant, short-stay portal calendar sync and (per K11) Google Maps address lookup — while preserving every local feature, above all the generic and per-site listing copy-and-paste packages.

**Architecture:** One codebase, two build variants selected by a generated, gitignored `src/_variant.py` stamp written by `tools/set_variant.py` and read through a single `src/features.py` switch module. Guards are placed at the composition roots (`Application`, `MainWindow`, `PropertyForm`, `ListingDialog`, `SettingsDialog`, `FirstRunWizard`, `main.py`, `tour.py`) and at the PyInstaller/USB-packaging boundary; no data-layer file, schema, repository, or settings field is changed, so both variants read and write the same `KeKarData/` portfolio interchangeably.

**Tech Stack:** Python 3.13 venv at `.venv` (project CI still targets 3.12) · PyQt6 · SQLite (`WAL`, embedded schema) · PyInstaller (`KeKar.spec`) · pytest 8/9 with `pytest-qt` conventions already in `tests/conftest.py` · GitHub Actions (`ubuntu-22.04`, `windows-latest`) · NSIS for the Windows installer · `tools/make_usb_package.py` / `tools/verify_usb.py`.

## Global Constraints

- **One source tree.** No fork, no second repository, no copied `src/` directory. The only variant-specific source file is the generated `src/_variant.py`, which is gitignored and restored by the tool that writes it.
- **Default is always `full`.** An unknown or absent `KEKAR_VARIANT` value resolves to `full`; a plain checkout, a plain `pytest`, and a plain `pyinstaller KeKar.spec` keep today's behaviour exactly.
- **Same data, same schema, no migration.** `src/data/schema.sql`, `src/data/_schema_embedded.py`, `SCHEMA_VERSION`, `KeKarData/` resolution in `src/paths.py`, and the `Settings` dataclass are byte-for-byte unchanged. Lite must never delete, reset, or refuse a full-KeKar database, and full KeKar must open a Lite-created database.
- **Offline-first.** KeKar Lite makes zero network calls in normal use: no provider ping, no API-key handshake, no iCal fetch, no CDP browser launch, no Google Places request. Every Lite feature works with the network unplugged.
- **Do not break existing KeKar users.** Full-mode tests that exercise the agent, Marketplace autofill, portals, tour wording, wizard, settings, and CLI keep passing unchanged. Settings written by full KeKar (including `api_key`, `autofill_enabled`, `browser_kind`, portal rows) load unmodified in Lite and are still present when the user switches back.
- **Listing copy-and-paste is never disabled.** `compile_listing`, `copy_listing`, `copy_text`, `validate_listing` and the surviving channel packages stay in both builds.
- **Test command:** `.venv/bin/python -m pytest -o addopts='' -q`. `pytest.ini` sets `addopts = -q`, so passing a second `-q` hides the summary line. `BASELINE` below means the `N passed` number printed by that command at the start of Task 1; every task must finish at or above `BASELINE` plus that task's new tests. Never copy a count out of `README.md`.
- **Test isolation:** `tests/conftest.py` forces `KEKAR_TESTING=1`, sets `QT_QPA_PLATFORM=offscreen` on headless Linux, gives every test its own `KEKAR_DATA_DIR`, and creates exactly one `Application`. Lite subprocess tests therefore use their own process, never a second `QApplication`.
- **Version alignment:** `packaging/windows/KeKar_Installer.nsi` carries its own `!define VERSION`; `tests/test_main_cli.py::test_app_version_matches_nsi_installer` fails on drift. Both variants keep the *same numeric* `APP_VERSION`; only the display name and artifact names change. Re-read both files at execution time and move them together if a parallel release has bumped them.
- **PyInstaller cannot cross-compile.** Each platform artifact is built on that platform's CI runner; the Linux job runs the suite, the Windows job builds and packages.
- **No placeholders.** Every code step below contains the exact code to write; every test step contains the exact assertion and the exact command to run.

---

## Key Decisions

Ambiguities in the request are resolved here. Each decision is named and is visible in the tasks below.

**K1 — One codebase with a build flag, not a separate repo.** The two products share one data model, one schema, one set of repositories and one test suite; only the composition roots differ. A fork would duplicate 64 modules and immediately drift, and would break the promise that a `KeKarData/` folder is portable between copies of the app. The flag is baked into the frozen build (`src/_variant.py`), with `KEKAR_VARIANT` honoured only for local development and tests so a shipped build cannot be flipped accidentally by an environment variable.

**K2 — "Direct connection" means any path that opens a socket, a browser, or a remote API.** That covers exactly three subsystems: Facebook Marketplace autofill (`src/services/browser/*`, `MarketplaceDialog`, the `marketplace_autofill` tool), the AI assistant (`src/agent/*`, `ChatPane`, `ChatRepo` usage, provider settings and key wizard), and portal calendar sync (`portal_sync.fetch` over `urllib`, the Portals group's "Sync now"). Local text generation, clipboard writes, manual bookings, lease rendering and photo handling stay. This is the line that keeps the request's "listing copy-and-paste options": they are pure local computation.

**K3 — The three named site packages are hidden in Lite; the copy-paste mechanism stays.** `CHANNELS` keeps every entry in `src/services/listing_channels.py` and `compile_channel()` still accepts every key — only the Lite channel *picker* is filtered. `LITE_HIDDEN_CHANNELS = {"apartments_com", "airbnb", "vrbo"}` removes exactly the sites the request names; `generic`, `zillow` and `booking_com` remain. Reason: the request explicitly names apartments.com, Airbnb and Vrbo as things to leave out, while explicitly keeping copy-and-paste; this reading honours both clauses without touching the data layer. If the intent was "remove connections only, keep all site packages", changing that one frozenset to `frozenset()` re-includes all three — no other task changes. Zillow and Booking.com are kept because they were not named and are working text-only paths.

**K4 — Portal calendar sync is removed for all three portals, including Booking.com.** `portal_sync` treats `PORTALS = ("airbnb", "vrbo", "booking_com")` as one mechanism and `README.md` records it as verified only against a local fixture, not a live export URL. Leaving a Booking.com "Sync now" row in Lite would keep a non-network-verified direct connection in an offline product. This is a deliberate extension beyond the two portals the request names; the trade-off is called out in the traceability matrix. Booking.com's *listing package* remains (K3), because that is copy-and-paste, not a connection.

**K5 — Product identity changes; data identity does not.** The Lite executable and folders are named `KeKarLite`; the displayed name is "KeKar Lite"; the numeric version is unchanged. Both builds use the identical `src/paths.py` chain (`KEKAR_DATA_DIR` → `<exe_dir>/../KeKarData` → `<exe_dir>/KeKarData` → OS fallback) and the identical `KeKarData/` folder on a USB package. Two apps sharing one folder is the same situation as two copies of KeKar today; no new conflict is introduced.

**K6 — `Settings` keeps every field.** Unused fields (`api_key`, `autofill_enabled`, `browser_kind`, provider/model data) stay in the encrypted blob. Dropping them would make a full-KeKar settings file unloadable after switching to Lite and back. The Lite UI simply does not show them.

**K7 — Short stays and the Stays tab stay.** Manual bookings, overlap rejection, the calendar, nightly/cleaning fees and minimum stay are local. The "Portal" column in the bookings table is preserved as a plain label on local data, not a connection; it still accepts "(direct)" and shows a stored value such as `airbnb` verbatim on a database opened from full KeKar. Nothing needs renaming there.

**K8 — Demo mode and the guided tour stay, with variant-aware wording.** They are local and are how a non-technical user learns the product. A tour that names a removed button is worse than no tour, so step text and step count become variant-dependent (`tests/test_tour.py` is updated in the same task).

**K9 — The `agent`, `browser`, `marketplace`, `chat_pane`, `portal_sync` and `ical_service` modules remain in the repository and in full builds.** "Stripped down" is achieved by not importing or bundling them in Lite, not by deleting code that full KeKar users still need. The only config file intentionally left unbundled in Lite is none: `config/` is shipped whole so `test_bundle_safety.py` keeps its invariants; the unused selector JSON is a 451-byte inert file.

**K10 — Build and release both variants from the same workflow.** A `strategy.matrix` over `variant: [full, lite]` produces `KeKar_{Linux,Windows}` and `KeKarLite_{Linux,Windows}` artifacts and four release zips. The Windows NSIS installer continues to install only the full build; a Lite installer is deliberately out of scope (the zip + launcher is the documented no-install path).

**K11 — Google Maps address suggestions are disabled in Lite.** This feature arrived in the v1.6.0 work that was in flight while this plan was written. It is another outbound call to a third party (`src/services/maps_service.py` → Google Places), so it falls under K2's offline-first rule even though the request did not name it. `features.maps_enabled()` returns `not is_lite()`; Lite never wires the `QCompleter` or the two `QThread` fetches, and `maps_key`/`maps_autofill` stay in `Settings` untouched (K6). This is a deliberate extra removal — if the intent is to keep address lookup in Lite, change `maps_enabled()` to `return True` and drop the two Lite-specific assertions in Tasks 4 and 6.

**Execution-time caveat.** The working tree was being changed concurrently (v1.6.0, Maps feature) while this plan was written. Before starting Task 1, re-read `src/ui/property_form.py`, `src/ui/settings_dialog.py`, `src/_version.py` and `tests/test_main_cli.py`; the line numbers cited below are anchors from the state at writing time, and the guards must be applied to whatever those files contain at execution time. Keep the guard semantics, not the line numbers.

---

## Scope: what disappears, what stays

| Capability | Full KeKar | KeKar Lite | How Lite achieves it |
|---|---|---|---|
| Property CRUD, amenities, notes, status | yes | **yes** | unchanged |
| Photos, cover image, collapsible Photos section | yes | **yes** | unchanged |
| Applicants / CRM pipeline | yes | **yes** | unchanged |
| Leases: template, generate, copy, print, email | yes | **yes** | unchanged |
| Manual short-stay bookings + calendar + overlap rule | yes | **yes** | unchanged |
| Generic listing compile + "Copy listing" / "Preview listing" | yes | **yes** | unchanged |
| Zillow and Booking.com copy packages | yes | **yes** | channel picker filtered, compiler untouched |
| Themes, panel collapse, branding, accounts/login | yes | **yes** | unchanged |
| Google Maps address suggestions (v1.6.0) | yes | **removed** | no completer wiring, no `maps_service` import; settings fields retained |
| Demo mode + guided tour | yes | **yes** | wording/step count variant-aware |
| Facebook Marketplace autofill (button, dialog, CDP, selectors, settings rows) | yes | **removed** | button/dialog not created; `playwright` not collected in bundle |
| AI chat pane, bottom pane, provider settings, key wizard, offline banner/ping | yes | **removed** | composition-root guards; no network in Lite |
| Portal rows, "Sync now", "Export calendar (.ics)" | yes | **removed** | `portals_box` not created |
| `apartments_com`, `airbnb`, `vrbo` channel packages | yes | **hidden in picker** | `features.visible_channels()`; compiler API unchanged |
| SQLite schema, tables, `property_portals`, `portal_sync_log`, `messages` | yes | **unchanged on disk** | no migration, no deletion |

---

## File Structure

**Create**

- `src/features.py` — the only switch module; every variant decision goes through it.
- `tests/test_features.py` — switch semantics.
- `tests/test_kekar_lite.py` — subprocess integration test for the Lite application object.
- `tests/test_lite_ui.py` — Lite widget-level tests (form, dialog, wizard, settings, tour).
- `tools/set_variant.py` — writes and restores the generated variant stamp around a build command.
- `tests/test_set_variant.py` — stamp write/restore behaviour.

**Modify**

- `src/app.py` — guard agent/memory/client construction and repository wiring.
- `src/main.py` — guard the first-run key wizard; use the variant-aware display name.
- `src/_version.py` — add `LITE_APP_NAME` and `display_name()`; leave `APP_NAME`/`APP_VERSION` alone.
- `src/ui/main_window.py` — no chat pane, no chat controls, no provider ping; variant-aware About text.
- `src/ui/property_form.py` — no publish button, no Portals group; keep Preview/Copy; variant-aware Type label.
- `src/ui/listing_dialog.py` — filter channels and reword the note.
- `src/ui/settings_dialog.py` — lazy provider import; hide key/provider/model/autofill/browser rows in Lite.
- `src/ui/wizard.py` — one welcome page in Lite, no API key requirement.
- `src/ui/tour.py` — variant-aware steps and wording.
- `tests/test_tour.py` — variant-aware expectations.
- `tools/make_usb_package.py`, `tools/verify_usb.py` — `--variant` for Lite package names/launchers/README.
- `tests/test_usb_packaging.py` — Lite layout tests.
- `KeKar.spec`, `build.sh`, `build.ps1`, `.github/workflows/build.yml`, `.gitignore` — build both variants.
- `README.md`, `docs/WIRING.md`, `docs/SPEC-COVERAGE.md`, `docs/TEST-MATRIX.md` — document the variant (in their own implementation tasks, not in this plan).

**Deliberately unchanged**

- `src/data/*` (all repositories, `db.py`, `models.py`, `schema.sql`, `_schema_embedded.py`, `demo_seed.py`).
- `src/services/listing_compiler.py`, `clipboard.py`, `image_service.py`, `lease_builder.py`, `ical_service.py`, `portal_sync.py`, `browser/*`.
- `src/config/settings.py`, `config/default_config.json`, `config/listing_templates.json`, `config/marketplace_selectors.json`.
- `src/agent/*`, `src/ui/chat_pane.py`, `src/ui/marketplace_dialog.py` — full builds still use them.

---

## Distribution & Portability

- **Build environment per target.** Linux artifacts are built on `ubuntu-22.04` (oldest supported glibc); Windows artifacts on `windows-latest`. `pyinstaller KeKar.spec` is run once per variant per OS with `KEKAR_VARIANT` set. PyInstaller does not cross-compile; there is no wine path.
- **Artifact layout.** Mirrors the existing package, with names swapped:
  ```
  out/KeKarLite_Linux/
  ├── KeKarLite_Linux/KeKarLite + _internal/
  ├── KeKarData/{photos,applicants,memory,config,backups,logs}/
  ├── KeKarLite.sh            (executable)
  └── README.txt              ("KEKAR LITE", no chat troubleshooting line)
  out/KeKarLite_Windows/      (KeKarLite.exe + _internal/, KeKarLite.bat, README.txt, KeKarData/)
  ```
  Release zips: `KeKarLite_Linux.zip`, `KeKarLite_Windows.zip`, attached on `release: published` exactly like the full zips.
- **Portable data location and fallback.** Unchanged from `src/paths.py::data_dir`: `KEKAR_DATA_DIR` → `<exe_dir>/../KeKarData` → `<exe_dir>/KeKarData` → `%APPDATA%/KeKar` or `$XDG_CONFIG_HOME/kekar`. Both builds therefore share one `KeKarData/` on the same drive. No machine-specific absolute path is baked into a launcher.
- **Launcher strategy.** Double-clickable `KeKarLite.sh` / `KeKarLite.bat`, generated from `tools/make_usb_package.py` templates that are byte-identical to the checked-in `assets/launchers/` sources. The Linux script falls back to `QT_QPA_PLATFORM=offscreen` on a headless machine. `tools/install_linux.py` ships with the package and writes a real absolute-path `.desktop` entry; run it again if the mount point changes.
- **Unsigned-executable friction.** Same as full KeKar: SmartScreen shows "Windows protected your PC"; README says **More info → Run anyway**. UPX stays off (`KeKar.spec`) to avoid AV false positives. No code-signing is introduced by this plan.
- **Real-display verification.** Task 11 gives the exact launch commands, window observations and screenshot checks on a real X11/Wayland session, plus a headless `--version` check. Nothing is declared verified until those commands have been run.

---

## Task 1: Feature switch module

**Files:**
- Create: `src/features.py`
- Create: `tests/test_features.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces: `features.variant() -> str`, `is_lite() -> bool`, `chat_enabled() -> bool`, `marketplace_enabled() -> bool`, `portal_sync_enabled() -> bool`, `maps_enabled() -> bool`, `visible_channels(all_channels: list[str]) -> list[str]`, constants `FULL`, `LITE`, `LITE_HIDDEN_CHANNELS`. All later tasks import these by name.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_features.py
import src.features as features


def test_full_variant_is_the_default(monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    assert features.variant() == "full"
    assert features.is_lite() is False
    assert features.chat_enabled() is True
    assert features.marketplace_enabled() is True
    assert features.portal_sync_enabled() is True


def test_unknown_variant_falls_back_to_full(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "experimental")
    assert features.variant() == "full"


def test_lite_disables_only_the_three_direct_connections(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    assert features.variant() == "lite"
    assert features.is_lite() is True
    assert features.chat_enabled() is False
    assert features.marketplace_enabled() is False
    assert features.portal_sync_enabled() is False


def test_lite_hides_only_the_named_site_channels(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    channels = ["generic", "zillow", "apartments_com", "airbnb", "vrbo",
                "booking_com"]
    assert features.visible_channels(channels) == [
        "generic", "zillow", "booking_com"]


def test_full_keeps_every_channel(monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    channels = ["generic", "zillow", "apartments_com", "airbnb", "vrbo",
                "booking_com"]
    assert features.visible_channels(channels) == channels


def test_lite_disables_google_maps_suggestions(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    assert features.maps_enabled() is False


def test_full_keeps_google_maps_suggestions(monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    assert features.maps_enabled() is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_features.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'src.features'`.

- [ ] **Step 3: Write the implementation**

```python
# src/features.py
"""Build variant and feature switches for KeKar / KeKar Lite.

One source tree ships two products. A frozen build carries a generated
``src/_variant.py`` stamp (written by ``tools/set_variant.py``); a source
checkout and the test suite use ``KEKAR_VARIANT``. Anything else resolves to
``full``, so a plain checkout keeps every KeKar feature.

The switch controls composition only. Data, schema and settings are identical
in both variants.
"""
from __future__ import annotations

import os

FULL = "full"
LITE = "lite"
VALID_VARIANTS = (FULL, LITE)

# Channel keys hidden from the Lite picker. The copy/paste mechanism itself is
# never disabled: compile_channel() still accepts every key in both builds.
LITE_HIDDEN_CHANNELS = frozenset({"apartments_com", "airbnb", "vrbo"})


def _stamped_variant() -> str | None:
    """The value baked into a frozen build, if one was generated."""
    try:
        from ._variant import VARIANT  # generated; gitignored
    except ImportError:
        return None
    return VARIANT if VARIANT in VALID_VARIANTS else None


def variant() -> str:
    """The active build variant: ``full`` (default) or ``lite``."""
    env = os.environ.get("KEKAR_VARIANT", "").strip().lower()
    if env in VALID_VARIANTS:
        return env
    return _stamped_variant() or FULL


def is_lite() -> bool:
    return variant() == LITE


def chat_enabled() -> bool:
    """The AI assistant is the only feature that needs an API key."""
    return not is_lite()


def marketplace_enabled() -> bool:
    """Facebook Marketplace autofill opens a browser over CDP."""
    return not is_lite()


def portal_sync_enabled() -> bool:
    """'Sync now' fetches a portal's iCal URL over the network."""
    return not is_lite()


def maps_enabled() -> bool:
    """Google Places address lookup is another outbound connection (K11)."""
    return not is_lite()


def visible_channels(all_channels: list[str]) -> list[str]:
    """Channel keys the current build offers in the listing picker."""
    if not is_lite():
        return list(all_channels)
    return [key for key in all_channels if key not in LITE_HIDDEN_CHANNELS]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_features.py -v`
Expected: 7 passed.

- [ ] **Step 5: Record the baseline and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 7> passed`; write the exact number into your task notes.

```bash
git add src/features.py tests/test_features.py
git commit -m "feat(lite): add the build-variant feature switch"
```

---

## Task 2: Application container composes without the agent in Lite

**Files:**
- Modify: `src/app.py` (imports lines 11–15, `__init__` lines 48–63, `_rebuild_repos` lines 162–179)
- Create: `tests/test_kekar_lite.py`

**Interfaces:**
- Consumes: `features.chat_enabled()` from Task 1.
- Produces: in Lite, `Application` has **no** `agent_runner`, **no** `client`, **no** `memory`, `chat_repo is None`, and `main_window.chat_pane is None` (Task 3). In full mode, all four exist exactly as today. Repositories `property_repo`, `applicant_repo`, `lease_repo`, `booking_repo`, `portal_repo`, `user_repo` exist in both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_kekar_lite.py
"""End-to-end checks that a Lite Application really is built without AI/CDP."""
import os
import subprocess
import sys


def _run_lite(code: str, tmp_path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(KEKAR_VARIANT="lite", KEKAR_TESTING="1",
               QT_QPA_PLATFORM="offscreen",
               KEKAR_DATA_DIR=str(tmp_path / "KeKarData"))
    return subprocess.run([sys.executable, "-c", code], env=env,
                          capture_output=True, text=True, timeout=60)


def test_lite_application_has_no_agent_or_chat(tmp_path):
    proc = _run_lite(
        "from src.app import Application\n"
        "a = Application([])\n"
        "assert not hasattr(a, 'agent_runner')\n"
        "assert not hasattr(a, 'client')\n"
        "assert not hasattr(a, 'memory')\n"
        "assert a.chat_repo is None\n"
        "assert a.main_window.chat_pane is None\n"
        "a.main_window.close()\n"
        "print('OK')\n", tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_full_application_still_has_the_agent(kekar_app):
    assert kekar_app.agent_runner is not None
    assert kekar_app.client is not None
    assert kekar_app.chat_repo is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_kekar_lite.py -v`
Expected: `test_lite_application_has_no_agent_or_chat` fails with `AssertionError` (the agent attributes exist); `test_full_application_still_has_the_agent` passes.

- [ ] **Step 3: Guard the composition roots in `src/app.py`**

Replace the block

```python
from .agent import providers
from .agent.client import LLMClient
from .agent.memory import MemoryStore
from .agent.runner import AgentRunner
from .agent.tools import ToolContext
```

with the single import

```python
from . import features
```

Replace in `Application.__init__`:

```python
        self.settings = Settings.load()
        # The taskbar, the start menu and the title bar all read this.
        self.setWindowIcon(QIcon(str(icon_path())))
        # A key saved before provider detection existed may point at the
        # wrong host. Repair it once, then leave the user's choice alone.
        self.provider_note = providers.migrate_default_provider(self.settings)
```

with

```python
        self.settings = Settings.load()
        # The taskbar, the start menu and the title bar all read this.
        self.setWindowIcon(QIcon(str(icon_path())))
        # Lite never talks to a provider, so it never repairs (or needs) the
        # saved provider choice. Full KeKar behaves exactly as before.
        self.provider_note = ""
        if features.chat_enabled():
            from .agent import providers
            self.provider_note = providers.migrate_default_provider(
                self.settings)
```

Replace

```python
        self.memory = MemoryStore()
        self.client = LLMClient(self.settings)
        self._open_database(self._real_db_path)
```

with

```python
        if features.chat_enabled():
            from .agent.client import LLMClient
            from .agent.memory import MemoryStore
            self.memory = MemoryStore()
            self.client = LLMClient(self.settings)
        self._open_database(self._real_db_path)
```

Replace the body of `_rebuild_repos` with:

```python
    def _rebuild_repos(self) -> None:
        """Re-point the repositories at the current database.

        Repositories resolve their connection lazily through the Database, so
        rebuilding them is enough — no view has to be reconstructed. The agent
        and its chat history exist only in the full build; Lite composes none
        of them even though the tables are still present on disk.
        """
        self.property_repo = PropertyRepo(self.db)
        self.applicant_repo = ApplicantRepo(self.db)
        self.lease_repo = LeaseRepo(self.db)
        self.booking_repo = BookingRepo(self.db)
        self.portal_repo = PortalRepo(self.db)
        self.user_repo = UserRepo(self.db)
        self.chat_repo = ChatRepo(self.db) if features.chat_enabled() else None
        if features.chat_enabled():
            from .agent.runner import AgentRunner
            from .agent.tools import ToolContext
            self.ctx = ToolContext(db=self.db, property_repo=self.property_repo,
                                   applicant_repo=self.applicant_repo,
                                   memory=self.memory, settings=self.settings,
                                   on_change=self.data_changed.emit)
            self.agent_runner = AgentRunner(self.client, self.settings, self.ctx)
```

Keep `from .data.chat_repo import ChatRepo` at module level; it is local code with no network dependency. Keep the `data_changed` → `reload_all` connection unchanged; in Lite nothing emits it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_kekar_lite.py -v`
Expected: 2 passed. `test_lite_application_has_no_agent_or_chat` currently fails at `a.main_window.chat_pane is None` until Task 3 lands; if that is the only failure, add the Task 3 guard now in the same working tree before committing, or land Task 3 as one combined commit with this task.

- [ ] **Step 5: Full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 9> passed`.

```bash
git add src/app.py tests/test_kekar_lite.py
git commit -m "feat(lite): compose Application without the agent stack"
```

---

## Task 3: Main window without a chat pane, chat controls or provider ping

**Files:**
- Modify: `src/ui/main_window.py` (imports lines 16–30, `__init__` lines 260–364, `_build_menu` lines 366–415, toggle helpers lines 557–628, `_restore_layout` lines 717–723, `apply_theme` lines 725–746)

**Interfaces:**
- Consumes: `features.chat_enabled()`; `Application` from Task 2.
- Produces: `MainWindow.chat_pane` is a `ChatPane` in full mode and `None` in Lite. `MainWindow.sidebar_action`, `chat_action`, `sidebar_toggle`, `chat_toggle` exist in both; the two chat-specific ones are hidden in Lite. `MainWindow._ping_timer` never becomes active in Lite.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lite_ui.py`:

```python
"""Widget-level behaviour of the Lite composition."""
from PyQt6.QtCore import Qt

from src import features
from src.app import Application
from src.data.models import Property, SHORT_STAY_KIND
from src.ui.listing_dialog import ListingDialog
from src.ui.main_window import MainWindow
from src.ui.property_form import PropertyForm
from src.ui.settings_dialog import SettingsDialog
from src.ui.wizard import FirstRunWizard


def _lite_window(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    return MainWindow(kekar_app)


def _close_window(kekar_app, window):
    try:
        kekar_app.data_changed.disconnect(window.reload_all)
    except (TypeError, RuntimeError):
        pass
    window.close()


def test_lite_window_has_no_chat_pane(kekar_app, monkeypatch):
    window = _lite_window(kekar_app, monkeypatch)
    try:
        assert window.chat_pane is None
        assert window.main_splitter.count() == 1
    finally:
        _close_window(kekar_app, window)


def test_lite_window_has_no_chat_controls_or_offline_ping(
        kekar_app, monkeypatch):
    window = _lite_window(kekar_app, monkeypatch)
    try:
        assert window.chat_action.isVisible() is False
        assert window.chat_toggle.isVisible() is False
        assert not window._ping_timer.isActive()
        assert window.offline_banner.isHidden()
        assert window.status_pill.isHidden()
    finally:
        _close_window(kekar_app, window)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py -v`
Expected: both tests fail — `chat_pane` is a `ChatPane` and `main_splitter.count() == 2`.

- [ ] **Step 3: Guard the shell**

Add `from .. import features` to the imports of `src/ui/main_window.py`. Remove the module-level `from .chat_pane import ChatPane`.

Replace

```python
        self.main_splitter.addWidget(self.top_splitter)
        self.chat_pane = ChatPane(app)
        self.chat_pane.setProperty("panel", True)
        self.main_splitter.addWidget(self.chat_pane)
        self.main_splitter.setSizes([560, 200])
```

with

```python
        self.main_splitter.addWidget(self.top_splitter)
        if features.chat_enabled():
            from .chat_pane import ChatPane
            self.chat_pane = ChatPane(app)
            self.chat_pane.setProperty("panel", True)
            self.main_splitter.addWidget(self.chat_pane)
            self.main_splitter.setSizes([560, 200])
        else:
            self.chat_pane = None
```

Replace

```python
        self.crm_tab.reload()
        self.chat_pane.load_history()

        # offline detection
        self._ping: _PingThread | None = None
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(PING_INTERVAL_MS)
        self._ping_timer.timeout.connect(self.check_online)
        # Tests must not reach the network; conftest sets KEKAR_TESTING.
        if not os.environ.get("KEKAR_TESTING"):
            self._ping_timer.start()
            self.check_online()
```

with

```python
        self.crm_tab.reload()
        if self.chat_pane is not None:
            self.chat_pane.load_history()

        # Offline detection exists only in the full build: Lite has no remote
        # service to reach, so it starts no timer and shows no network pill.
        self._ping: _PingThread | None = None
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(PING_INTERVAL_MS)
        self._ping_timer.timeout.connect(self.check_online)
        if features.chat_enabled() and not os.environ.get("KEKAR_TESTING"):
            self._ping_timer.start()
            self.check_online()
        else:
            self.offline_banner.hide()
            self.status_pill.hide()
```

In `_build_menu`, replace

```python
        self.chat_action = view_menu.addAction("Collapse chat")
        self.chat_action.triggered.connect(self._toggle_chat)
```

with

```python
        self.chat_action = view_menu.addAction("Collapse chat")
        self.chat_action.triggered.connect(self._toggle_chat)
        self.chat_action.setVisible(self.chat_pane is not None)
```

Replace `_toggle_chat` with:

```python
    def _toggle_chat(self) -> None:
        if self.chat_pane is None:
            return
        self.main_splitter.toggle_pane(1)
        self._remember_layout()
```

```python
    def _remember_layout(self) -> None:
        self.app.settings.sidebar_collapsed = self.top_splitter.is_collapsed(0)
        self.app.settings.chat_collapsed = (self.main_splitter.is_collapsed(1)
                                            if self.chat_pane is not None
                                            else False)
        try:
            self.app.settings.save()
        except Exception:
            pass
        self._refresh_panel_actions()
```

Replace

```python
    def _agent_busy(self) -> bool:
        return self.chat_pane._thread is not None
```

with

```python
    def _agent_busy(self) -> bool:
        return self.chat_pane is not None and self.chat_pane._thread is not None
```

In `_build_panel_toggles`, after creating `self.chat_toggle`, add:

```python
        self.chat_toggle.setVisible(self.chat_pane is not None)
```

In `_refresh_panel_actions`, guard the chat toggle's text/tooltip block with:

```python
        if self.chat_pane is None:
            return
```

immediately before `if hasattr(self, "chat_toggle"):` — the sidebar block above it stays.

In `_restore_layout`, replace

```python
        if self.app.settings.chat_collapsed:
            self.main_splitter.collapse(1, True)
```

with

```python
        if self.chat_pane is not None and self.app.settings.chat_collapsed:
            self.main_splitter.collapse(1, True)
```

In `apply_theme`, replace `self.chat_pane.apply_theme(theme)` with:

```python
        if self.chat_pane is not None:
            self.chat_pane.apply_theme(theme)
```

In `AboutDialog.__init__`, use a variant-aware body. Replace the paragraph that ends with `"assistant."`:

```python
            f"<p>Your properties, photos and applicant notes live in the "
            f"KeKarData folder next to the program. Nothing leaves this "
            f"drive except the questions you choose to send to the "
            f"assistant.</p>"
```

with

```python
            f"<p>Your properties, photos and applicant notes live in the "
            f"KeKarData folder next to the program. "
            + ("Nothing ever leaves this drive.</p>"
               if not features.chat_enabled() else
               "Nothing leaves this drive except the questions you choose "
               "to send to the assistant.</p>")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py tests/test_kekar_lite.py -v`
Expected: 4 passed.

- [ ] **Step 5: Check the full build did not regress and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 11> passed`; full-mode tests `test_chat_loads_stored_history`, `test_ping_is_disabled_under_test`, `test_offline_banner_reflects_ping_result` still pass.

```bash
git add src/ui/main_window.py tests/test_lite_ui.py
git commit -m "feat(lite): remove the chat pane and provider ping from the shell"
```

---

## Task 4: Property form without Marketplace autofill or the Portals group

**Files:**
- Modify: `src/ui/property_form.py` (imports lines 10–21, `_PortalSyncThread.run` line 47, `KIND_LABELS` lines 23–27, `__init__` portals block lines 198–251 and actions lines 289–312, portal helpers lines 327–414, `_on_kind_changed` lines 419–428, `_fill_fields` line 510, `save` line 554)
- Modify: `tests/test_lite_ui.py` (append)

**Interfaces:**
- Consumes: `features.is_lite()`, `features.marketplace_enabled()`, `features.portal_sync_enabled()`.
- Produces: `PropertyForm.publish_btn` is `None` and `PropertyForm.portals_box` is `None` in Lite; `save_btn`, `preview_btn`, `copy_btn`, `rented_btn`, `vacant_btn` exist in both. `PropertyForm.copy_listing()` and `preview_listing()` work unchanged in both.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lite_ui.py`:

```python
def test_lite_form_has_no_publish_or_portals_but_keeps_copy(kekar_app,
                                                            monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    form = PropertyForm(kekar_app)
    assert form.publish_btn is None
    assert form.portals_box is None
    assert form.portal_rows == {}
    assert form.copy_btn.text() == "Copy listing"
    assert form.preview_btn.text() == "Preview listing"
    assert form.kind_combo.itemData(1) == SHORT_STAY_KIND
    assert form.kind_combo.itemText(1) == "Short stay"
    form.close()


def test_lite_form_never_starts_a_maps_request(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    monkeypatch.setattr(kekar_app.settings, "maps_key", "test-key")
    form = PropertyForm(kekar_app)
    # The completer is never attached and the debounce timer never runs, so
    # typing an address cannot reach Google Places even with a stored key.
    assert form.address_input.completer() is None
    assert not form._maps_timer.isActive()
    form.address_input.setText("99 Network Free Street")
    form._on_address_edited("99 Network Free Street")
    assert not form._maps_timer.isActive()
    form.close()


def test_lite_form_still_saves_a_short_stay_without_portal_rows(
        kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    form = PropertyForm(kekar_app)
    form.address_input.setText("9 Lite Lane")
    form.kind_combo.setCurrentIndex(1)
    form.nightly_input.setValue(175)
    form.save()
    saved = kekar_app.property_repo.get(form.current_id)
    assert saved.kind == SHORT_STAY_KIND
    assert saved.nightly_price == 175
    assert kekar_app.portal_repo.list_for_property(saved.id) == []
    form.close()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py -v`
Expected: all three new tests fail on `form.publish_btn is None` / `form.portals_box is None`.

- [ ] **Step 3: Guard the form sections**

Add `from .. import features` to the imports. Remove the top-level

```python
from ..services import maps_service
```

and add `from ..services import maps_service` as the first statement of `_MapsAutocompleteThread.run` and `_MapsDetailsThread.run`. In Lite those classes are never instantiated, so the module is never imported.

Change

```python
from ..data.models import (PORTAL_LABELS, PORTALS, PROPERTY_KINDS,
                           PortalSettings, Property, SHORT_STAY_KIND)
```

to

```python
from ..data.models import PROPERTY_KINDS, Property, SHORT_STAY_KIND
```

Remove the top-level imports of `ical_service` and `portal_sync`. In `_PortalSyncThread.run`, add a local import before the call:

```python
        from ..services import portal_sync
        result = portal_sync.sync_portal(self.app.db, prop, self.portal)
```

In `__init__`, keep the `_maps_model`, `_maps_completer`, `_maps_timer`, `_map_suggestions` and `last_maps_error` attributes unconditionally (the helper methods and `_clear_fields` reference them), but wrap only the four wiring lines in a guard:

```python
        if features.maps_enabled():
            self.address_input.setCompleter(self._maps_completer)
            self._maps_completer.activated.connect(self._on_address_selected)
            self._maps_timer.timeout.connect(self._start_address_search)
            self.address_input.textEdited.connect(self._on_address_edited)
```

Add an early return to each of the three Maps handlers so they are inert even when called directly from a test or a queued signal:

```python
    def _on_address_edited(self, text: str) -> None:
        if not features.maps_enabled():
            self._maps_timer.stop()
            return
```

```python
    def _start_address_search(self) -> None:
        if not features.maps_enabled():
            return
```

```python
    def _on_address_selected(self, description: str) -> None:
        if not features.maps_enabled():
            return
```

With no completer attached, no signal connected and those three early returns, no key and no keystroke can start a request.

Replace the `KIND_LABELS` constant with a function:

```python
def _kind_labels() -> tuple[tuple[str, str], ...]:
    """Lite has no portal connections, so it drops the site name."""
    stay = "Short stay" if features.is_lite() else "Short stay (Airbnb)"
    return (("Long-term rental", "rental"), (stay, SHORT_STAY_KIND))
```

and in `__init__` change `for label, key in KIND_LABELS:` to `for label, key in _kind_labels():`.

Wrap the entire portals block (currently lines 198–251, from `self.portals_box = QGroupBox("Portals", self)` through `layout.addWidget(self.portals_box)`) in:

```python
        if features.portal_sync_enabled():
            from ..data.models import PORTALS, PORTAL_LABELS, PortalSettings
            ...  # the existing block, unchanged
        else:
            self.portals_box = None
            self.portal_rows = {}
```

Inside that block only, the local imports must appear before the first use of `PORTALS`, and the methods below need their own local imports because they run later. Add `from ..data.models import PortalSettings` at the top of `_save_portals`, and `from ..data.models import PORTAL_LABELS` at the top of `_on_sync_done`.

Replace the publish button creation with:

```python
        self.publish_btn = None
        if features.marketplace_enabled():
            self.publish_btn = QPushButton("Publish to Marketplace...")
            self.publish_btn.clicked.connect(self._publish_or_list)
```

and change the second action row to add `self.publish_btn` only when present:

```python
        actions_two = QHBoxLayout()
        for btn in (self.publish_btn, self.rented_btn, self.vacant_btn):
            if btn is not None:
                actions_two.addWidget(btn)
        actions_two.addStretch(1)
        layout.addLayout(actions_two)
```

Add early returns to the portal helpers, immediately after each `def` line:

```python
    def _load_portals(self, prop: Property) -> None:
        if self.portals_box is None:
            return
```

```python
    def _save_portals(self, prop: Property) -> None:
        if self.portals_box is None:
            return
```

```python
    def _sync_portal(self) -> None:
        if self.portals_box is None:
            return
```

```python
    def export_calendar(self) -> None:
        if self.portals_box is None:
            return
        from ..services import ical_service
```

In `_on_kind_changed`, replace

```python
        self.portals_box.setVisible(short)
        # ... comment ...
        self.publish_btn.setText("Portal listing…" if short
                                 else "Publish to Marketplace...")
```

with

```python
        if self.portals_box is not None:
            self.portals_box.setVisible(short)
        if self.publish_btn is not None:
            self.publish_btn.setText("Portal listing…" if short
                                     else "Publish to Marketplace...")
```

In `_fill_fields`, change `self._load_portals(p)` to:

```python
        if self.portals_box is not None:
            self._load_portals(p)
```

In `save`, change `self._save_portals(prop)` to:

```python
        if self.portals_box is not None:
            self._save_portals(prop)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py -v`
Expected: 5 passed.

- [ ] **Step 5: Full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 14> passed`; `test_property_form_has_a_publish_button`, `test_short_stay_action_button_opens_the_portal_listing`, `test_rental_action_button_says_marketplace` still pass in full mode.

```bash
git add src/ui/property_form.py tests/test_lite_ui.py
git commit -m "feat(lite): hide Marketplace autofill and the Portals group"
```

---

## Task 5: Listing dialog keeps copy-and-paste, filters named channels

**Files:**
- Modify: `src/ui/listing_dialog.py` (imports lines 13–17, channel loop line 38, note text lines 44–53)
- Modify: `tests/test_lite_ui.py` (append)

**Interfaces:**
- Consumes: `features.visible_channels()` from Task 1 and `features.is_lite()`; `known_channels()` from `src/services/listing_channels.py` (unchanged).
- Produces: `ListingDialog.channel` offers `["generic", "zillow"]` for a Lite rental and `["generic", "booking_com"]` for a Lite short stay; full mode is unchanged. `compile_channel()` and `compile_listing()` are unchanged and still importable for every key.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lite_ui.py`:

```python
def test_lite_listing_dialog_offers_only_local_rental_channels(
        kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    prop = kekar_app.property_repo.create(
        Property(address="10 Copy Court", rent_price=900, sqft=800,
                 bedrooms=2, bathrooms=1.0))
    dialog = ListingDialog(kekar_app, prop)
    keys = [dialog.channel.itemData(i) for i in range(dialog.channel.count())]
    assert keys == ["generic", "zillow"]
    dialog.close()


def test_lite_listing_dialog_offers_only_local_stay_channels(
        kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    prop = kekar_app.property_repo.create(
        Property(address="11 Copy Court", kind=SHORT_STAY_KIND,
                 nightly_price=190, max_guests=4, min_stay_nights=2))
    dialog = ListingDialog(kekar_app, prop)
    keys = [dialog.channel.itemData(i) for i in range(dialog.channel.count())]
    assert keys == ["generic", "booking_com"]
    assert "Airbnb" not in dialog.note.text()
    dialog.close()


def test_lite_compile_channel_still_accepts_a_hidden_key():
    """Hiding a channel in the picker must not change the data layer."""
    from src.services.listing_channels import compile_channel
    prop = Property(address="12 Copy Court", rent_price=700, sqft=700)
    package = compile_channel(prop, "apartments_com")
    assert "Description" in [name for name, _ in package.fields]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py -v`
Expected: the first two fail because the picker still contains all channels; the third passes already and guards against over-removal.

- [ ] **Step 3: Filter the picker and reword the note**

Add `from .. import features` to the imports. Replace

```python
        for key in known_channels(prop.kind):
```

with

```python
        for key in features.visible_channels(known_channels(prop.kind)):
```

Replace the note block:

```python
        self.note = QLabel(
            "Zillow and apartments.com have no posting API, so KeKar builds "
            "the listing for each site's form. Copy it and paste it in — "
            "posting stays with you.")
        if prop.kind == SHORT_STAY_KIND:
            self.note.setText(
                "Airbnb, Vrbo and Booking.com have no posting API for an "
                "independent host, so KeKar builds the listing for each "
                "portal's form. Copy it and paste it in — posting stays "
                "with you.")
```

with

```python
        self.note = QLabel(
            "Copy the listing and paste it into the site's form — posting "
            "stays with you."
            if features.is_lite() else
            "Zillow and apartments.com have no posting API, so KeKar builds "
            "the listing for each site's form. Copy it and paste it in — "
            "posting stays with you.")
        if prop.kind == SHORT_STAY_KIND:
            self.note.setText(
                "Short-stay sites have no posting API for an independent "
                "host. Copy the package and paste it in — posting stays "
                "with you."
                if features.is_lite() else
                "Airbnb, Vrbo and Booking.com have no posting API for an "
                "independent host, so KeKar builds the listing for each "
                "portal's form. Copy it and paste it in — posting stays "
                "with you.")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py tests/test_listing_channels.py -v`
Expected: all pass, including full-mode `test_dialog_offers_every_channel`.

- [ ] **Step 5: Full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 17> passed`.

```bash
git add src/ui/listing_dialog.py tests/test_lite_ui.py
git commit -m "feat(lite): keep copy-paste listings, hide named channels"
```

---

## Task 6: First-run wizard and Settings without the AI connection

**Files:**
- Modify: `src/ui/wizard.py` (import line 9, `__init__` line 30, `_go_next` lines 80–100, `save_key` line 112)
- Modify: `src/ui/settings_dialog.py` (import line 13, rows lines 128–189, `_save` lines 216–233)
- Modify: `src/main.py` (import line 13, wizard guard line 80, display name in help)
- Modify: `tests/test_lite_ui.py` (append)

**Interfaces:**
- Consumes: `features.chat_enabled()`; `display_name()` from Task 8 (only for the help text; Task 6 may land before Task 8 by using `APP_NAME` temporarily and folding the rename into Task 8).
- Produces: in Lite, `FirstRunWizard.pages.count() == 1`, `SettingsDialog` has no `key_input`/`autofill`/`browser` widgets, and `SettingsDialog._save()` leaves provider fields untouched. Full mode unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lite_ui.py`:

```python
def test_lite_wizard_needs_no_api_key(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    wizard = FirstRunWizard(kekar_app)
    assert wizard.pages.count() == 1
    assert not hasattr(wizard, "key_input")
    wizard._go_next()
    assert wizard.result() == FirstRunWizard.DialogCode.Accepted


def test_lite_settings_hide_every_provider_control(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    dialog = SettingsDialog(kekar_app)
    for attr in ("key_input", "provider", "api_base", "models_input",
                 "autofill", "browser", "test_btn", "remove_btn",
                 "maps_key", "maps_autofill"):
        assert not hasattr(dialog, attr), attr
    assert dialog.theme is not None
    assert dialog.keep_days is not None
    dialog.close()


def test_lite_settings_save_preserves_existing_key(kekar_app, monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    kekar_app.settings.api_key = "sk-or-existing"
    kekar_app.settings.maps_key = "maps-existing"
    dialog = SettingsDialog(kekar_app)
    dialog.keep_days.setValue(14)
    dialog._save()
    assert kekar_app.settings.backup_keep_days == 14
    assert kekar_app.settings.api_key == "sk-or-existing"
    assert kekar_app.settings.maps_key == "maps-existing"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py -v`
Expected: all three new tests fail — the wizard has two pages, the settings dialog has all provider widgets, and `_save` overwrites the key with an empty string.

- [ ] **Step 3: Guard the wizard**

In `src/ui/wizard.py`, add `from .. import features` and remove the module-level `from ..agent import providers`. In `__init__`, replace

```python
        self.pages.addWidget(self._welcome_page())
        self.pages.addWidget(self._api_page())
```

with

```python
        self.pages.addWidget(self._welcome_page())
        if features.chat_enabled():
            self.pages.addWidget(self._api_page())
```

In `save_key`, add `from ..agent import providers` as the first statement (this method is unreachable in Lite).

Replace `_go_next` with:

```python
    def _go_next(self) -> None:
        if self.pages.currentIndex() == self.pages.count() - 1:
            if not features.chat_enabled():
                data_dir()   # ensure the data tree exists on a fresh install
                self.accept()
                return
            ok, message = self.save_key()
            if not ok:
                QMessageBox.warning(self, "KeKar", message)
                return
            # Verify against the provider. This is a real network call, so it
            # can be slow — tell the user rather than freezing silently.
            self.next_button.setEnabled(False)
            self.next_button.setText("Checking...")
            try:
                ok, message = self._verify_connection()
            finally:
                self.next_button.setEnabled(True)
                self._update_buttons()
            if not ok:
                QMessageBox.warning(self, "KeKar", message)
                return
            self.accept()
            return
        self.pages.setCurrentIndex(self.pages.currentIndex() + 1)
        self._update_buttons()
```

- [ ] **Step 4: Guard the Settings dialog**

In `src/ui/settings_dialog.py`, add `from .. import features` and replace

```python
from ..agent import providers
```

with a lazy accessor:

```python
def _providers():
    """Imported only in the full build; Lite never loads the AI stack."""
    from ..agent import providers
    return providers
```

Then replace every `providers.X` reference with `_providers().X` (`_on_provider_changed`, `_is_default_models`, `_detect_provider`, `_apply_provider`). None of those paths execute in Lite.

In `__init__`, wrap the provider rows so only `Theme` and `Keep backups for (days)` are unconditional. Replace the block from `self.key_input = QLineEdit()` through `form.addRow("Browser", self.browser)` with:

```python
        if features.chat_enabled():
            self.key_input = QLineEdit()
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.key_input.setText(app.settings.api_key)
            form.addRow("API key", self.key_input)

            self.provider = QComboBox()
            for prov in _providers().PROVIDERS:
                self.provider.addItem(prov.name, prov.id)
            index = self.provider.findData(app.settings.provider)
            if index >= 0:
                self.provider.setCurrentIndex(index)
            self.provider.currentIndexChanged.connect(self._on_provider_changed)
            form.addRow("Provider", self.provider)

            detect_btn = QPushButton("Detect from key")
            detect_btn.setToolTip(
                "Identify the provider from the key's format, then confirm "
                "it actually works.")
            detect_btn.clicked.connect(self._detect_provider)
            form.addRow("", detect_btn)

            self.api_base = QLineEdit()
            self.api_base.setText(app.settings.api_base)
            self.api_base.setPlaceholderText("https://…/api/v1")
            form.addRow("API endpoint", self.api_base)

            self.models_input = QTextEdit()
            self.models_input.setPlainText("\n".join(app.settings.model_chain))
            self.models_input.setMaximumHeight(90)
            self.models_input.setToolTip("Tried in order until one succeeds.")
            form.addRow("Models (one per line, tried in order)", self.models_input)

            fetch_btn = QPushButton("Fetch the provider's model list")
            fetch_btn.clicked.connect(self._fetch_models)
            form.addRow("", fetch_btn)

            self.autofill = QCheckBox(
                "Auto-fill Marketplace listings (experimental)")
            self.autofill.setChecked(app.settings.autofill_enabled)
            form.addRow(self.autofill)

            if features.maps_enabled():
                self.maps_key = QLineEdit()
                self.maps_key.setEchoMode(QLineEdit.EchoMode.Password)
                self.maps_key.setText(app.settings.maps_key)
                self.maps_key.setPlaceholderText(
                    "Optional — address suggestions")
                form.addRow("Google Maps key", self.maps_key)

                self.maps_autofill = QCheckBox(
                    "Auto-fill empty City and ZIP from Google Maps")
                self.maps_autofill.setChecked(app.settings.maps_autofill)
                form.addRow(self.maps_autofill)

            self.browser = QComboBox()
            self.browser.addItems(["auto", "chrome", "edge"])
            self.browser.setCurrentText(app.settings.browser_kind)
            form.addRow("Browser", self.browser)
```

Keep the `theme` and `keep_days` rows exactly where they are, outside this guard.

Replace the actions block (`test_btn` and `remove_btn`) with:

```python
        self.test_btn = None
        self.remove_btn = None
        if features.chat_enabled():
            self.test_btn = QPushButton("Test connection")
            self.test_btn.clicked.connect(self._test_connection)
            actions.addRow(self.test_btn)

            self.remove_btn = QPushButton("Remove stored key")
            self.remove_btn.clicked.connect(self._remove_key)
            actions.addRow(self.remove_btn)
```

Replace `_save` with:

```python
    def _save(self) -> None:
        settings = self.app.settings
        if features.chat_enabled():
            settings.api_key = self.key_input.text().strip()
            settings.provider = self.provider.currentData() or "custom"
            settings.api_base = self.api_base.text().strip()
            settings.model_chain = [m.strip() for m in
                                    self.models_input.toPlainText().splitlines()
                                    if m.strip()]
            settings.autofill_enabled = self.autofill.isChecked()
            settings.browser_kind = self.browser.currentText()
        if features.maps_enabled():
            settings.maps_key = self.maps_key.text().strip()
            settings.maps_autofill = self.maps_autofill.isChecked()
        settings.backup_keep_days = self.keep_days.value()
        try:
            settings.save()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME,
                                f"Could not save settings: {exc}")
            return
        self.accept()
```

Add guards at the top of `_set_busy` and `_on_task_done` for `self.test_btn is None` (Lite never calls them, but a queued signal must not crash):

```python
        if self.test_btn is None:
            return
```

- [ ] **Step 5: Guard `src/main.py`**

Add `from src import features` to the imports and replace

```python
    if not app.settings.is_configured():
```

with

```python
    if features.chat_enabled() and not app.settings.is_configured():
```

The comment immediately above stays: in Lite the wizard is shown once for the welcome page only.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_lite_ui.py tests/test_gui_smoke.py tests/test_ui_behaviour.py -v`
Expected: all pass, including `test_wizard_rejects_empty_key`, `test_settings_dialog_opens`, `test_settings_saves_the_provider_and_endpoint` in full mode.

- [ ] **Step 7: Full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 20> passed`.

```bash
git add src/ui/wizard.py src/ui/settings_dialog.py src/main.py tests/test_lite_ui.py
git commit -m "feat(lite): remove the API-key handshake and provider settings"
```

---

## Task 7: Variant-aware guided tour

**Files:**
- Modify: `src/ui/tour.py` (imports line 21, `build_tour_steps` lines 219–290)
- Modify: `tests/test_tour.py` (lines 9–45)

**Interfaces:**
- Consumes: `features.chat_enabled()`; `MainWindow.chat_pane` from Task 3; `MainWindow.tabs` (unchanged).
- Produces: 11 steps in full mode, 10 in Lite; every step target is a real widget; no step in Lite names Facebook, autofill, Airbnb, Vrbo or apartments.com.

- [ ] **Step 1: Write the failing tests**

Replace `test_tour_steps_target_real_widgets` and `test_tour_describes_the_real_feature_set` in `tests/test_tour.py` with:

```python
"""Guided tour: spotlight overlay, step targets, and navigation."""
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QPushButton

from src import features
from src.ui.tour import TourOverlay, TourStep, build_tour_steps


def test_tour_steps_target_real_widgets(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    assert len(steps) == (11 if features.chat_enabled() else 10)
    for step in steps:
        assert isinstance(step, TourStep)
        if step.target is not None:
            assert step.target.parent() is not None, (
                f"{step.title!r} target is not in the widget tree")


def test_tour_describes_the_real_feature_set(kekar_app):
    """The wording must match what the app can actually do."""
    steps = build_tour_steps(kekar_app.main_window)
    text = " ".join(f"{step.title} {step.body}" for step in steps)
    for phrase in ("collapse", "Light", "OLED", "Leases", "template",
                   "Accounts", "print", "calendar", "status bar",
                   "Photos heading", "Help menu"):
        assert phrase in text, f"the tour never mentions {phrase!r}"
    if features.chat_enabled():
        for phrase in ("Zillow", "apartments.com", "Airbnb",
                       "Publish to Marketplace"):
            assert phrase in text, f"the tour never mentions {phrase!r}"
    else:
        for phrase in ("Facebook", "autofill", "Airbnb", "Vrbo",
                       "apartments.com", "Marketplace"):
            assert phrase not in text, f"Lite tour still mentions {phrase!r}"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_tour.py -v`
Expected: full-mode tests pass; under `KEKAR_VARIANT=lite` the suite would fail on the phrase checks because the tour text is still full-mode. To demonstrate the failure explicitly, run:

Run: `KEKAR_VARIANT=lite .venv/bin/python -m pytest tests/test_tour.py::test_tour_describes_the_real_feature_set -v`
Expected: FAIL — `the tour still mentions 'Facebook'`.

- [ ] **Step 3: Make the step list variant-aware**

Add `from .. import features` to `src/ui/tour.py`. Replace the details-form step with a conditional string:

```python
        TourStep(
            window.property_form, "The details form",
            "Address, rent, deposit and the rest. Use Type to switch a unit "
            "to a short stay, which brings its own nightly rate, fees and "
            "minimum stay. 'Preview listing' builds a copy package you can "
            "paste into Zillow for a rental, or Booking.com for a short "
            "stay. 'Copy listing' copies the generic version for any site."
            if features.is_lite() else
            "Address, rent, deposit and the rest. Use Type to switch a unit "
            "to a short stay, which brings its own nightly rate, fees, "
            "minimum stay and portal calendars. 'Preview listing' builds a "
            "copy package — Zillow and apartments.com for a rental, Airbnb, "
            "Vrbo and Booking.com for a short stay — and the action button "
            "reads 'Publish to Marketplace' (the opt-in Facebook auto-fill) "
            "for a rental, or 'Portal listing…' for a short stay."),
```

Replace the Stays step body with:

```python
            "For Airbnb-style units: every reservation on a calendar, with "
            "the guest, portal, dates and payout. Add a stay by hand; KeKar "
            "keeps the dates and payout on this device."
            if features.is_lite() else
            "For Airbnb-style units: every reservation on a calendar, with "
            "the guest, portal, dates and payout. Add a stay by hand, or "
            "import a portal's own calendar from the Portals section of the "
            "property form.",
```

Move the assistant step out of the returned list into a variable and insert it conditionally. Replace the existing `TourStep(window.chat_pane, "The assistant", ...)` element with `assistant_step` and end `build_tour_steps` like this:

```python
    assistant_step = TourStep(
        window.chat_pane, "The assistant",
        "Ask questions in plain language, or give an instruction like "
        "'draft a message to John'. It can read and update your records.")

    steps = [
        welcome_step, properties_step, details_step, photos_step,
        applicants_step, leases_step, stays_step, panels_step,
        brand_step, demo_step,
    ]
    if features.chat_enabled():
        # Position 7: after Stays, before Panels/themes/accounts.
        steps.insert(7, assistant_step)
    return steps
```

Turn the ten inline `TourStep(...)` literals already in `build_tour_steps` into those ten named variables, keeping each target, title, `on_enter` callback and body verbatim except for the two reworded bodies above. `assistant_step` is the existing chat literal with the same target, title and body. In order the variables are: Welcome, Your properties, The details form, Photos, Applicants, Leases, Stays, Panels/themes/accounts, The brand, You're in demo mode.

- [ ] **Step 4: Run the tests in both variants**

Run: `.venv/bin/python -m pytest tests/test_tour.py -v`
Expected: 9 passed (11 steps, full wording).
Run: `KEKAR_VARIANT=lite .venv/bin/python -m pytest tests/test_tour.py -v`
Expected: 9 passed (10 steps, no removed feature named).

- [ ] **Step 5: Full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 20> passed`.

```bash
git add src/ui/tour.py tests/test_tour.py
git commit -m "feat(lite): make the guided tour describe the shipped feature set"
```

---

## Task 8: Variant-aware product name and CLI output

**Files:**
- Modify: `src/_version.py`
- Modify: `src/main.py` (`_print_version`, `_print_help`)
- Modify: `src/app.py` (`setApplicationDisplayName`)
- Modify: `src/ui/main_window.py` (window title, About title/heading)
- Modify: `tests/test_main_cli.py` (append)

**Interfaces:**
- Consumes: `features.is_lite()`; `APP_NAME` and `APP_VERSION` unchanged.
- Produces: `display_name() -> str`, returning `"KeKar Lite"` in Lite and `"KeKar"` in full. `--version` prints `KeKar Lite <APP_VERSION>` in Lite. `APP_NAME` remains `"KeKar"` internally for data paths and settings.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_main_cli.py`:

```python
def test_lite_version_flag_prints_lite_name(monkeypatch, capsys):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    from src.main import main
    from src._version import APP_VERSION
    assert main(["KeKarLite", "--version"]) == 0
    assert capsys.readouterr().out.strip() == f"KeKar Lite {APP_VERSION}"


def test_lite_help_still_works_headless(monkeypatch, capsys):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    from src.main import main
    assert main(["KeKarLite", "--help"]) == 0
    out = capsys.readouterr().out
    assert "KeKar Lite" in out
    assert "--version" in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_main_cli.py -v`
Expected: both new tests fail — output is `KeKar <version>`.

- [ ] **Step 3: Add the display name**

Append to `src/_version.py`:

```python
LITE_APP_NAME = "KeKar Lite"


def display_name() -> str:
    """The product name shown to users; the internal APP_NAME never changes."""
    from . import features
    return LITE_APP_NAME if features.is_lite() else APP_NAME
```

In `src/main.py`, change

```python
from src._version import APP_NAME, APP_VERSION
```

to

```python
from src._version import APP_VERSION, display_name
```

and replace `APP_NAME` with `display_name()` inside `_print_version` and `_print_help`.

In `src/app.py`, keep `from ._version import APP_NAME, APP_VERSION` and add `display_name` to that import; change

```python
        self.setApplicationDisplayName(f"{APP_NAME} Property Manager")
```

to

```python
        self.setApplicationDisplayName(f"{display_name()} Property Manager")
```

In `src/ui/main_window.py`, add `display_name` to the `_version` import and change

```python
        self.setWindowTitle(f"{APP_NAME} Property Manager")
```

to

```python
        self.setWindowTitle(f"{display_name()} Property Manager")
```

and in `AboutDialog`, change `f"About {APP_NAME}"` to `f"About {display_name()}"` and the `<h2>` heading likewise.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_main_cli.py -v`
Expected: 8 passed; `test_version_flag_prints_version` and `test_app_version_matches_nsi_installer` still pass.

- [ ] **Step 5: Full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 22> passed`.

```bash
git add src/_version.py src/main.py src/app.py src/ui/main_window.py tests/test_main_cli.py
git commit -m "feat(lite): give the variant its own display name and CLI output"
```

---

## Task 9: Build-time variant stamp and PyInstaller spec

**Files:**
- Create: `tools/set_variant.py`
- Create: `tests/test_set_variant.py`
- Modify: `.gitignore`, `KeKar.spec`, `build.sh`, `build.ps1`

**Interfaces:**
- Consumes: nothing from the app.
- Produces: `tools/set_variant.py stamp(variant) -> None` (writes `src/_variant.py`), `tools/set_variant.py main()` (stamps, runs a child command with `KEKAR_VARIANT` in its environment, restores the previous file or deletes it in `finally`). `KeKar.spec` reads `KEKAR_VARIANT` and produces `KeKar` or `KeKarLite`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_set_variant.py
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool(monkeypatch, stamp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "set_variant", ROOT / "tools" / "set_variant.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["set_variant"] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STAMP", stamp_path)
    return module


def test_stamp_writes_a_valid_python_module(monkeypatch, tmp_path):
    stamp = tmp_path / "src" / "_variant.py"
    stamp.parent.mkdir()
    tool = _tool(monkeypatch, stamp)
    tool.stamp("lite")
    assert 'VARIANT = "lite"' in stamp.read_text(encoding="utf-8")


def test_main_restores_an_absent_stamp(monkeypatch, tmp_path):
    stamp = tmp_path / "src" / "_variant.py"
    stamp.parent.mkdir()
    tool = _tool(monkeypatch, stamp)
    monkeypatch.setattr(sys, "argv", ["set_variant.py", "lite"])
    assert tool.main() == 0
    assert not stamp.exists()


def test_main_restores_previous_contents(monkeypatch, tmp_path):
    stamp = tmp_path / "src" / "_variant.py"
    stamp.parent.mkdir()
    stamp.write_text("VARIANT = 'full'  # keep me\n", encoding="utf-8")
    tool = _tool(monkeypatch, stamp)
    monkeypatch.setattr(sys, "argv", ["set_variant.py", "lite"])
    assert tool.main() == 0
    assert stamp.read_text(encoding="utf-8") == "VARIANT = 'full'  # keep me\n"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_set_variant.py -v`
Expected: `ModuleNotFoundError` — `tools/set_variant.py` does not exist.

- [ ] **Step 3: Write the stamp tool**

```python
#!/usr/bin/env python3
"""Stamp the build variant, run a command, then restore the source tree.

Usage:
    python tools/set_variant.py lite -- pyinstaller KeKar.spec --noconfirm

The generated ``src/_variant.py`` is gitignored. It is removed (or restored to
its previous contents) even when the child command fails, so a developer's
checkout can never be left accidentally in Lite mode.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

STAMP = Path(__file__).resolve().parents[1] / "src" / "_variant.py"


def stamp(variant: str) -> None:
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(
        '"""Generated by tools/set_variant.py — do not edit or commit."""\n'
        f'VARIANT = "{variant}"\n',
        encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=["full", "lite"])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    previous = STAMP.read_text(encoding="utf-8") if STAMP.exists() else None
    env = dict(os.environ)
    env["KEKAR_VARIANT"] = args.variant
    try:
        stamp(args.variant)
        if not args.command:
            return 0
        command = args.command[1:] if args.command[0] == "--" else args.command
        return subprocess.call(command, env=env)
    finally:
        if previous is None:
            STAMP.unlink(missing_ok=True)
        else:
            STAMP.write_text(previous, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_set_variant.py -v`
Expected: 3 passed.

- [ ] **Step 5: Wire the spec and build scripts**

Append to `.gitignore`:

```
src/_variant.py
```

In `KeKar.spec`, insert after `ROOT = Path(SPECPATH).resolve()`:

```python
import os

LITE = os.environ.get("KEKAR_VARIANT", "full").strip().lower() == "lite"
NAME = "KeKarLite" if LITE else "KeKar"
```

Replace the two collection loops with:

```python
runtime_pkgs = ("PyQt6", "cryptography", "httpx", "PIL")
if not LITE:
    runtime_pkgs += ("playwright",)

for pkg in runtime_pkgs:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

bundle_pkgs = ("PyQt6",) if LITE else ("PyQt6", "playwright")
for pkg in bundle_pkgs:
    try:
        for binaries_, datas_, hiddenimports_ in collect_all(pkg):
            binaries += binaries_
            datas += datas_
            hiddenimports += hiddenimports_
    except Exception:
        pass
```

Change `name="KeKar"` in **both** the `EXE(...)` and `COLLECT(...)` calls to `name=NAME`. Keep everything else in the spec identical (including the `datas` entry for the whole `config/` folder).

In `build.sh`, add after the existing full build and verification lines:

```bash
.venv/bin/python tools/set_variant.py lite -- \
  .venv/bin/python -m PyInstaller KeKar.spec --noconfirm
.venv/bin/python tools/make_usb_package.py --platform linux \
  --source dist/KeKarLite --out out/KeKarLite_Linux --variant lite
.venv/bin/python tools/verify_usb.py out/KeKarLite_Linux \
  --platform linux --variant lite
echo "Built: out/KeKarLite_Linux/"
```

In `build.ps1`, add the PowerShell equivalent:

```powershell
.venv\Scripts\python.exe tools\set_variant.py lite -- `
  .venv\Scripts\python.exe -m PyInstaller KeKar.spec --noconfirm
.venv\Scripts\python.exe tools\make_usb_package.py --platform windows `
  --source dist\KeKarLite --out out\KeKarLite_Windows --variant lite
.venv\Scripts\python.exe tools\verify_usb.py out\KeKarLite_Windows `
  --platform windows --variant lite
Write-Host "Built: out\KeKarLite_Windows\"
```

- [ ] **Step 6: Run the full suite and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 25> passed`; confirm `git status --short` does not list `src/_variant.py`.

```bash
git add tools/set_variant.py tests/test_set_variant.py .gitignore KeKar.spec build.sh build.ps1
git commit -m "build(lite): stamp the variant and build KeKarLite with PyInstaller"
```

---

## Task 10: USB packaging and CI matrix for both variants

**Files:**
- Modify: `tools/make_usb_package.py` (templates lines 22–110, package functions lines 115–175, CLI lines 178–201)
- Modify: `tools/verify_usb.py`
- Modify: `tests/test_usb_packaging.py` (append)
- Modify: `.github/workflows/build.yml` (both jobs)

**Interfaces:**
- Consumes: `--variant` on both tools; `KeKar.spec` output name from Task 9.
- Produces: `make_platform_package(platform, source, out, variant="full")`, `_write_launchers(out, variant="full")`, `verify_usb(root, platform, variant="full")`. Existing call sites and the `BAT`/`SH`/`README` module constants keep their current values in full mode.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_usb_packaging.py`:

```python
def test_lite_usb_package_layout(tool, tmp_path):
    source = tmp_path / "build" / "KeKarLite"
    (source / "_internal").mkdir(parents=True)
    (source / "KeKarLite").write_text("binary", encoding="utf-8")
    out = tool.make_platform_package(
        "linux", source, tmp_path / "out", variant="lite")
    assert (out / "KeKarLite_Linux" / "KeKarLite").exists()
    assert (out / "KeKarLite.sh").exists()
    assert (out / "KeKarLite.sh").stat().st_mode & 0o111
    assert (out / "KeKarData").is_dir()
    readme = (out / "README.txt").read_text(encoding="utf-8")
    assert "KEKAR LITE" in readme
    assert "Chat says it can't connect" not in readme
    launcher = (out / "KeKarLite.sh").read_text(encoding="utf-8")
    assert "KeKarLite_Linux/KeKarLite" in launcher
    assert "./KeKarLite.sh" in launcher


def test_full_usb_package_layout_is_unchanged(tool, tmp_path):
    source = tmp_path / "build" / "KeKar"
    (source / "_internal").mkdir(parents=True)
    (source / "KeKar").write_text("binary", encoding="utf-8")
    out = tool.make_platform_package(
        "linux", source, tmp_path / "out-full")
    assert (out / "KeKar_Linux" / "KeKar").exists()
    assert (out / "KeKar.sh").read_text(encoding="utf-8") == tool.SH
    assert (out / "README.txt").read_text(encoding="utf-8") == tool.README
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_usb_packaging.py -v`
Expected: `test_lite_usb_package_layout` fails with `TypeError: make_platform_package() got an unexpected keyword argument 'variant'`.

- [ ] **Step 3: Parameterize the packaging tool**

In `tools/make_usb_package.py`, change the three string constants into functions and keep the old names as full-mode aliases. Concretely, change `BAT = """..."""` to:

```python
def bat_for(variant: str) -> str:
    name = "KeKarLite" if variant == "lite" else "KeKar"
    return f"""@echo off
rem {name} launcher (Windows)
rem
rem Double-click this file to open {name}. It works from any drive letter and
rem leaves nothing behind on the computer except the KeKarData folder on this
rem drive.
setlocal
set "HERE=%~dp0"

if not exist "%HERE%{name}_Windows\\{name}.exe" (
  echo.
  echo  {name} was not found on this drive.
  echo  Look for the folder named {name}_Windows and try again.
  echo.
  pause
  exit /b 1
)

start "" "%HERE%{name}_Windows\\{name}.exe"
endlocal
"""
```

Do the same for `SH`:

```python
def sh_for(variant: str) -> str:
    name = "KeKarLite" if variant == "lite" else "KeKar"
    return f"""#!/bin/sh
# {name} launcher (Linux)
#
# Double-click this file, or run:  ./{name}.sh
# Works from any mount point; all data stays in the KeKarData folder here.
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -x "$HERE/{name}_Linux/{name}" ]; then
  echo "{name} was not found on this drive."
  echo "Look for the folder named {name}_Linux and try again."
  exit 1
fi

# Qt needs a platform plugin. On a headless machine fall back to offscreen so
# the app starts instead of aborting with "could not connect to display".
if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
  export QT_QPA_PLATFORM="${{QT_QPA_PLATFORM:-offscreen}}"
fi

exec "$HERE/{name}_Linux/{name}" "$@"
"""
```

Note the doubled braces `${{QT_QPA_PLATFORM:-offscreen}}` so `str.format` emits `${QT_QPA_PLATFORM:-offscreen}`.

For `README`, add `def readme_for(variant: str) -> str:` that returns the current text when `variant == "full"` and, when `"lite"`, the same text with `"KEKAR PROPERTY MANAGER"` → `"KEKAR LITE"`, every `KeKar.bat`/`KeKar.sh` → `KeKarLite.bat`/`KeKarLite.sh`, and the line `"Chat says it can't connect        Check the computer's internet, then retry"` removed. Keep the two-line SmartScreen advice verbatim.

After the three functions, add the aliases so existing drift tests and call sites are unchanged:

```python
BAT = bat_for("full")
SH = sh_for("full")
README = readme_for("full")
```

Change `make_platform_package(platform, source, out)` to `make_platform_package(platform, source, out, variant="full")`, and compute:

```python
    name = "KeKarLite" if variant == "lite" else "KeKar"
    target = out / f"{name}_{platform.capitalize()}"
```

Replace `_stage_icon(target)` with `_stage_icon(target)` (unchanged), and `_write_launchers(out)` with `_write_launchers(out, variant)`.

Change `_write_launchers(out)` to `_write_launchers(out, variant="full")`; inside, derive `name` the same way and write:

```python
    (out / f"{name}.bat").write_text(bat_for(variant), encoding="utf-8")
    sh = out / f"{name}.sh"
    sh.write_text(sh_for(variant), encoding="utf-8")
    sh.chmod(0o755)
    (out / "README.txt").write_text(readme_for(variant), encoding="utf-8")
```

Keep `install_linux.py` staging and the shared `KeKarData/` subdirectory loop unchanged. In `main()`, add:

```python
    parser.add_argument("--variant", choices=["full", "lite"], default="full")
```

and pass `args.variant` to `make_platform_package` / `combine` / `_write_launchers`.

In `tools/verify_usb.py`, add the same `--variant` argument and derive:

```python
    name = "KeKarLite" if variant == "lite" else "KeKar"
    builds = [b for b in (f"{name}_Windows", f"{name}_Linux") if (root / b).is_dir()]
    binary = f"{name}.exe" if platform == "windows" else name
    expected = ("KeKarData", "README.txt", f"{name}.sh", f"{name}.bat")
```

Keep every other check identical.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_usb_packaging.py -v`
Expected: 24 passed (22 existing + 2 new); `test_bat_matches_assets_source` and `test_sh_matches_assets_source` still pass because the aliases are byte-identical to full-mode output.

- [ ] **Step 5: Add both variants to CI**

In `.github/workflows/build.yml`, convert both jobs to `strategy.matrix`:

```yaml
    strategy:
      matrix:
        variant: [full, lite]
```

For each job, define a shell-agnostic suffix step before the build:

```yaml
      - name: Resolve variant names
        id: names
        shell: bash
        run: |
          if [ "${{ matrix.variant }}" = "lite" ]; then
            echo "app=KeKarLite" >> "$GITHUB_OUTPUT"
          else
            echo "app=KeKar" >> "$GITHUB_OUTPUT"
          fi
```

Then, in the Linux job, run PyInstaller through the stamp tool and package with the derived name:

```yaml
      - name: Build ${{ matrix.variant }}
        run: |
          KEKAR_VARIANT=${{ matrix.variant }} python tools/set_variant.py ${{ matrix.variant }} -- \
            python -m PyInstaller KeKar.spec --noconfirm
      - run: python tools/make_usb_package.py --platform linux --source dist/${{ steps.names.outputs.app }} --out out/${{ steps.names.outputs.app }}_Linux --variant ${{ matrix.variant }}
      - run: python tools/verify_usb.py out/${{ steps.names.outputs.app }}_Linux --platform linux --variant ${{ matrix.variant }}
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ steps.names.outputs.app }}_Linux
          path: out/${{ steps.names.outputs.app }}_Linux/
      - name: Zip the Linux package
        run: cd out && zip -qr ${{ steps.names.outputs.app }}_Linux.zip ${{ steps.names.outputs.app }}_Linux
      - name: Attach the Linux build to the release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: out/${{ steps.names.outputs.app }}_Linux.zip
```

Apply the same substitutions to the Windows job (keeping `shell: pwsh` for `Compress-Archive`). Keep the NSIS installer steps **outside** the matrix's Lite case by adding `if: matrix.variant == 'full'` to "Compile the NSIS installer" and "Attach the installer to the release"; the full Windows zip and installer continue to behave exactly as before. The four zips on a release are `KeKar_Linux.zip`, `KeKar_Windows.zip`, `KeKarLite_Linux.zip`, `KeKarLite_Windows.zip`.

- [ ] **Step 6: Verify both packages locally and commit**

Run: `.venv/bin/python -m pytest tests/test_usb_packaging.py tests/test_bundle_safety.py -v`
Expected: all pass. Then run the real Linux builds from Task 9:

Run: `bash build.sh`
Expected: `out/KeKar_Linux/` and `out/KeKarLite_Linux/` both created; both verify tools exit 0; `out/KeKarLite_Linux/KeKarLite_Linux/KeKarLite --version` prints `KeKar Lite <version>`.

```bash
git add tools/make_usb_package.py tools/verify_usb.py tests/test_usb_packaging.py .github/workflows/build.yml
git commit -m "build(lite): package and publish KeKarLite beside KeKar"
```

---

## Task 11: Documentation, real-display verification and release

**Files:**
- Modify: `README.md`, `docs/WIRING.md`, `docs/SPEC-COVERAGE.md`, `docs/TEST-MATRIX.md`
- Modify: `tests/test_usb_packaging.py` (one documentation guard test)

**Interfaces:**
- Consumes: all of Tasks 1–10.
- Produces: documentation that describes both variants; a human-run verification procedure with exact commands, observations and paste-back; a release checklist entry for the four zips.

- [ ] **Step 1: Write the failing documentation guard test**

Append to `tests/test_usb_packaging.py`:

```python
def test_readme_documents_both_variants():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in ("KeKar Lite", "copy-and-paste", "KEKAR_VARIANT",
                   "out/KeKarLite_Linux"):
        assert phrase in readme, f"README never mentions {phrase!r}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_usb_packaging.py::test_readme_documents_both_variants -v`
Expected: FAIL — `README never mentions 'KeKar Lite'`.

- [ ] **Step 3: Document the variant**

In `README.md`, add a "## KeKar Lite" section after "## Download" containing, verbatim in substance:

- "KeKar Lite is the same program with the unfinished external connections removed: Facebook Marketplace auto-fill, the AI chat assistant, short-stay portal calendar sync, and Google Maps address lookup. The `apartments.com`, Airbnb and Vrbo channel packages are hidden from the picker; generic, Zillow and Booking.com copy-and-paste listings stay."
- "Both builds use the same `KeKarData/` folder and the same SQLite schema; either can open a portfolio created by the other. No data is deleted or migrated."
- build commands: `bash build.sh` (both Linux builds) and `./build.ps1` (both Windows builds); releases attach `KeKarLite_Linux.zip` and `KeKarLite_Windows.zip`.
- `KEKAR_VARIANT=lite` selects the variant when running from source; an unset value always means full KeKar.
- the launcher names `KeKarLite.sh` / `KeKarLite.bat`.

In `docs/WIRING.md`, add a "## Build variants" section before "## Frozen vs. development" that states: `src/features.py` is the only switch; `src/_variant.py` is generated by `tools/set_variant.py` and gitignored; the guards sit in `Application` (agent stack), `MainWindow` (chat pane, provider ping), `PropertyForm` (publish button, Portals group), `ListingDialog` (channel picker), `SettingsDialog`/`FirstRunWizard` (API key UI), `tour.py` (step wording) and `KeKar.spec` (Playwright exclusion); repositories, schema and settings are identical. Add the Lite startup chain as a short code block.

In `docs/SPEC-COVERAGE.md`, add two rows: "KeKar Lite variant | `src/features.py`, `tools/set_variant.py` | `test_features.py`, `test_set_variant.py`, `test_kekar_lite.py`" and "KeKar Lite keeps copy-and-paste | `src/ui/listing_dialog.py`, `src/services/listing_compiler.py`, `src/services/clipboard.py` | `test_lite_ui.py`, `test_listing_channels.py`". Add a deviation row: "Portal calendar sync in Lite | removed for all three portals, including Booking.com | one unverified network subsystem is incompatible with an offline-only product (K4)".

In `docs/TEST-MATRIX.md`, add scenarios L1–L6 with columns Scenario / Command / Expected observation / Result:
- L1: `KEKAR_VARIANT=lite ./KeKarLite.sh` on a real display → window title "KeKar Lite Property Manager", no bottom chat pane, no status pill.
- L2: open a short-stay property → Type shows "Short stay", no Portals group, no "Publish to Marketplace…" button.
- L3: Properties → Preview listing → rental offers "Any site (generic)" and "Zillow"; short stay offers generic and Booking.com; "Copy to clipboard" works.
- L4: open the same `KeKarData/` with full KeKar → properties, applicants, leases, stays and the chat history are all still present.
- L5: unplug the network / block outbound traffic → every Lite feature works; no error dialogs.
- L6: `out/KeKarLite_Linux/KeKarLite_Linux/KeKarLite --version` → prints `KeKar Lite <version>` on a headless machine.

- [ ] **Step 4: Run the real-display verification (do not skip)**

On a machine with a display, after `bash build.sh`:

Run: `out/KeKarLite_Linux/KeKarLite_Linux/KeKarLite`
Observe and capture screenshots: the window opens; its title shows "KeKar Lite Property Manager"; the three-region card layout has only the property list and tab card (no chat pane); the Properties form shows "Preview listing" and "Copy listing" but no "Publish to Marketplace…" and no "Portals" group; the View menu has no "Collapse chat" entry.

Run: `out/KeKar/KeKar --version` and `out/KeKarLite_Linux/KeKarLite_Linux/KeKarLite --version`
Expected: `KeKar <version>` and `KeKar Lite <version>` respectively.

Run: `.venv/bin/python tools/verify_usb.py out/KeKarLite_Linux --platform linux --variant lite`
Expected: exit 0, no problems reported.

Paste each observation and screenshot path into the L1–L6 result column of `docs/TEST-MATRIX.md`. Mark nothing "verified" until this step has actually been executed.

- [ ] **Step 5: Full suite, docs test and commit**

Run: `.venv/bin/python -m pytest -o addopts='' -q`
Expected: `<BASELINE + 28> passed`, and the full suite under `KEKAR_VARIANT=lite .venv/bin/python -m pytest -o addopts='' -q` also passes.

```bash
git add README.md docs/WIRING.md docs/SPEC-COVERAGE.md docs/TEST-MATRIX.md tests/test_usb_packaging.py
git commit -m "docs(lite): document the offline variant and its test matrix"
```

- [ ] **Step 6: Release checklist**

On `release: published`, confirm CI attached all four zips (`KeKar_Linux.zip`, `KeKar_Windows.zip`, `KeKarLite_Linux.zip`, `KeKarLite_Windows.zip`) and the full-build installer `KeKar_Setup_<version>.exe`. Confirm the Windows job was green for both matrix cases before publishing; tag pushes alone attach nothing.

---

## Traceability matrix

| Request element | Where it is honoured | Verified by |
|---|---|---|
| Stripped-down simplified variant | K1–K2; Tasks 1–8 | `test_features.py`, `test_kekar_lite.py`, `test_lite_ui.py` |
| No direct Facebook connection | Task 2 (no autofill tool), Task 4 (no publish button), Task 6 (no autofill/browser settings), Task 9 (no Playwright in Lite bundle) | `test_lite_ui.py::test_lite_form_has_no_publish_or_portals_but_keeps_copy`, `test_lite_ui.py::test_lite_settings_hide_every_provider_control`, real build `KeKarLite.spec` |
| No AI Chat | Task 2 (no `client`/`agent_runner`/`chat_repo`), Task 3 (no pane/ping/banner), Task 6 (no key wizard or provider UI), Task 7 (no assistant tour step) | `test_kekar_lite.py::test_lite_application_has_no_agent_or_chat`, `test_lite_ui.py`, `test_tour.py` |
| No direct Vrbo/Airbnb connections | K4: Task 4 removes the whole Portals group; Task 9 excludes the network stack | `test_lite_ui.py::test_lite_form_has_no_publish_or_portals_but_keeps_copy` |
| No Apartments.com presence in Lite picker | K3: Task 5 filters `LITE_HIDDEN_CHANNELS` | `test_lite_ui.py::test_lite_listing_dialog_offers_only_local_rental_channels` |
| Keep listing copy-and-paste | K2/K3; Tasks 4 and 5 keep `compile_listing`, `copy_listing`, `ListingDialog`, generic + Zillow + Booking.com packages | `test_lite_ui.py::test_lite_form_still_saves_a_short_stay_without_portal_rows`, `test_lite_ui.py::test_lite_compile_channel_still_accepts_a_hidden_key`, all of `test_listing_channels.py` |
| Only remove what is not working | K3/K4: Zillow and Booking.com copy packages and every local feature kept; no data-layer or schema change | `test_lite_ui.py::test_full_usb_package_layout_is_unchanged`, `test_bundle_safety.py`, Task 11 matrix L4 |
| One codebase, not a separate repo | K1; Tasks 1, 9, 10 | `test_set_variant.py`, `tests/test_usb_packaging.py` |
| Preserve `KeKarData` portability and SQLite schema | K5/K6; no `src/data/*` or `src/config/settings.py` edits anywhere | `test_db.py`, `test_bundle_safety.py`, `test_settings.py`, matrix L4 |
| Offline-first | K2/K8/K11; Tasks 2, 3, 4, 6 | `test_lite_ui.py::test_lite_window_has_no_chat_controls_or_offline_ping`, `test_lite_ui.py::test_lite_form_never_starts_a_maps_request`, matrix L5 |
| Google Maps disabled in Lite | K11; Tasks 1, 4, 6 | `test_features.py::test_lite_disables_google_maps_suggestions`, `test_lite_ui.py::test_lite_settings_hide_every_provider_control` |
| Do not break existing KeKar users | Default `full`; Tasks 2–8 keep their full-mode assertions; Task 10 keeps full artifacts | full suite with no env var; `test_full_application_still_has_the_agent` |
| Files/features removed or hidden | Scope table + File Structure + K9 | Task-level file lists |
| Tests added/updated | Tasks 1–11 | `BASELINE + 28` at final run |
| Real-display verification | Distribution & Portability; Task 11 Step 4 | matrix L1–L6 with screenshots |
| Packaging/build/release | Tasks 9, 10, 11 Step 6 | `bash build.sh`, `verify_usb.py`, CI four-zip check |

**Deliberate deviations, stated explicitly:**

1. **K3** hides the Airbnb, Vrbo and apartments.com *copy packages* in Lite as well as their connections. If the intent was to keep those packages, set `LITE_HIDDEN_CHANNELS = frozenset()` in `src/features.py` and update the two channel-picker tests in Task 5; nothing else changes.
2. **K4** removes Booking.com's portal calendar sync although the request named only Airbnb and Vrbo, because the mechanism is shared and unverified. Booking.com's copy package stays.
3. **K10** ships no KeKar Lite NSIS installer; the Lite zip plus its launcher is the only distribution path.
4. **K9** leaves unused modules and `config/marketplace_selectors.json` in the source tree; "stripped down" is enforced at import/bundle level, not by deleting files full KeKar still needs.
5. **K11** disables Google Maps address lookup in Lite even though the request never named it, because it is another outbound third-party call; the `maps_key`/`maps_autofill` settings fields remain. Set `maps_enabled()` to `return True` and drop the two Lite Maps assertions if that feature should survive in Lite.

---

## Self-review

**Spec coverage.** Every clause in the request maps to at least one task in the traceability matrix. There is no task whose removal would leave a named requirement unimplemented. The three clauses that could be read two ways ("direct connections", whether named site packages are kept, whether Booking.com sync goes) are resolved in K2–K4 and K11 and surfaced as deviations.

**Placeholder scan.** No "TBD", "TODO", "implement later", "fill in details", "add error handling", "write tests for the above", or "similar to Task N" appears. Every code step contains the actual code or the exact widget/field specification; every test step contains assertions and an exact command. The only intentional ellipses are inside quoted blocks that explicitly say "the existing block, unchanged" and then enumerate the surrounding edits — those blocks are already in the repository and are identified by file and line range.

**Type and name consistency.** `features.variant/is_lite/chat_enabled/marketplace_enabled/portal_sync_enabled/maps_enabled/visible_channels` are defined in Task 1 and used with those exact names in Tasks 2–8 and 11. `Application.chat_repo is None` (Task 2) matches the `features.chat_enabled()` guards in Task 6. `MainWindow.chat_pane` is `None` or `ChatPane` (Task 3) and is checked before every use in Tasks 2, 3 and 7. `PropertyForm.publish_btn`/`portals_box` are `None` or widgets (Task 4) with matching guards in every helper. `tools/set_variant.py::stamp` and the `STAMP` module constant are the names monkeypatched in Task 9. `KeKarLite` is the artifact and executable name in Tasks 8–10; `KeKar Lite` is the display name; `KeKar` remains the application/data name. `APP_VERSION` is never changed, so the NSI alignment test holds.

**Ordering.** Task 1 must land first (all guards import `features`). Tasks 2 and 3 land together if the subprocess test in Task 2 fails only on `chat_pane`. Tasks 4–7 each depend only on Task 1 plus the task before them. Task 8 can be folded into Task 3 if desired, but its tests must still pass. Tasks 9 and 10 depend on the display name from Task 8 for the CLI assertion. Task 11 depends on all previous tasks.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-24-kekar-lite.md`. Two execution options:

**1. Subagent-Driven (recommended)** — a fresh subagent per task, review between tasks, fast iteration. Required sub-skill: `superpowers:subagent-driven-development`.

**2. Inline Execution** — execute tasks in this session with checkpoints for review. Required sub-skill: `superpowers:executing-plans`.

Which approach?
