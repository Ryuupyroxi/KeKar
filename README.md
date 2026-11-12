# kekar project

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
| `tests/` | pytest suite (28 test modules). |
| `config/` | Listing templates, default config, Marketplace selectors. |
| `tools/` | Build, packaging, and USB copy/verify tools. |
| `packaging/` | NSIS installer (Windows) and AppImage builder (Linux). |
| `assets/` | Launchers and icons. |

## What we are building

A portable, self-contained desktop app that runs straight from a USB flash
drive on **both Windows 10/11 and Linux x86_64**, for a non-technical landlord.

One codebase, two PyInstaller builds, one shared `KeKarData/` portfolio on the
drive. All data stays local; only the AI chat needs the network.

## Status

Implementation complete through Phase 7. **211 tests passing** (`pytest -q`).
Source: 48 modules, 4,575 lines.

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

## The interface

The window is three regions: a property list on the left, tabs on the right,
and the assistant along the bottom.

- **Property list** — each row is a cover thumbnail, the address as the title,
  and the city/ZIP underneath. Status is a coloured stripe on the left edge
  (green = Vacant, red = Rented), so the address is never crowded out by a
  badge. The search box is deliberately inclusive: it matches address, city,
  ZIP, pet policy, free-form notes **and every enabled amenity**, so
  "dishwasher" or "fenced yard" finds the right properties.
- **Properties tab** — a two-column form (Details, Financials, Amenities,
  Notes) that scrolls when the window is short, so no field is ever squeezed
  to nothing. Quick actions: Save, Copy listing, Preview listing, Publish to
  Marketplace, Mark as rented / vacant, Delete.
- **Photos** — import, thumbnail, set cover, delete. The cover becomes the
  row's thumbnail in the list.
- **Applicants tab** — a table of applicants with a colour-coded screening
  stage (Inquiry Received → Questionnaire Sent → Background Check →
  Approved / Rejected). Adding an applicant asks which property they are
  applying for. Pre-screening questions copy to the clipboard in one click.
- **Assistant** — the chat pane talks to the in-app agent, which can only call
  whitelisted tools (never raw SQL, never `eval`). Offline is handled with a
  banner and a status pill rather than a crash.

## Verified by real execution

- `bash build.sh` produces a working Linux one-folder build (`dist/KeKar`).
- `dist/KeKar/KeKar --version` prints `KeKar 0.1.0` on a headless machine.
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
- `tools/seed_first_run.py` writes an encrypted key and the resulting settings
  file loads back with `is_configured() == True`.
- The app was launched on a real display and screenshotted: the property list,
  the populated form (address, rent, bedrooms, amenities) and the photo panel
  all render with readable text at 1280x800.
- Startup crash fixed and re-verified. A `QThread` was destroyed while its
  thread was still unwinding, which makes Qt abort the whole process. It was a
  race, so it survived casual testing: 2 of 15 launches died. After the fix
  (`src/ui/worker.py`), 25 of 25 launches survived.

### Security review

See `docs/SECURITY.md`. Runtime dependencies were audited and raised:
`cryptography` 45.0.7 → 50.0.2 and `Pillow` 11.1.0 → 13.0.0, closing 53
pip-audit findings. Remaining findings are recorded with reasons.

The API key is encrypted at rest (AES-256-GCM), its key file is `0600`, and it
is redacted from every log line, dialog and crash report. It is never written
to the database.

### Known gaps before release

- `docs/TEST-MATRIX.md` scenarios 1-18 need a human on real hardware.
- Windows artifact requires a GitHub Actions run (no Windows machine here).
- Marketplace autofill is implemented but untested against the live Facebook DOM.

## Source documents (kept outside this folder, referenced by the plan)

- Spec: `/home/Ryuu/Documents/KeKar - Digital Property Manager Specification.pdf`
- Proposal: `/home/Ryuu/Fenrys-Backup/hermes/profiles/fenrys/KeKar_Rental_Properties_Proposal.pdf`
