# KeKar — Session Handoff Notes (2026-11-12 → 11-14)

Written for future sessions. Everything here was verified by real execution, not
by reading code.

---

## 1. Where things stand

**Repo:** https://github.com/Ryuupyroxi/KeKar (public, `main` branch, pushed)

**Release:** https://github.com/Ryuupyroxi/KeKar/releases/tag/v0.1.0
(Windows + Linux zips are attached by CI — see §5 for the current build status)

**Test suite:** 234 passing, 50 source modules, 5,130 lines.
Run with `pytest` or `python -m pytest` from the project root
(`/home/Ryuu/Documents/kekar project`).

**Commits this session** (newest first):

| Commit | What |
|---|---|
| `ab7d64b` | Attach Linux and Windows builds to GitHub releases |
| `1b14386` | Document demo mode and the guided tour |
| `cc10b7a` | Demo banner, Help menu tour entry, first-run prompt |
| `7de2a4a` | Guided tour overlay with spotlight and navigation |
| `7b2a9b1` | Seed the demo database with sample properties and applicants |
| `799230d` | Demo mode switches to a separate database |
| `e873ab9` | Implementation plan for demo mode and guided tour |
| `0a3c608` | Design spec for demo mode and guided tour |

---

## 2. What was built — demo mode + guided tour

### Demo mode

- `paths.demo_database_path()` → `<data_dir>/demo/database.db`.
  A **separate database file**; everything else (settings, memory, photos,
  logs) is shared with the real install. This was Master's explicit choice.
- `Application.enter_demo_mode()` / `exit_demo_mode()` close the current
  database, open the other one, rebuild the repositories, reload every view,
  and toggle the banner.
- **Both database paths are resolved once in `__init__`** and reused.
  Re-resolving on every switch would open a *different* file if the data
  directory changed mid-run — silently losing the real database. There is a
  regression test for exactly this (`test_demo_mode_keeps_the_database_it_started_with`).
- Seeded on entry by `src/data/demo_seed.py`: 4 properties, 4 applicants.
  Idempotent.
- **Session-only.** Nothing on disk records demo mode, so closing the app
  mid-tour returns the user to real data.
- **Settings are disabled during demo mode** (`File → Settings`), because the
  settings file is shared — otherwise a tour could change the real API key.

### Guided tour

- `src/ui/tour.py`: `TourStep`, `TourOverlay`, `build_tour_steps(window)`.
- The overlay is a **transparent child of the main window**. `paintEvent` fills
  the window with a dim colour clipped to everything *except* a hole around the
  target, then draws an amber ring. **No composition modes** — robust everywhere.
- Modal: captures clicks. `Esc` exits, arrow keys navigate.
- 8 steps. Step 5 (Applicants) switches to that tab and restores the previous
  tab on exit.
- Offered once after first-run setup via `Application.maybe_offer_tour()`;
  the answer is recorded in `Settings.tour_completed` either way.

---

## 3. Bugs found and fixed during implementation

These were real failures the tests caught. Do not reintroduce them.

1. **The app re-resolved the data directory on every database switch.**
   Symptom: a property created in the real database "vanished" after leaving
   demo mode — because `exit_demo_mode()` opened whatever `database_path()`
   resolved to *then*, not the file the app started with.
   Fix: resolve `_real_db_path` and `_demo_db_path` once in `__init__`.

2. **A tour step callback looked up its overlay with `findChild`.**
   `findChild` can return a *stale* overlay left behind by an earlier tour, so
   the tab to restore was recorded on the wrong object and the Applicants tab
   was never put back.
   Fix: `TourStep.on_enter` now receives the overlay running the step.

3. **`QRegion` is in `PyQt6.QtGui`, not `QtCore`.**

4. **`QAction` has no `isHidden()`** — use `isVisible()`.

5. **`pytest` does not put the project root on `sys.path`.** Locally we always
   ran `python -m pytest`, which does. Plain `pytest` (what CI used) failed with
   `ModuleNotFoundError: No module named 'src'`.
   Fix: `pythonpath = .` in `pytest.ini`.

---

## 4. Earlier in the same session (assistant not connecting)

The assistant was broken for **four separate reasons**; only the last two were
code defects.

1. Endpoint hardcoded to OpenRouter while the stored key was an OpenAI project
   key → every call 401'd.
2. The stored key is out of credit everywhere (OpenAI 429 "no credits
   remaining"; Nous/OpenRouter/Groq/DeepSeek all 401).
3. A working OpenRouter key was already on the machine, in Hermes's own auth
   pool (`~/.hermes/profiles/fenrys/auth.json`, `credential_pool.openrouter`).
   KeKar now uses it, on the `openrouter/free` chain.
4. Two code bugs that would have broken it anyway:
   - **SQLite is thread-pinned.** The connection was created in the GUI thread
     while the agent's tools run in a worker `QThread`; every tool call died with
     "SQLite objects created in a thread can only be used in that same thread".
     Fixed with per-thread connections (`threading.local`) in `Database`.
   - **The GUI never refreshed** after the agent wrote. Fixed with
     `Application.data_changed` → `MainWindow.reload_all`.

Also fixed: a reasoning model can return HTTP 200 with `content: null`; the
client now treats that as a per-model failure instead of a blank reply. And the
chat pane no longer hides the provider's real error behind "I can't reach the
assistant right now".

**Current provider config** (in `dist/KeKarData/config/settings.enc`):
provider `openrouter`, models
`['openrouter/free', 'nvidia/nemotron-3-ultra-550b-a55b:free',
'nvidia/nemotron-3.5-lightning:free', 'google/gemma-4-26b-a4b-it:free']`.

`openrouter/free` is OpenRouter's **free-models router** — it picks whichever
free model is live, so it needs no credits and survives catalogue changes.

---

## 5. Windows release — what was done and what to check

- CI already existed (committed before this session) in
  `.github/workflows/build.yml`: builds **both** Linux and Windows with
  PyInstaller, packages via `tools/make_usb_package.py --platform <linux|windows>`,
  verifies via `tools/verify_usb.py`, uploads artifacts.
- I added: a `release: types: [published]` trigger, and zip + attach steps so
  both `.zip` files land on the release page for the client to download.
- I **removed** my own `tools/make_windows_package.py` — it was redundant with
  the existing packager.
- Repo created with `gh repo create KeKar --public --source=. --push`.
- Release `v0.1.0` published.

### To verify after a build

```bash
gh run list --repo Ryuupyroxi/KeKar --limit 3
gh run view <run-id> --repo Ryuupyroxi/KeKar --log-failed
gh release view v0.1.0 --repo Ryuupyroxi/KeKar --json assets --jq '.assets[].url'
```

### Known remaining issue

The Windows build is **not code-signed**, so SmartScreen warns on first run.
`START-HERE.txt` and the release notes tell the user to click
**More info → Run anyway**. A code-signing certificate is the real fix — Master
has not decided on that yet.

---

## 6. Design docs

- Spec: `docs/superpowers/specs/2026-11-12-demo-mode-and-guided-tour-design.md`
- Plan: `docs/superpowers/plans/2026-11-12-demo-mode-and-guided-tour.md`

Both are committed. The plan's task list is complete.

---

## 7. Useful commands

```bash
cd "/home/Ryuu/Documents/kekar project"

# tests
pytest                                        # or: python -m pytest

# full build (tests + pyinstaller + linux package + verify)
bash build.sh

# run the app against a throwaway data dir (keeps the real one pristine)
KEKAR_DATA_DIR=/tmp/kekar-test DISPLAY=:0 ./dist/KeKar/KeKar

# show the tour on a real display for a screenshot
python /home/Ryuu/.hermes/profiles/fenrys/cache/scratch/show_tour.py

# measure facts before editing any doc
find src -name '*.py' | wc -l
find src -name '*.py' -exec cat {} + | wc -l
pytest | tail -1
```

### Verifying UI changes

KeKar's UI must be checked on a **real display**, not offscreen — offscreen
hides layout faults (squashed group boxes, clipped text). A real X server is
usually running on `:0` even when `DISPLAY` is empty in the shell.

```bash
DISPLAY=:0 xdotool search --name "^KeKar Property Manager$"
DISPLAY=:0 import -window root /tmp/shot.png
```

Window coordinates matter: the window sits at `(0, 44)` on this machine, so
absolute clicks need `+44` on the y axis. Use `xdotool getwindowgeometry --shell
<wid>` to check.

---

## 8. Conventions worth keeping

- **Never trust a doc's numbers.** Re-measure the test count, module count and
  LOC before editing any document.
- **End-to-end beats unit tests** for cross-thread and UI paths. A green suite
  hid two crashes that only happened in the real app.
- **Resolve paths once at startup**, not per call, when a component holds them
  for a session.
- **Bind callbacks to the object that owns them**, never look them up by type.
- Repositories resolve `conn` lazily through `Database` — that is what makes
  per-thread connections and database swapping work.
- `demo_seed` references properties by **address**, not a guessed id.
