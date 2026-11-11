# kekar project

One folder for everything KeKar. No stray files, no scattered repos, no
"where did I put that" — if it belongs to KeKar, it lives here.

## Where things are

| Path | What it is |
|---|---|
| `docs/KeKar-Build-Plan.md` | **Master build plan — start here.** 36 tasks, 8 phases, full code for the foundations. |
| `docs/SECURITY.md` | Security review checklist (created in Phase 7). |
| `docs/TEST-MATRIX.md` | Cross-platform end-to-end test matrix (created in Phase 7). |
| `src/` | Application source — Python 3.12, PyQt6, SQLite. |
| `tests/` | pytest suite. |
| `config/` | Listing templates and Marketplace selector configs. |
| `tools/` | Build, packaging, and USB copy/verify tools. |
| `packaging/` | NSIS installer (Windows) and AppImage builder (Linux). |
| `assets/` | Launchers and icons. |

## What we are building

A portable, self-contained desktop app that runs straight from a USB flash
drive on **both Windows 10/11 and Linux x86_64**, for a non-technical landlord.

One codebase, two PyInstaller builds, one shared `KeKarData/` portfolio on the
drive. All data stays local; only the AI chat needs the network.

## Status

Implementation complete through Phase 7. **139 tests passing** (`pytest -q`).

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

### Verified by real execution

- `bash build.sh` produces a working Linux one-folder build (`dist/KeKar`).
- `dist/KeKar/KeKar --version` prints `KeKar 0.1.0` on a headless machine.
- The built binary starts, creates `KeKarData/`, runs the schema migration, and
  reports `PRAGMA integrity_check = ok`. Confirmed by running the binary.
- `tools/make_usb_package.py` + `tools/verify_usb.py` pass on the real build.
- `tools/copy_to_usb.sh` copied 553 files to a mock drive and verified every
  SHA-256.
- `assets/launchers/KeKar.sh` launches the built app from any working directory,
  including from a copy of the package on another path.
- `tools/seed_first_run.py` writes an encrypted key and the resulting settings
  file loads back with `is_configured() == True`.

### Security review

See `docs/SECURITY.md`. Runtime dependencies were audited and raised:
`cryptography` 45.0.7 → 50.0.2 and `Pillow` 11.1.0 → 13.0.0, closing 53
pip-audit findings. Remaining findings are recorded with reasons.

### Known gaps before release

- `docs/TEST-MATRIX.md` scenarios 1-18 need a human on real hardware.
- Windows artifact requires a GitHub Actions run (no Windows machine here).
- No git history yet; the plan's commit steps have not been run.
- Marketplace autofill is implemented but untested against the live Facebook DOM.

## Source documents (kept outside this folder, referenced by the plan)

- Spec: `/home/Ryuu/Documents/KeKar - Digital Property Manager Specification.pdf`
- Proposal: `/home/Ryuu/Fenrys-Backup/hermes/profiles/fenrys/KeKar_Rental_Properties_Proposal.pdf`
