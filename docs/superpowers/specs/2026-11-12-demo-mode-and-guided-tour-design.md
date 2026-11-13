# Demo Mode and Guided Tour — Design

Date: 2026-11-12
Status: Approved design, pending spec review
Feature: Tutorial / demo mode introducing KeKar's features and options

## Goal

A new user opens KeKar, connects an API key, and then faces an empty app with no
explanation of what any of it does. This feature gives them a populated app to
explore and a guided walkthrough of it, without ever exposing their real records
to the demo.

Two mechanisms, one feature:

- **Demo mode** — KeKar runs against a separate demo database.
- **Guided tour** — a spotlight overlay walks the user through the UI, running
  inside demo mode.

## Decisions

| Question | Decision |
|---|---|
| What is the tutorial? | A guided, spotlight-overlay tour. |
| When does it run? | Automatically once on first run (after the setup wizard), and re-openable from the Help menu. |
| How does demo data work? | A **separate database file**. Everything else — settings, memory, photos, logs — is shared with the real install. |
| Real data safety | Real data directory untouched by construction: a different database file is opened. Demo mode never persists across a restart. |

### Consequences of sharing everything but the database

- Settings are shared, so an API-key change made while in demo mode also applies
  to the real install. Accepted: demo mode is a tour, and the Settings dialog is
  hidden while demo mode is active to prevent accidental changes.
- `KeKarData/memory/MEMORY.md` is shared. The assistant's saved notes are the
  one piece of real state that could be written during a demo. Accepted for this
  scope, and called out here so it is a conscious choice rather than an
  oversight.
- Photos and applicant documents are shared directories. Demo seed data creates
  no files, so nothing is written there.
- Chat history lives in the database, so it is isolated with the demo database.

## Architecture

Five pieces, in dependency order:

```
1. paths.demo_database_path()            <- where the demo DB lives
2. Application.enter_demo_mode()         <- swap the database, rebuild the layer
   Application.exit_demo_mode()
3. demo_seed.seed_if_empty(db)           <- sample data, idempotent
4. ui/tour.py                            <- overlay + steps + navigation
5. main_window: Help menu + demo banner  <- entry points
```

### 1. Demo database path

`src/paths.py` gains one function:

```python
def demo_database_path() -> Path:
    return data_dir() / "demo" / "database.db"
```

`Database(path=...)` already accepts an explicit path, so no change is needed
there. `open_with_recovery(path)` already accepts one too.

### 2. Entering and leaving demo mode

`Application` gains:

- `self.demo_mode: bool`
- `enter_demo_mode()` — close the current database, open the demo database (via
  `open_with_recovery(demo_database_path())`), seed it if empty, rebuild the
  repositories (they are constructed from `self.db`), reload the main window,
  show the banner.
- `exit_demo_mode()` — the reverse: close, reopen the real database, rebuild,
  reload, hide the banner.
- `_rebuild_data_layer()` — the shared body of both: close the old `Database`,
  open the new one, construct `PropertyRepo` / `ApplicantRepo` / `ChatRepo`,
  and re-point `self.ctx` at them. `self.memory`, `self.client` and
  `self.agent_runner` keep working because they read `self.settings` and
  `self.ctx`.

Repositories already resolve `conn` lazily through the `Database`, so a rebuilt
`Database` is enough — no view needs to be reconstructed.

Demo mode is session-only. Nothing writes a "demo" flag to disk, so closing the
app mid-tour returns the user to their real data on the next launch.

### 3. Demo seed data

`src/data/demo_seed.py`:

```python
def seed_if_empty(db: Database) -> bool:
    """Populate an empty demo database. Returns True if it seeded."""
```

Idempotent: if the `properties` table has any rows, do nothing. Guarded so a
second entry into demo mode never duplicates data.

Seeded content — four properties with mixed statuses, rents and amenities, and
four applicants spread across the pipeline:

| Property | Town | Rent | Beds | Baths | Status | Amenities |
|---|---|---|---|---|---|---|
| 123 Main Street | Springfield | 1200 | 2 | 1.0 | Vacant | W/D, AC |
| 456 Oak Avenue | Springfield | 950 | 1 | 1.0 | Rented | Parking |
| 789 Elm Lane | Shelbyville | 1450 | 3 | 2.0 | Vacant | Yard, Dishwasher |
| 321 Pine Court | Capital City | 2100 | 4 | 2.5 | Rented | all five |

Applicants: John Doe (Inquiry Received, property 1), Jane Smith (Background
Check, property 2), Bob Johnson (Approved, property 3), Alice Brown (Rejected,
property 4).

No photos or documents are created — the seed touches only the database.

### 4. The tour

`src/ui/tour.py` contains:

- `TourStep` — `target` (a QWidget or None), `title`, `body`, `placement`.
- `TourOverlay(QWidget)` — a child of the main window covering its whole client
  area, painted with four dim rectangles around the target's rect, leaving a
  hole. Four rectangles rather than composition modes: no transparency
  attribute is needed and it cannot fail on a platform that dislikes
  `CompositionMode_Clear`.
- A caption panel beside the hole with title, body, `Back` / `Next` / `Skip`,
  and a "Step N of M" indicator.
- Keyboard: `Esc` exits, `Left`/`Right` navigate.

The overlay captures clicks, making the tour a guided walkthrough. It is a
child widget of the main window, so it closes with it and cannot be orphaned.

The tour follows the existing `worker.py` ownership rule: it never holds a
thread, and it is dismissed on `MainWindow.closeEvent` if it is somehow still
open.

#### Steps

| # | Title | Target | Body |
|---|---|---|---|
| 1 | Welcome | none (centred) | What KeKar is and what the tour covers. |
| 2 | Your properties | PropertyDrawer | The list, the search box, and adding a property. |
| 3 | The details form | PropertyForm | Address, rent, and the fields a listing needs. |
| 4 | Photos | PhotoPanel | Adding photos and choosing a cover. |
| 5 | Applicants | CrmTab | The pipeline stages; the tour switches to this tab. |
| 6 | The assistant | ChatPane | Asking questions and giving instructions. |
| 7 | Settings | Menu bar | Providers, models, backups, and auto-fill. |
| 8 | You're in demo mode | none | What demo mode is, and how to leave it. |

Step 5 calls `MainWindow.tabs.setCurrentIndex(1)` on entry and restores the
previous index on exit, so the user sees the Applicants tab without having to
find it.

### 5. Entry points

`MainWindow._build_menu()` gains, under Help:

- **Guided tour** — if not already in demo mode, offers to enter it (a short
  confirmation dialog explaining that sample data will be used); then starts the
  tour.
- **Exit demo mode** — visible only while `app.demo_mode` is true; leaves demo
  mode and ends the tour.

`File → Settings` is hidden while demo mode is active.

A `DemoBanner` (reusing the existing `OfflineBanner` styling from
`src/ui/widgets.py`) sits below the menu bar while demo mode is active, reading:
"Demo mode — sample data. Your own records are not shown. Exit demo mode", with
an Exit button.

### 6. First run

After the setup wizard completes, `Application` checks
`settings.tour_completed`. If false, it shows a short dialog:

> **Take a quick tour?**
> The tour uses sample data, so you can see everything working. Your own
> records are never touched.
> `Start the tour` / `Skip`

Either choice sets `tour_completed = True` and saves, so the question is never
asked twice. Choosing **Start the tour** enters demo mode and runs the tour.

## Testing

The critical property is isolation: real data must be unchanged by demo mode.

- `paths.demo_database_path()` points inside the data directory and is not the
  real database path.
- `enter_demo_mode()` swaps the database; `exit_demo_mode()` restores it.
- **Isolation**: create a property in the real database, enter demo mode,
  assert it is absent, exit demo mode, assert it is back.
- `seed_if_empty()` is idempotent — seeding twice does not duplicate.
- Seeding an empty database produces the expected property and applicant rows.
- The tour's step targets resolve to real widgets in a constructed
  `MainWindow`.
- The overlay paints without raising, and the caption panel never lands outside
  the window for any step or window size.
- `tour_completed` persists and suppresses the first-run prompt.
- Entering demo mode when the demo database does not exist creates it.
- The Settings action is disabled during demo mode.

## Documentation

Updated to match: `README.md` (feature list and status), `docs/WIRING.md`
(demo mode and tour sections), `docs/TEST-MATRIX.md` (new coverage),
`docs/SPEC-COVERAGE.md` (the feature's spec rows).

## Order of work

1. `paths.demo_database_path()`, `enter/exit_demo_mode()`, `_rebuild_data_layer()`
   and their tests.
2. `demo_seed.py` and its tests.
3. `ui/tour.py` — overlay, steps, navigation — and its tests.
4. Menu entries, demo banner, first-run prompt, Settings guard.
5. Docs and commit.

## Out of scope

- Letting the user click into the app mid-tour.
- A separate practice mode.
- Isolating the assistant's memory file during demo mode.
- Shipping the demo data as a separate downloadable pack.
