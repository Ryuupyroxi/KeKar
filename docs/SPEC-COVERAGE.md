# KeKar — Specification Coverage

Traceability from the source specification to the code that implements it.
Source documents:

- Spec: `/home/Ryuu/Documents/KeKar - Digital Property Manager Specification.pdf`
- Proposal: `/home/Ryuu/Fenrys-Backup/hermes/profiles/fenrys/KeKar_Rental_Properties_Proposal.pdf`

Decision references (D1-D10) are defined in Part 1 of
`docs/KeKar-Build-Plan.md`.

| Spec § | Requirement | Implemented in | Verified by |
|---|---|---|---|
| §1 | Single-click tool, no CLI | `assets/launchers/KeKar.bat`, `KeKar.sh` | `test_usb_packaging.py` |
| §2 | PyQt6 GUI | `src/ui/*` | `test_gui_smoke.py` |
| §2 | Embedded agent skeleton | **D4** — `src/agent/*` | `test_agent_*.py` |
| §2 | SQLite local database | `src/data/db.py`, `schema.sql` | `test_db.py` |
| §2 | Playwright/CDP integration | `src/services/browser/*` | `test_cdp_client.py`, `test_launcher.py`, `test_marketplace.py` |
| §2 | PyInstaller packaging | `KeKar.spec`, `build.sh`, `build.ps1` | real build + `KeKar --version` |
| §3.1 | Property schema + amenity toggles | `src/data/models.py`, `property_repo.py`, `src/ui/property_form.py` | `test_property_repo.py`, `test_gui_smoke.py` |
| §3.2 | Listing generator + clipboard + Marketplace | `src/services/listing_compiler.py`, `clipboard.py`, `browser/marketplace.py` | `test_listing_compiler.py`, `test_listing_templates.py`, `test_clipboard.py`, `test_marketplace.py` |
| §3.3 | Scoped conversational assistant | `src/agent/runner.py`, `src/ui/chat_pane.py` | `test_agent_runner.py`, `test_gui_smoke.py` |
| §3.4 | Applicant tracker | `src/data/applicant_repo.py`, `src/ui/crm_tab.py` | `test_applicant_repo.py`, `test_gui_smoke.py` |
| §5.1 | SOUL.md persona | `src/agent/soul.py` | `test_agent_tools.py` |
| §5.2 | MEMORY.md + local state | `src/agent/memory.py` → `KeKarData/memory/MEMORY.md` | `test_memory.py` |
| §5.3 | `browser.use_real_profile` | **D5** — dedicated profile via CDP, `browser/launcher.py` | `test_launcher.py` |
| §6 | Low-friction onboarding | `src/ui/wizard.py` | `test_gui_smoke.py` |
| §7.1 | Data folder layout | **D3** — portable `KeKarData/` instead of `%APPDATA%` | `test_paths.py` |
| §7.2 | Exact table schemas | `src/data/schema.sql` (field names verbatim) | `test_db.py`, `test_bundle_safety.py` |
| §8.1 | Split-pane dashboard + drawer | `src/ui/main_window.py`, `property_drawer.py` | `test_gui_smoke.py` |
| §8.2 | Embedded chat | `src/ui/chat_pane.py` | `test_gui_smoke.py` |
| §8.3 | CRM tab | `src/ui/crm_tab.py` | `test_gui_smoke.py` |
| §9 | Build milestones 1-5 | Phases 0-6 | README status table |
| §10.1 | USB portable bundle | `tools/make_usb_package.py`, `copy_to_usb.sh` | `test_usb_packaging.py`, real copy + verify |
| §10.2 | Dedicated API account + encrypted storage | **D6** — `src/config/crypto.py`, `settings.py` | `test_crypto.py`, `test_settings.py` |
| §10.3 | Pre-bundled toolsets | `src/agent/tools.py` (four toolsets as functions) | `test_agent_tools.py` |
| §11.1 | Offline degradation + friendly errors | `src/ui/main_window.py` (offline banner), `chat_pane.py` | `test_gui_smoke.py` |
| §11.2 | Image compression + attachment | `src/services/image_service.py` | `test_image_service.py` |
| §11.3 | The four named tools | `src/agent/tools.py` | `test_agent_tools.py` |
| §12.1 | First-run welcome + key handshake | `src/ui/wizard.py` | `test_gui_smoke.py` |
| §12.2 | Zero-touch subsequent launches | `Settings.load()` in `src/app.py` | `test_settings.py` |
| §14.1 | Questionnaire + document storage | `src/data/applicant_repo.py` (`add_document`, `documents`) | `test_applicant_repo.py` |
| §14.2 | AI applicant summaries | `src/agent/tools.py` + `chat_pane.py` | `test_agent_tools.py` |

## Deliberate deviations from the spec

| Spec says | KeKar does | Why |
|---|---|---|
| `%APPDATA%\KeKar` data location | Portable `KeKarData/` next to the executable | Spec §7.1 breaks portability and cannot work on Linux (D3) |
| "Embedded Hermes Agent Skeleton" | Lightweight in-app agent loop | Real Hermes is ~1.9 GB and its venv is full of symlinks, which FAT32/exFAT cannot store (D4) |
| `browser.use_real_profile` | Dedicated KeKar browser profile over CDP | Chrome/Edge refuse remote debugging on the default profile (D5) |
| Windows only | Windows + Linux, one source tree | Every layer was already cross-platform (D1) |
| — | Marketplace autofill stops before Publish | Human-in-the-loop requirement; never publishes (R3) |
