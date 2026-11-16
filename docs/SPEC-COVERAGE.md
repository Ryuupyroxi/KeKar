# KeKar — Specification Coverage

Traceability from the source specification to the code that implements it.
Source documents:

- Spec: `/home/Ryuu/Documents/KeKar - Digital Property Manager Specification.pdf`
- Proposal: `/home/Ryuu/Fenrys-Backup/hermes/profiles/fenrys/KeKar_Rental_Properties_Proposal.pdf`

Decision references (D1-D10) are defined in Part 1 of
`docs/KeKar-Build-Plan.md`.

| Spec § | Requirement | Implemented in | Verified by |
|---|---|---|---|
| §1 | Single-click tool, no CLI | `assets/launchers/KeKar.bat`, `KeKar.sh`, `tools/install_linux.py` | `test_usb_packaging.py` |
| §2 | PyQt6 GUI | `src/ui/*` | `test_gui_smoke.py` |
| §2 | Embedded agent skeleton | **D4** — `src/agent/*` | `test_agent_*.py` |
| §2 | AI provider detection, switching, and model discovery | `src/agent/providers.py`, `src/ui/settings_dialog.py` | `test_providers.py`, `test_ui_behaviour.py` |
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
| §6 | First-run guided tour on demo data | `src/ui/tour.py`, `src/data/demo_seed.py`, `src/app.py::maybe_offer_tour` | `test_tour.py`, `test_demo_mode.py` |
| §6 | Demo mode on a separate database, real data untouched | `src/paths.py::demo_database_path`, `src/app.py::enter/exit_demo_mode` | `test_demo_mode.py` |
| §7.1 | Data folder layout | **D3** — portable `KeKarData/` instead of `%APPDATA%` | `test_paths.py` |
| §7.2 | Exact table schemas | `src/data/schema.sql` (field names verbatim) | `test_db.py`, `test_bundle_safety.py` |
| §8.1 | Split-pane dashboard + drawer | `src/ui/main_window.py`, `property_drawer.py` | `test_gui_smoke.py`, `test_ui_behaviour.py` |
| §8.2 | Embedded chat | `src/ui/chat_pane.py` | `test_gui_smoke.py` |
| §8.3 | CRM tab | `src/ui/crm_tab.py` | `test_gui_smoke.py`, `test_ui_behaviour.py` |
| §8.1 | Readable typography (no tiny default fonts) | `src/ui/theme.py`, `widgets.py` | `test_ui_behaviour.py` |
| §8.1 | Property rows paint themselves (no child widget tree) for list speed | `src/ui/property_drawer.py` | `test_ui_behaviour.py`, `tools/measure_performance.py` |
| §8.1 | Inclusive search (address, city, ZIP, pet policy, notes, amenities) | `src/ui/property_drawer.py::search_text` | `test_ui_behaviour.py` |
| §3.2 | Marketplace autofill UI with a hard stop before Publish | `src/ui/marketplace_dialog.py` | `test_ui_behaviour.py`, `test_marketplace.py` |
| §3.2 | Listing preview and one-click copy | `src/ui/listing_dialog.py`, `src/services/clipboard.py` | `test_ui_behaviour.py`, `test_clipboard.py` |
| §3.4 | Applicant linked to a property | `src/ui/crm_tab.py`, `src/data/applicant_repo.py` | `test_ui_behaviour.py`, `test_applicant_repo.py` |
| §9 | Build milestones 1-5 | Phases 0-6 | README status table |
| §10.1 | USB portable bundle | `tools/make_usb_package.py`, `copy_to_usb.sh` | `test_usb_packaging.py`, real copy + verify |
| §10.2 | Dedicated API account + encrypted storage | **D6** — `src/config/crypto.py`, `settings.py` | `test_crypto.py`, `test_settings.py` |
| §10.3 | Pre-bundled toolsets | `src/agent/tools.py` (four toolsets as functions) | `test_agent_tools.py` |
| §11.1 | Offline degradation + friendly errors | `src/ui/main_window.py` (offline banner), `chat_pane.py` | `test_gui_smoke.py` |
| §11.2 | Image compression + attachment | `src/services/image_service.py` | `test_image_service.py` |
| §11.3 | The four named toolsets — `db_query_tool`, `listing_compiler_tool`, `clipboard_bridge_tool`, `browser_automation_tool` — exposed as 12 whitelisted functions | `src/agent/tools.py` (`TOOL_SCHEMAS`: property/applicant CRUD + status + stage, `listing_compile`, `clipboard_copy`, `marketplace_autofill`, memory read/write) | `test_agent_tools.py` |
| §12.1 | First-run welcome + key handshake | `src/ui/wizard.py` | `test_gui_smoke.py` |
| §12.2 | Zero-touch subsequent launches | `Settings.load()` in `src/app.py` | `test_settings.py` |
| §14.1 | Questionnaire + document storage | `src/data/applicant_repo.py` (`add_document`, `documents`) | `test_applicant_repo.py` |
| §14.2 | AI applicant summaries | `src/agent/tools.py` + `chat_pane.py` | `test_agent_tools.py` |
| §3.5 | Lease drawn up from the client's example lease | `src/services/lease_builder.py`, `src/data/lease_repo.py`, `src/ui/lease_tab.py` | `test_leases.py` |
| §3.2 | Per-channel listing packages (Zillow, apartments.com) | `src/services/listing_channels.py`, `src/ui/listing_dialog.py` | `test_listing_channels.py` |
| §8.1 | Collapsible property list and chat panels | `src/ui/main_window.py` (`CollapsibleSplitter`, menu-bar toggles) | `test_layout.py` |
| §8.1 | Light, dark and OLED themes with WCAG contrast | `src/ui/palette.py`, `src/ui/theme.py`, `src/config/settings.py` | `test_themes.py` |
| §6 | Guided tour covers the Leases tab | `src/ui/tour.py` | `test_tour.py`, `test_leases.py` |
| §8.1 | Supplied icon and logo wired into the window, start menu, About and the packages | `src/paths.py::resource_path`, `src/ui/main_window.py::_set_logo`, `src/app.py`, `packaging/linux/kekar.desktop`, `packaging/linux/kekar.png`, `packaging/windows/kekar.ico`, `tools/make_usb_package.py` | `test_branding.py`, `test_usb_packaging.py` |
| §8.1 | Accounts and login plumbing (the client-facing feature's foundation) | `src/services/auth.py`, `src/data/user_repo.py`, `src/ui/login_dialog.py`, `src/ui/users_dialog.py` | `test_auth.py` |
| §7.2 | Short-stay property kind and its own terms (design: `2026-11-15-airbnb-short-stay-design.md`) | `properties.kind` + 10 columns, `Database._add_missing_columns`, `src/ui/property_form.py` (`kind_combo`, Rental/Short-stay terms) | `test_short_stay.py`, `test_property_repo.py` |
| §3.2 | Short-stay listing packages (Airbnb, Vrbo, Booking.com) and per-portal overrides | `src/services/listing_channels.py`, `src/ui/listing_dialog.py` | `test_short_stay.py`, `test_listing_channels.py` |
| §8.3 | Reservations: calendar, bookings table, overlap rejection | `src/data/booking_repo.py`, `src/ui/stays_tab.py` | `test_short_stay.py` |
| §10.1 | Two-way portal calendar sync over iCal, with a sync log | `src/services/ical_service.py`, `src/services/portal_sync.py`, `src/data/portal_repo.py`, `property_portals` / `portal_sync_log` | `test_short_stay.py` |

## Deliberate deviations from the spec

| Spec says | KeKar does | Why |
|---|---|---|
| `%APPDATA%\KeKar` data location | Portable `KeKarData/` next to the executable | Spec §7.1 breaks portability and cannot work on Linux (D3) |
| "Embedded Hermes Agent Skeleton" | Lightweight in-app agent loop | Real Hermes is ~1.9 GB and its venv is full of symlinks, which FAT32/exFAT cannot store (D4) |
| `browser.use_real_profile` | Dedicated KeKar browser profile over CDP | Chrome/Edge refuse remote debugging on the default profile (D5) |
| Windows only | Windows + Linux, one source tree | Every layer was already cross-platform (D1) |
| — | Marketplace autofill stops before Publish | Human-in-the-loop requirement; never publishes (R3) |
| "Full channel management" for Airbnb/Vrbo/Booking.com | KeKar owns bookings and per-portal pricing; calendars sync by iCal; listing copy is a per-portal package | None of the three exposes a posting API to an independent host — the design doc records the constraint |
