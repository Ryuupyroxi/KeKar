# KeKar Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every gap between what KeKar v1.2.0 claims and what has actually been proven, building the automatable ones and writing executable procedures for the ones that need a human or real credentials.

**Architecture:** Three code phases (CI installer, live-sync harness, config cleanup) that a worker can finish without a human, and three procedure phases (live portal sync, live Marketplace autofill, Windows hardware, human test matrix) that turn "someone should check that" into a checklist somebody can complete in one sitting. Each procedure names the exact command, the exact observation, and what to paste back.

**Tech Stack:** Python 3.12 · PyQt6 · SQLite · GitHub Actions (`windows-latest`, `ubuntu-22.04`) · NSIS/makensis · pytest 8 + pytest-qt · `tools/verify_usb.py` manifest check.

## Global Constraints

- The suite must stay green: `.venv/bin/python -m pytest -o addopts='' -q` → **387 passed** is the baseline; every phase ends above it.
- `pytest.ini` sets `addopts = -q`; a second `-q` hides the summary. Use `-o addopts=''` whenever a doc needs the real `N passed` count.
- Never re-measure a number out of a doc: run the command, then edit.
- Docs that must stay true after any phase: `README.md` (status, known gaps), `docs/TEST-MATRIX.md`, `docs/WIRING.md`, `docs/SECURITY.md`, `docs/SPEC-COVERAGE.md`.
- `packaging/windows/KeKar_Installer.nsi` carries `!define VERSION`, and `tests/test_main_cli.py::test_app_version_matches_nsi_installer` fails if it drifts from `src/_version.py`. Bump both together.
- A tag push builds artifacts but attaches nothing: the workflow's attach steps are `if: github.event_name == 'release'`. Publishing the release is what attaches.
- The suite is POSIX-oriented; it runs on the Linux CI job only. The Windows job builds and packages.
- Nothing here changes app behaviour for a long-term rental.

## Key Decisions

**D1 — the login-gated "portal" is not a gap, and is not planned.** The word
appears only in `README.md` and `docs/HANDOFF.md`, written by earlier sessions.
The specification's §12.1 "First-Run Welcome & Authentication Dialog" is the
API-key handshake, and `docs/KeKar-Build-Plan.md` never mentions a portal. What
exists (`src/services/auth.py`, `user_repo.py`, `LoginDialog`, `UsersDialog`,
`MainWindow.set_locked`) is working plumbing for a feature that was never
specified. Planning it here would silently invent a product. If Master wants it,
that is its own spec → plan cycle.

**D2 — direct posting stays out of scope.** Airbnb, Vrbo, Booking.com, Zillow and
apartments.com expose no posting API to an independent host, and Facebook sits
behind anti-automation. Copy-and-paste plus the opt-in autofill that stops before
Publish is the design.

**D3 — the human gaps are delivered as procedures, not as code that pretends to
verify them.** A script cannot click "Run anyway" through SmartScreen, and a test
fixture is not a live portal calendar. Each procedure names the command, the
observation and the paste-back.

**D4 — build the installer on the Windows runner, not under wine.** `windows-latest`
is a real Windows environment, so `makensis` runs natively and the artifact is a
genuine Windows installer. Wine on the Linux job would be a second, flaky path.
The probe (Task 1.1) refined this: NSIS is **not** on the runner image and
choco's PATH update does not reach the job, so the step installs NSIS via choco
and invokes `makensis.exe` by full path.

## Gap inventory

| # | Gap | Kind | Closed by | Who |
|---|---|---|---|---|
| G1 | The NSIS installer is never built or attached by CI | code/CI | Phase 1 | Fenrys |
| G2 | Portal sync is only verified against a local `.ics` fixture | tool + human | Phase 2 | Fenrys builds, Master runs |
| G3 | Marketplace autofill has never run against the live Facebook DOM | procedure | Phase 3 | Master |
| G4 | The Windows build has never been run on real Windows hardware | procedure | Phase 4 | Master |
| G5 | `docs/TEST-MATRIX.md` scenarios 1-18 and 26-31 are blank | procedure | Phase 5 | Master |
| G6 | `~/.hermes/.env::GITHUB_TOKEN` holds the Discord bot token | config | Phase 6 | Fenrys |
| — | Direct posting to any site | not a gap (D2) | — | — |
| — | The login-gated portal | not a gap (D1) | — | — |

---

## Phase 1 — Build the Windows installer in CI

The installer script exists and is correct, but no job compiles it, so Windows
users only ever get a zip. This phase makes CI produce
`KeKar_Setup_1.2.0.exe` and attach it beside the two zips.

### Task 1.1: Probe the runner for makensis

**Files:**
- Read: `.github/workflows/build.yml`
- Read: `packaging/windows/KeKar_Installer.nsi`

**Interfaces:**
- Consumes: nothing
- Produces: a confirmed answer to "is `makensis` on PATH on `windows-latest`?"

- [ ] **Step 1: Add a temporary probe job**

Create `.github/workflows/probe.yml`:

```yaml
name: probe
on: workflow_dispatch
jobs:
  nsis:
    runs-on: windows-latest
    steps:
      - run: makensis /VERSION
```

- [ ] **Step 2: Run it**

Run: `gh workflow run probe.yml --repo Ryuupyroxi/KeKar` then
`gh run watch $(gh run list --repo Ryuupyroxi/KeKar --limit 1 --json databaseId --jq '.[0].databaseId')`
Expected: either a version string, or "command not found".

- [ ] **Step 3: Record the answer and delete the probe**

Delete `.github/workflows/probe.yml` and commit:

```bash
git rm .github/workflows/probe.yml
git commit -m "KeKar: drop the NSIS probe workflow"
```

### Task 1.2: Build and attach the installer

**Files:**
- Modify: `.github/workflows/build.yml` (the `windows` job, after the zip step)
- Modify: `tests/test_usb_packaging.py` (a guard that the workflow really builds it)

**Interfaces:**
- Consumes: `out/KeKar_Windows/` from the existing `make_usb_package.py` step;
  `${__FILEDIR__}\kekar.ico` resolved by the NSIS script.
- Produces: `out/KeKar_Setup_<version>.exe`, attached to the release.

- [ ] **Step 1: Write the failing test**

In `tests/test_usb_packaging.py`:

```python
def test_ci_builds_and_attaches_the_windows_installer():
    """A Windows release must carry the NSIS installer, not just the zip."""
    workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")
    assert "makensis" in workflow, "CI never compiles the NSIS installer"
    assert "KeKar_Setup_" in workflow, "CI never attaches the installer"
    assert "choco install nsis" in workflow, "no fallback if NSIS is absent"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_usb_packaging.py::test_ci_builds_and_attaches_the_windows_installer`
Expected: FAIL — "CI never compiles the NSIS installer".

- [ ] **Step 3: Add the build and attach steps**

In `.github/workflows/build.yml`, in the `windows` job, after
`Compress-Archive ... KeKar_Windows.zip` and before the attach step:

```yaml
      # NSIS is not on the runner image. Probed 2026-11-16: `makensis` is not
      # on PATH, `choco install nsis` deploys it to
      # C:\Program Files (x86)\NSIS but does NOT add it to PATH (a registry
      # Path refresh in-step does not help either), so call it by full path.
      - name: Compile the NSIS installer
        shell: pwsh
        run: |
          choco install nsis --yes --no-progress
          $nsis = "C:\Program Files (x86)\NSIS\makensis.exe"
          & $nsis /VERSION
          Push-Location out
          & $nsis ..\packaging\windows\KeKar_Installer.nsi
          Pop-Location
          Get-Item out\KeKar_Setup_*.exe | Select-Object Name, Length

      - name: Attach the installer to the release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: out/KeKar_Setup_*.exe
```

The tag is `v1.2.0` while the script's `OutFile` is `KeKar_Setup_1.2.0.exe`, so
the attach step globs rather than deriving the name from the tag. Task 1.3
guards both the `OutFile` pattern and the glob.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_usb_packaging.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/build.yml tests/test_usb_packaging.py
git commit -m "KeKar: build the Windows installer in CI and attach it to the release"
```

### Task 1.3: Guard the installer filename against version drift

**Files:**
- Modify: `tests/test_usb_packaging.py`

The attach step derives the filename from the tag; the script derives it from
`!define VERSION`. A tag of `v1.3.0` with a stale script would silently attach
the wrong file (or none). Add:

```python
def test_installer_output_name_matches_the_release_tag_scheme():
    """OutFile uses !define VERSION, so the tag and the script must agree."""
    nsi = Path("packaging/windows/KeKar_Installer.nsi").read_text(encoding="utf-8")
    assert 'OutFile "KeKar_Setup_${VERSION}.exe"' in nsi
    assert "github.ref_name" in Path(".github/workflows/build.yml").read_text(
        encoding="utf-8"
    ), "the attach step must key off the tag, not a hard-coded name"
```

- [ ] **Step 1: Run it** — Expected: PASS.
- [ ] **Step 2: Commit** — `git commit -am "KeKar: guard the installer name against version drift"`

### Task 1.4: Prove it on a real release

- [ ] **Step 1: Push a tag and watch both runs**

```bash
git tag -a v1.2.1 -m "KeKar v1.2.1"
git push origin v1.2.1
gh run watch $(gh run list --repo Ryuupyroxi/KeKar --limit 1 --json databaseId --jq '.[0].databaseId')
```

- [ ] **Step 2: Publish and confirm three assets**

```bash
gh release create v1.2.1 --title "KeKar v1.2.1" --notes "Installer-in-CI verification release."
gh run watch $(gh run list --repo Ryuupyroxi/KeKar --limit 1 --json databaseId --jq '.[0].databaseId')
gh release view v1.2.1 --repo Ryuupyroxi/KeKar --json assets --jq '.assets[].name'
```

Expected: `KeKar_Linux.zip`, `KeKar_Setup_1.2.1.exe`, `KeKar_Windows.zip`.

- [ ] **Step 3: Delete the throwaway release and tag**

`gh release delete v1.2.1 --repo Ryuupyroxi/KeKar --yes && git push origin :refs/tags/v1.2.1 && git tag -d v1.2.1`

- [ ] **Step 4: Update the docs**

`README.md` Download section: name the installer as the preferred Windows path and
keep the zip as the no-install fallback. `docs/TEST-MATRIX.md` scenario 24: add
"run KeKar_Setup_1.2.1.exe, confirm the Start-menu and Desktop shortcuts".

---

## Phase 2 — Live portal-sync harness

Portal sync is verified against a fixture in `tests/test_short_stay.py::CALENDAR`.
That proves the parser, not the portals' real iCal dialect. This phase gives
Master a safe way to run a real import without touching his database.

### Task 2.1: Write `tools/live_sync_check.py`

**Files:**
- Create: `tools/live_sync_check.py`
- Test: `tests/test_live_sync_check.py`

**Interfaces:**
- Consumes: `src.services.portal_sync.sync_portal`, `src.services.ical_service`,
  `src.data.db.Database`, `src.paths.data_dir`.
- Produces: `python tools/live_sync_check.py --url <ical-url> --portal airbnb`
  prints a dry-run report; `--commit` writes into a **copy** of the data dir.

- [ ] **Step 1: Write the failing test**

```python
def test_live_sync_check_reports_without_writing(tmp_path, monkeypatch):
    from src.data.db import Database
    from src.data.models import Property
    from src.data.property_repo import PropertyRepo
    from tools import live_sync_check

    data = tmp_path / "KeKarData"
    data.mkdir()
    db = Database(data / "database.db")
    prop_id = PropertyRepo(db).create(
        Property(address="7 Airbnb Way", kind="short_stay"))
    db.close()

    seen = {}

    def fake_sync(db, prop, portal):
        seen.update(prop=prop.id, portal=portal)
        return {"status": "ok", "added": 2, "updated": 0, "skipped": 1,
                "total": 3}

    monkeypatch.setattr(live_sync_check, "sync_portal", fake_sync)

    report = live_sync_check.run("https://example/cal.ics", "airbnb",
                                 source_dir=data)

    assert report["dry_run"] is True
    assert report["portal"] == "airbnb"
    assert report["added"] == 2
    assert report["property"] == "7 Airbnb Way"
    assert seen == {"prop": prop_id, "portal": "airbnb"}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_live_sync_check.py`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Implement it**

```python
#!/usr/bin/env python3
"""Import a real portal calendar into a COPY of the portfolio, and report.

    python tools/live_sync_check.py --url https://.../cal.ics --portal airbnb
    python tools/live_sync_check.py --url ... --portal vrbo --commit

Never writes to the real KeKarData: without --commit it works on a throwaway
copy under the scratch/tmp directory and prints what would change.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.db import Database
from src.data.models import (PORTALS, PORTAL_LABELS, PortalSettings,
                             Property)
from src.data.portal_repo import PortalRepo
from src.data.property_repo import PropertyRepo
from src.services.portal_sync import sync_portal


def run(url: str, portal: str, commit: bool = False,
        source_dir: Path | None = None) -> dict:
    if portal not in PORTALS:
        raise SystemExit(f"unknown portal: {portal} (choose from {PORTALS})")
    source_dir = (source_dir or
                  Path(__file__).resolve().parent.parent / "KeKarData")
    if not (source_dir / "database.db").exists():
        raise SystemExit(f"no portfolio at {source_dir}")
    scratch = Path(tempfile.mkdtemp(prefix="kekar-live-sync-"))
    target = scratch / "KeKarData"
    shutil.copytree(source_dir, target)
    try:
        db = Database(target / "database.db")
        repo = PropertyRepo(db)
        short_stays = repo.list(kind="short_stay")
        rentals = repo.list()
        prop = (short_stays or rentals or [None])[0]
        if prop is None:
            raise SystemExit("the portfolio has no property to import into")
        # The URL is handed to this tool, so store it before syncing —
        # otherwise sync_portal answers "no calendar URL is set".
        portals = PortalRepo(db)
        settings = portals.get(prop.id, portal) or PortalSettings(
            property_id=prop.id, portal=portal)
        settings.enabled = True
        settings.external_ical_url = url
        portals.save(settings)
        result = sync_portal(db, prop, portal)
        bookings = db.conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE property_id=?",
            (prop.id,)).fetchone()[0]
        result.update({
            "dry_run": not commit,
            "property": prop.address,
            "portal_label": PORTAL_LABELS[portal],
            "bookings_now": bookings,
            "copied_to": str(target),
        })
        return result
    finally:
        if not commit:
            shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="the portal's .ics URL")
    parser.add_argument("--portal", required=True, choices=PORTALS)
    parser.add_argument("--commit", action="store_true",
                        help="write into the copy (it is never the real data dir)")
    parser.add_argument("--source-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run(args.url, args.portal, commit=args.commit,
                 source_dir=args.source_dir)
    for key, value in report.items():
        print(f"{key}: {value}")
    return 0 if report.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_live_sync_check.py`
Expected: PASS.

- [ ] **Step 5: Run it against a served copy of the fixture**

```bash
SCRATCH=$(mktemp -d)
mkdir -p "$SCRATCH/KeKarData"
KEKAR_DATA_DIR="$SCRATCH/KeKarData" .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.data.db import Database
from src.data.models import Property
from src.data.property_repo import PropertyRepo
db = Database('$SCRATCH/KeKarData/database.db')
PropertyRepo(db).create(Property(address='7 Airbnb Way', kind='short_stay'))
db.close()"
.venv/bin/python -c "import tests.test_short_stay as t; print(t.CALENDAR)" \
  > "$SCRATCH/cal.ics"
.venv/bin/python tools/live_sync_check.py \
  --url "file://$SCRATCH/cal.ics" --portal airbnb \
  --source-dir "$SCRATCH/KeKarData"
```

`fetch_ical` is `urllib`, so a `file://` URL exercises the real fetch path with
no server to run. Expected: `status: ok`, `added: 1`, `dry_run: True`, and no
`copied_to` line (the copy is deleted unless `--commit` is passed).

- [ ] **Step 6: Commit**

`git add tools/live_sync_check.py tests/test_live_sync_check.py && git commit -m "KeKar: add a live portal-sync check that never touches the real portfolio"`

### Task 2.2: Write the human procedure

**Files:**
- Modify: `docs/TEST-MATRIX.md` (scenario 30, replace the "needs a real URL" note)

Add a "How to run scenario 30" block:

```markdown
## Scenario 30 — live portal sync

1. Log into the portal and copy its calendar export URL (Airbnb: Listing →
   Availability → Export calendar).
2. Run:
   .venv/bin/python tools/live_sync_check.py --url "<paste>" --portal airbnb
3. Expect `status: ok` and `added:`/`updated:` counts. Paste the whole output
   into this row.
4. In KeKar, open the Portals group for that property and press Sync now.
   Expect the same counts, and `Last sync:` to update.
5. Press Sync now a second time. Expect `status: unchanged` and `added: 0`.
6. Add one booking in KeKar, then Export calendar (.ics)… and open the file in
   a text editor. Expect a BEGIN:VCALENDAR with one VEVENT per live booking.
```

- [ ] **Step 1: Commit** — `git commit -am "KeKar: write the live portal-sync procedure"`

---

## Phase 3 — Live Marketplace autofill procedure

The autofill is implemented, opt-in, and stops before Publish. Nothing has run it
against the live DOM. This is a procedure, not code.

**Files:**
- Modify: `docs/TEST-MATRIX.md` (scenario 12)

- [ ] **Step 1: Write the procedure**

```markdown
## Scenario 12 — live Marketplace autofill

Needs: Facebook logged in once in KeKar's dedicated browser profile, and
Settings → Marketplace autofill turned on.

1. File → Settings → enable Marketplace autofill. Close the dialog.
2. Select a rental property with a photo. Properties tab → Publish to Marketplace…
3. The KeKar browser profile opens and navigates to the Marketplace listing form.
4. Watch it fill title, price, description and photos. It then STOPS.
5. Read the report in the dialog. Expect `autofilled` or `needs_review`.
   `failed` is also an acceptable result — record the message verbatim.
6. Confirm the browser tab still shows an unpublished draft: no Publish click.
7. Paste the report text and the dialog screenshot into this row.
```

- [ ] **Step 2: Record the selector state**

`config/marketplace_selectors.json` carries a `schema_version`. If the run reports
`needs_review`, update the selectors and bump that version.

- [ ] **Step 3: Commit** — `git commit -am "KeKar: write the live Marketplace autofill procedure"`

---

## Phase 4 — Windows-on-hardware smoke procedure

**Files:**
- Modify: `docs/TEST-MATRIX.md` (a new "Windows hardware pass" section)

- [ ] **Step 1: Write the checklist**

```markdown
## Windows hardware pass (scenarios 1-8, 11-18, 24, 26-31)

Run on the target Windows 10/11 machine, from the release zip.

1. Unzip KeKar_Windows.zip to a folder. Double-click KeKar.bat.
   SmartScreen: click More info → Run anyway. Record whether it appeared.
2. Scenarios 1-9 in order. Scenario 11 needs two machines or a VM.
3. Scenario 13: set the drive read-only (or use a read-only bind mount) and
   confirm the app warns and falls back instead of dying.
4. Scenario 14: corrupt KeKarData/database.db, relaunch, confirm the restore path.
5. Scenario 24: confirm the Start-menu and Desktop shortcuts, the taskbar icon
   and the title-bar icon all show the house mark.
6. Scenarios 26-31: the short-stay pass.
7. Paste back: KeKarData/logs/kekar.log (tail -40) and one screenshot per row.

What proves it: every row marked PASS with an observation, not "looked fine".
```

- [ ] **Step 2: Commit** — `git commit -am "KeKar: write the Windows hardware pass"`

---

## Phase 5 — Human test matrix

**Files:**
- Modify: `docs/TEST-MATRIX.md`
- Create: `tools/seed_matrix_data.py` (optional, only if Master wants a fixed portfolio)

- [ ] **Step 1: Split the matrix by risk**

Mark each scenario as `demo-safe` (run it in demo mode; nothing touches real data)
or `real-data` (needs a scratch copy of `KeKarData`). Demo mode already seeds four
properties and four applicants, so scenarios 4-9, 12, 16, 19-23 and 26-31 are
demo-safe; 1-3, 10-11, 13-15, 17-18 need a real install or a second machine.

- [ ] **Step 2: Add the routing column to the table**

Add a `Runs in` column with `demo` or `real` per row.

- [ ] **Step 3: Commit** — `git commit -am "KeKar: route each test-matrix row to demo mode or a real install"`

### Task 5.2 (optional): A fixed portfolio for repeatable runs

Only build this if Master wants the matrix repeatable. Skip it otherwise (YAGNI).

- [ ] **Step 1: Write `tools/seed_matrix_data.py`** that creates: two rentals (one
  Vacant with photos, one Rented), one short stay with a booking, one applicant at
  each screening stage, and one saved lease. Mirror the shape of
  `tools/seed_first_run.py`, which already writes a settings file.
- [ ] **Step 2: Test it** — `.venv/bin/python -m pytest -o addopts='' -q`
  Expected: 387 + N passed.
- [ ] **Step 3: Commit.**

---

## Phase 6 — Fix the mislabelled GitHub token

`~/.hermes/.env::GITHUB_TOKEN` is byte-identical to `DISCORD_BOT_TOKEN` and
returns `401 Bad credentials` from the GitHub API. `auth.json` carries the same
value twice more. Nothing in KeKar reads it, but the next tool that does will
send a Discord token to GitHub.

- [ ] **Step 1: Find every reader before removing anything**

```bash
grep -rn "GITHUB_TOKEN" /home/Ryuu/.hermes --include="*.py" --include="*.yaml" \
  --include="*.yml" --include="*.json" --include="*.env" 2>/dev/null
```

Expected: only the definitions, no readers.

- [ ] **Step 2: Remove the three copies**

```bash
sed -i '/^GITHUB_TOKEN=/d' /home/Ryuu/.hermes/.env
```

Then edit `/home/Ryuu/.hermes/profiles/fenrys/auth.json`: delete the top-level
`github_token` and the `credential_pool.github` entry, and write the file back
with the same permissions (`chmod 600`).

- [ ] **Step 3: Prove nothing broke**

```bash
gh auth status
git -C "/home/Ryuu/Documents/kekar project" push --dry-run origin main
```

Expected: gh still shows the keyring `ghp_` token; the dry-run succeeds.

- [ ] **Step 4: Do NOT commit anything** — these are outside the repo. Record the
change in `docs/HANDOFF.md` instead.

---

## Traceability

| Gap | Phase | Tasks | Proof |
|---|---|---|---|
| G1 installer never built by CI | 1 | 1.1-1.4 | a release with 3 assets, `KeKar_Setup_1.2.1.exe` present |
| G2 portal sync only fixture-tested | 2 | 2.1-2.2 | `tools/live_sync_check.py` output pasted into TEST-MATRIX row 30 |
| G3 autofill never run live | 3 | — | scenario 12 row filled with the report text |
| G4 Windows never run on hardware | 4 | — | the Windows hardware pass rows filled |
| G5 matrix blank | 5 | 5.1 (5.2 optional) | every row has an observation |
| G6 mislabelled token | 6 | — | `grep` finds no reader; `gh auth status` still green |
| Direct posting | — | — | not a gap (D2) |
| Login-gated portal | — | — | not a gap (D1); needs its own spec |

## Risks

- **The installer attach step may fail on the first try.** `OutFile` is written
  relative to the makensis CWD, and `softprops/action-gh-release` needs the exact
  filename. Task 1.3's test plus the throwaway v1.2.1 release are there to catch
  it before a real release.
- **`makensis` may be missing on the runner.** The probe in Task 1.1 decides; the
  `choco install nsis` fallback is in the step.
- **`choco install` needs a shell that can elevate.** On `windows-latest` the
  runner user is an administrator, so it works; if it does not, the step fails
  loudly rather than silently.
- **A live portal may return a calendar KeKar's parser rejects.** That is the
  point of Phase 2 — a real finding, not a plan failure. Record it and fix the
  parser in a follow-up.
- **Phase 6 edits files outside the repo.** Do it by hand, not from a script that
  could rewrite `auth.json` wholesale.

## As built (2026-11-16)

**Phase 1 — done and proven.** Three defects the plan did not anticipate, each
caught by the throwaway v1.2.1 release rather than by reading the code:

1. `makensis` is **not** on the `windows-latest` image, and
   `choco install nsis` deploys to `C:\Program Files (x86)\NSIS` **without**
   adding it to PATH — refreshing the registry PATH in-step does not help.
   The step calls `makensis.exe` by full path.
2. NSIS resolves `${__FILEDIR__}` against the CWD when the script is named
   relatively, so it looked for `packaging\packaging\windows\kekar.ico`.
   CI passes an absolute script path.
3. NSIS anchors **both** `File` and `OutFile` relative paths to the script, not
   the working directory. `KEKAR_PACKAGE_DIR` and `KEKAR_OUT_FILE` are now
   defines with portable defaults, and CI passes absolute values.

   Result: a release with `KeKar_Linux.zip`, `KeKar_Windows.zip` **and**
   `KeKar_Setup_1.2.0.exe` (100,411,978 bytes). The throwaway release and tag
   were deleted; v1.2.0 keeps its original two assets.

**Phase 2 — done.** `tools/live_sync_check.py` + 3 tests. Verified against the
fixture over `file://` (no server needed): `status: ok`, `added: 1`,
`dry_run: True`.

**Phases 3-5 — done.** Procedures written; the matrix now routes every row to
demo or real.

**Phase 6 — done, with one deviation.** Step 1 predicted "only the definitions,
no readers". That was wrong: `hermes_cli/git_credentials.py` reads `GITHUB_TOKEN`
as a git credential source. It already guards against a stale value (it yields
`GITHUB_TOKEN` first and `gh auth token` second and lets the remote decide), so
the bad token was only a wasted first attempt. `GITHUB_TOKEN` is removed from
`~/.hermes/.env`; `gh auth status` and `git push --dry-run` still work. A
backup is at `~/.hermes/.env.bak-20261116`.

`auth.json`'s `credential_pool.github` was **left alone**: no reader exists, and
it is Hermes's live credential store, so editing it risks the profile for no
gain. The mislabelled value there is still the Discord token and is still worth
clearing by hand.

## Definition of done

- `bash build.sh` green; suite above 387.
- A published release carries `KeKar_Linux.zip`, `KeKar_Windows.zip` and
  `KeKar_Setup_<version>.exe`.
- `docs/TEST-MATRIX.md` has no blank "Notes / evidence" cell for a scenario that
  has been run, and every human procedure names its command and its paste-back.
- `README.md` "Known gaps" lists only what is genuinely still open.
- `grep -rn "GITHUB_TOKEN" ~/.hermes` finds no definition.
