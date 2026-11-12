# KeKar End-to-End Test Matrix

Release gate for v0.1.0. Every scenario must be run by a human on real hardware
— these cannot be automated from the build machine. Check the box only after
watching the scenario pass.

**Legend:** PASS = observed working · FAIL = observed broken · n/a = not
applicable on that platform · blank = not yet run

| # | Scenario | Windows | Linux | Notes / evidence |
|---|---|---|---|---|
| 1 | First run: wizard creates `KeKarData/` and accepts a key | | | |
| 2 | Second run: wizard is skipped | | | |
| 3 | Add a property, save, restart, data persists | | | |
| 4 | Mark Vacant -> Rented -> Vacant | | | |
| 5 | Copy listing -> paste into Notepad/text editor, content correct | | | |
| 6 | Add photos, thumbnails appear, restart, photos persist | | | |
| 7 | Add applicant, change stage, restart, stage persists | | | |
| 8 | Chat: ask "which properties allow pets?" -> correct answer | | | |
| 9 | Chat with no network -> friendly message, no crash | | | |
| 10 | Kill the app mid-write, restart -> integrity check passes or restores | | | |
| 11 | Unplug and replug into a different machine -> data intact | | | |
| 12 | Marketplace autofill (if enabled) -> fills fields, never publishes | | | |
| 13 | Drive set to read-only -> app falls back to OS config dir with a warning | | | |
| 14 | Corrupt the DB -> app restores the newest backup automatically | | | |
| 15 | Run from a drive letter other than the build machine's | | n/a | |
| 16 | Copy listing to clipboard, paste into Facebook Marketplace manually | | | |
| 17 | Daily backup appears in `KeKarData/backups/` after 24 h | | | |
| 18 | Uninstall/remove the drive -> no leftover data in `%APPDATA%` or `~/.config` | | | |

## Automated coverage

These are covered by the pytest suite (`pytest -q`, 211 tests) and must stay
green:

- Schema creation, WAL mode, foreign keys, migration idempotency (`test_db.py`)
- Property and applicant CRUD, stage validation, document records
  (`test_property_repo.py`, `test_applicant_repo.py`)
- Backup, restore, prune, corruption recovery (`test_backup.py`)
- Listing compiler, including missing-optionals handling (`test_listing_compiler.py`)
- Versioned listing templates and the fallback when the file is missing
  (`test_listing_templates.py`)
- Image import, resize, thumbnail, cover selection, deletion (`test_image_service.py`)
- Agent tool schemas, dispatch, unknown-tool rejection (`test_agent_tools.py`)
- Agent loop: final answer, tool execution, cancellation, step limit
  (`test_agent_runner.py`)
- LLM fallback chain (`test_agent_client.py`)
- Provider key verification against `/models` (`test_agent_verify_key.py`)
- Settings encryption roundtrip, wrong-key failure, passphrase derivation
  (`test_crypto.py`, `test_settings.py`)
- Default config loader and its embedded fallback (`test_default_config.py`)
- Browser launcher flag construction, CDP connect failure handling
  (`test_launcher.py`, `test_cdp_client.py`)
- Marketplace autofill stops before Publish; missing selector -> `needs_review`
  (`test_marketplace.py`)
- GUI construction, drawer, form, photo panel, CRM, chat pane, wizard, settings
  (`test_gui_smoke.py`, headless `QT_QPA_PLATFORM=offscreen`)
- UI behaviour: typography, status stripes, inclusive search across amenities,
  listing preview/copy, marketplace dialog safeguards, applicant-property
  linking, CRM stage colours (`test_ui_behaviour.py`)
- CLI flags `--version`, `-V`, `--help` (`test_main_cli.py`)
- First-run key seeding roundtrip (`test_seed_first_run.py`)
- USB packaging: launcher sources stay in sync, package layout, reproducibility
  (`test_usb_packaging.py`)
- Frozen-bundle safety: no runtime dependency on an unshipped file
  (`test_bundle_safety.py`)

## How to run a scenario

1. Copy the package to the drive with `tools/copy_to_usb.sh <mount> <package>`.
2. Launch with `KeKar.bat` (Windows) or `./KeKar.sh` (Linux).
3. Perform the steps in the scenario.
4. Record the result and, for anything that failed, attach the relevant lines
   from `KeKarData/logs/kekar.log`.

## Known gaps

- Scenario 10 (kill mid-write) needs a manual `kill -9`; there is no automated
  test because the recovery path is exercised by `test_recovery_restores_on_corruption`
  instead.
- Scenario 13 (read-only drive) needs a physical write-protect switch or a
  read-only bind mount.
- Scenario 17 needs a 24-hour wait; the prune logic is covered by
  `test_prune`.
