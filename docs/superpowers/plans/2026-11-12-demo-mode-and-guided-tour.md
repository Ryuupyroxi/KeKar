# Demo Mode and Guided Tour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a new KeKar user a populated demo database to explore and a guided spotlight tour of the UI, without ever touching their real records.

**Architecture:** Demo mode swaps the open SQLite database for a separate demo file and rebuilds the repository layer; everything else (settings, memory, photos, logs) stays shared. The tour is a transparent child widget of the main window that dims everything except the highlighted widget, with a caption panel and Back/Next/Skip navigation.

**Tech Stack:** Python 3.12+, PyQt6, SQLite (WAL), pytest, PyInstaller.

## Global Constraints

- No new runtime dependencies. Use only what `pyproject.toml` already pins.
- The API key must never appear in a log line, dialog, crash report, or database.
- Demo data must never be written to the real database file.
- Demo mode is session-only: nothing on disk records that it was used.
- Every task ends with a green suite and a commit.
- Project root: `/home/Ryuu/Documents/kekar project`. Run tests with `.venv/bin/python -m pytest` from there.
- Existing patterns to follow: repositories resolve `conn` lazily through `Database`; worker threads go through `src/ui/worker.py`; data paths come only from `src/paths.py`.

---

## Key Decisions

| Decision | Choice | Reason |
|---|---|---|
| What is isolated in demo mode | The database file only | Master's instruction. Simplest change: `Database(path=...)`. |
| Settings during demo mode | Shared, but the Settings action is disabled | Shared file means a key change would affect the real install; disabling the dialog removes the risk. |
| Assistant memory during demo mode | Shared | Accepted consciously; flagged in the spec. |
| Demo mode persistence | Session-only | Nothing on disk says "demo", so a crash mid-tour returns the user to real data. |
| Tour modality | Modal — the overlay captures clicks | A guided walkthrough; simplest and cannot lead to accidental edits. |
| Spotlight painting | `setClipRegion` with the inverse of the hole | No composition modes, no transparency attribute beyond `WA_TranslucentBackground`, robust across platforms. |
| Windows build | GitHub Actions on `windows-latest` | PyInstaller cannot cross-compile; a CI runner is reproducible and needs no local Windows box. |

### Spec deviations

None. The spec was approved with the database-only variation already applied.

---

## File Structure

**Create:**
- `src/ui/tour.py` — `TourStep`, `TourOverlay`, and the step list.
- `src/data/demo_seed.py` — `seed_if_empty(db)` and the sample rows.
- `tests/test_demo_mode.py` — demo mode and isolation tests.
- `tests/test_tour.py` — overlay and step tests.
- `tools/make_windows_package.py` — Windows artifact builder.
- `.github/workflows/build.yml` — CI build and release.

**Modify:**
- `src/paths.py` — add `demo_database_path()`.
- `src/app.py` — `demo_mode`, `_open_database()`, `_rebuild_repos()`, `enter_demo_mode()`, `exit_demo_mode()`, `maybe_offer_tour()`.
- `src/ui/main_window.py` — demo banner, Help menu entries, Settings guard, `set_demo_mode()`.
- `src/ui/widgets.py` — add `DemoBanner`.
- `src/config/settings.py` — add `tour_completed: bool = False`.
- `src/main.py` — call `maybe_offer_tour()` after the wizard.
- `README.md`, `docs/WIRING.md`, `docs/TEST-MATRIX.md`, `docs/SPEC-COVERAGE.md` — document the feature.

---

## Task 1: Demo database path and mode switching

**Files:**
- Modify: `src/paths.py` (append one function)
- Modify: `src/app.py` (`__init__`, new methods)
- Modify: `src/ui/main_window.py` (`reload_all` is already sufficient; no change needed here)
- Test: `tests/test_demo_mode.py` (create)

**Interfaces:**
- Consumes: `paths.data_dir()`, `data.backup.open_with_recovery(path)`, `Database`
- Produces:
  - `paths.demo_database_path() -> Path`
  - `Application.demo_mode: bool`
  - `Application.enter_demo_mode() -> None`
  - `Application.exit_demo_mode() -> None`
  - `Application._open_database(path: Path | None) -> None`
  - `Application._rebuild_repos() -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_demo_mode.py`:

```python
from pathlib import Path

from src.data.db import Database
from src.data.property_repo import PropertyRepo
from src.data.models import Property
from src.paths import data_dir, demo_database_path


def test_demo_path_is_separate():
    assert demo_database_path() != data_dir() / "database.db"
    assert demo_database_path().name == "database.db"
    assert demo_database_path().parent.name == "demo"


def test_enter_and_exit_demo_mode(kekar_app):
    real_repo = PropertyRepo(kekar_app.db)
    real_id = real_repo.create(Property(address="1 Real Street"))

    kekar_app.enter_demo_mode()
    try:
        assert kekar_app.demo_mode is True
        demo_repo = PropertyRepo(kekar_app.db)
        assert demo_repo.list() == [], "demo database should start empty"
        assert demo_repo.get(real_id) is None, "real property leaked into demo"
    finally:
        kekar_app.exit_demo_mode()

    assert kekar_app.demo_mode is False
    assert PropertyRepo(kekar_app.db).get(real_id) is not None, (
        "real property vanished after leaving demo mode")


def test_demo_database_file_is_created(kekar_app):
    kekar_app.enter_demo_mode()
    try:
        assert demo_database_path().exists()
    finally:
        kekar_app.exit_demo_mode()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_demo_mode.py -v`
Expected: FAIL with `ImportError: cannot import name 'demo_database_path'` and `AttributeError: 'Application' object has no attribute 'enter_demo_mode'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/paths.py`:

```python
def demo_database_path() -> Path:
    """The demo database, inside the real data directory but separate from
    the user's own database so demo mode can never write to it."""
    return data_dir() / "demo" / "database.db"
```

In `src/app.py`, add the import and the methods:

```python
from pathlib import Path

from .data.backup import open_with_recovery, prune_backups
from .paths import demo_database_path
```

Replace the repository construction in `Application.__init__`:

```python
        self.demo_mode = False
        self.db = None
        self.memory = MemoryStore()
        self.client = LLMClient(self.settings)
        self._open_database(None)
```

Add the new methods after `__init__`:

```python
    def _open_database(self, path: Path | None) -> None:
        """Open a database and point the repositories at it.

        ``path=None`` means the user's real database; the demo path comes from
        ``paths.demo_database_path()`` so it can never drift.
        """
        if self.db is not None:
            try:
                self.db.close()
            except Exception:
                pass
        self.db = open_with_recovery(path)
        self._rebuild_repos()

    def _rebuild_repos(self) -> None:
        self.property_repo = PropertyRepo(self.db)
        self.applicant_repo = ApplicantRepo(self.db)
        self.chat_repo = ChatRepo(self.db)
        self.ctx = ToolContext(db=self.db, property_repo=self.property_repo,
                               applicant_repo=self.applicant_repo,
                               memory=self.memory, settings=self.settings,
                               on_change=self.data_changed.emit)
        self.agent_runner = AgentRunner(self.client, self.settings, self.ctx)

    def enter_demo_mode(self) -> None:
        """Switch to the demo database. The real one is closed untouched."""
        if self.demo_mode:
            return
        self._open_database(demo_database_path())
        self.demo_mode = True
        self.main_window.reload_all()
        self.main_window.set_demo_mode(True)

    def exit_demo_mode(self) -> None:
        """Return to the user's real database."""
        if not self.demo_mode:
            return
        self._open_database(None)
        self.demo_mode = False
        self.main_window.reload_all()
        self.main_window.set_demo_mode(False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_demo_mode.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Add the main window hook the app calls**

The tests above call `main_window.set_demo_mode(True)`, which does not exist
yet. Add it to `src/ui/main_window.py` now so Task 1 is self-contained — a
minimal version that Task 4 extends:

```python
    def set_demo_mode(self, active: bool) -> None:
        """Reflect demo mode in the UI. Task 4 adds the banner and menu."""
        self.demo_mode = active
```

Add `self.demo_mode = False` in `MainWindow.__init__`.

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: all pass (217 tests)

- [ ] **Step 7: Commit**

```bash
git add src/paths.py src/app.py src/ui/main_window.py tests/test_demo_mode.py
git commit -m "KeKar: demo mode switches to a separate database"
```

---

## Task 2: Demo seed data

**Files:**
- Create: `src/data/demo_seed.py`
- Test: `tests/test_demo_mode.py` (append)

**Interfaces:**
- Consumes: `Database`, `PropertyRepo(db)`, `ApplicantRepo(db)`
- Produces: `demo_seed.seed_if_empty(db: Database) -> bool` — True when it seeded.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_demo_mode.py`:

```python
from src.data import demo_seed


def test_seed_is_idempotent(kekar_app):
    kekar_app.enter_demo_mode()
    try:
        assert demo_seed.seed_if_empty(kekar_app.db) is True
        first = PropertyRepo(kekar_app.db).list()
        assert len(first) == 4

        assert demo_seed.seed_if_empty(kekar_app.db) is False
        assert len(PropertyRepo(kekar_app.db).list()) == 4
    finally:
        kekar_app.exit_demo_mode()


def test_seed_content(kekar_app):
    kekar_app.enter_demo_mode()
    try:
        demo_seed.seed_if_empty(kekar_app.db)
        props = {p.address: p for p in PropertyRepo(kekar_app.db).list()}
        assert set(props) == {
            "123 Main Street", "456 Oak Avenue",
            "789 Elm Lane", "321 Pine Court"}
        assert props["123 Main Street"].rent_price == 1200.0
        assert props["456 Oak Avenue"].status == "Rented"
        assert props["789 Elm Lane"].amenity_yard is True

        from src.data.applicant_repo import ApplicantRepo
        stages = {a.screening_stage
                  for a in ApplicantRepo(kekar_app.db).list()}
        assert stages == {"Inquiry Received", "Background Check",
                          "Approved", "Rejected"}
    finally:
        kekar_app.exit_demo_mode()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_demo_mode.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.demo_seed'`

- [ ] **Step 3: Write minimal implementation**

Create `src/data/demo_seed.py`:

```python
"""Sample data for demo mode.

Seeded into the demo database only. Never touches the user's real database.
"""
from __future__ import annotations

from .applicant_repo import ApplicantRepo
from .models import Applicant, Property
from .property_repo import PropertyRepo

PROPERTIES = [
    Property(address="123 Main Street", city="Springfield", zip_code="62701",
             rent_price=1200.0, deposit_amount=1200.0, bedrooms=2,
             bathrooms=1.0, sqft=900, status="Vacant",
             amenity_wd=True, amenity_ac=True),
    Property(address="456 Oak Avenue", city="Springfield", zip_code="62704",
             rent_price=950.0, deposit_amount=950.0, bedrooms=1,
             bathrooms=1.0, sqft=650, status="Rented",
             amenity_parking=True),
    Property(address="789 Elm Lane", city="Shelbyville", zip_code="62565",
             rent_price=1450.0, deposit_amount=1450.0, bedrooms=3,
             bathrooms=2.0, sqft=1400, status="Vacant",
             amenity_yard=True, amenity_dishwasher=True),
    Property(address="321 Pine Court", city="Capital City", zip_code="62707",
             rent_price=2100.0, deposit_amount=2100.0, bedrooms=4,
             bathrooms=2.5, sqft=2000, status="Rented",
             amenity_wd=True, amenity_ac=True, amenity_yard=True,
             amenity_dishwasher=True, amenity_parking=True),
]

APPLICANTS = [
    ("John Doe", "123 Main Street", "555-0101", "Inquiry Received"),
    ("Jane Smith", "456 Oak Avenue", "555-0102", "Background Check"),
    ("Bob Johnson", "789 Elm Lane", "555-0103", "Approved"),
    ("Alice Brown", "321 Pine Court", "555-0104", "Rejected"),
]


def seed_if_empty(db) -> bool:
    """Populate an empty demo database. Returns True if it seeded.

    Idempotent: an existing property means the demo is already set up.
    """
    properties = PropertyRepo(db)
    applicants = ApplicantRepo(db)
    if properties.list():
        return False

    ids = {prop.address: properties.create(prop) for prop in PROPERTIES}
    for name, address, contact, stage in APPLICANTS:
        applicants.create(Applicant(
            applicant_name=name, property_id=ids[address],
            contact_info=contact, screening_stage=stage))
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_demo_mode.py -v`
Expected: PASS

- [ ] **Step 5: Wire the seed into demo mode**

In `src/app.py`, import and call it:

```python
from .data.demo_seed import seed_if_empty
```

```python
    def enter_demo_mode(self) -> None:
        if self.demo_mode:
            return
        self._open_database(demo_database_path())
        seed_if_empty(self.db)
        self.demo_mode = True
        self.main_window.reload_all()
        self.main_window.set_demo_mode(True)
```

- [ ] **Step 6: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/data/demo_seed.py src/app.py tests/test_demo_mode.py
git commit -m "KeKar: seed the demo database with sample properties and applicants"
```

---

## Task 3: The tour overlay

**Files:**
- Create: `src/ui/tour.py`
- Test: `tests/test_tour.py` (create)

**Interfaces:**
- Consumes: `MainWindow` (the widget to cover), `font()` from `src/ui/theme.py`
- Produces:
  - `TourStep(target: QWidget | None, title: str, body: str, on_enter: Callable | None = None)`
  - `TourOverlay(window: QWidget, steps: list[TourStep])`
  - `TourOverlay.start() -> None`
  - `TourOverlay.finish() -> None`
  - `build_tour_steps(window) -> list[TourStep]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tour.py`:

```python
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

from src.ui.tour import TourOverlay, TourStep, build_tour_steps


def test_tour_steps_target_real_widgets(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    assert len(steps) == 8
    for step in steps:
        assert isinstance(step, TourStep)
        if step.target is not None:
            assert step.target is not None
            assert step.target.parent() is not None, (
                f"{step.title} target is not in the widget tree")


def test_overlay_paints_without_raising(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    overlay = TourOverlay(window, steps)
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()
    overlay.grab()  # forces a paint; raises if painting fails
    overlay.finish()


def test_overlay_navigation(kekar_app):
    window = kekar_app.main_window
    overlay = TourOverlay(window, build_tour_steps(window))
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()

    assert overlay.current_index == 0
    overlay.next()
    assert overlay.current_index == 1
    overlay.back()
    assert overlay.current_index == 0
    overlay.back()
    assert overlay.current_index == 0, "cannot go before the first step"

    overlay.goto_last()
    overlay.next()
    assert overlay.current_index == len(build_tour_steps(window)) - 1, (
        "cannot go past the last step")
    overlay.finish()


def test_overlay_switches_to_applicants_tab(kekar_app):
    window = kekar_app.main_window
    steps = build_tour_steps(window)
    overlay = TourOverlay(window, steps)
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()

    overlay.goto_step(5)  # the Applicants step
    kekar_app.processEvents()
    assert window.tabs.currentIndex() == 1

    overlay.finish()
    assert window.tabs.currentIndex() == 0, "tour must restore the tab"


def test_esc_closes_the_tour(kekar_app):
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent

    window = kekar_app.main_window
    overlay = TourOverlay(window, build_tour_steps(window))
    overlay.resize(window.size())
    overlay.show()
    kekar_app.processEvents()
    assert overlay.isVisible()

    overlay.keyPressEvent(QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not overlay.isVisible()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_tour.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ui.tour'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ui/tour.py`:

```python
"""Guided tour: a spotlight overlay that walks the user through the UI.

The overlay is a transparent child of the main window. It paints a dim layer
everywhere except a hole around the current target, and hosts a caption panel
with Back / Next / Skip.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QEvent, Qt, QRect
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPen, QRegion, QShortcut
from PyQt6.QtWidgets import (QDialogButtonBox, QFrame, QLabel, QPushButton,
                             QVBoxLayout, QWidget)

from .theme import font

DIM = QColor(20, 16, 12, 170)
RING = QColor("#ffb300")


@dataclass
class TourStep:
    """One tour step. ``target=None`` means a centred, untargeted card."""

    target: object | None
    title: str
    body: str
    on_enter: Callable[[], None] | None = None


class TourOverlay(QWidget):
    def __init__(self, window: QWidget, steps: list[TourStep]):
        super().__init__(window)
        self._window = window
        self._steps = steps
        self.current_index = 0
        self.restore_tab: int | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.caption = QFrame(self)
        self.caption.setObjectName("tourCaption")
        self.caption.setStyleSheet(
            "background:#fffdf7; border:1px solid #d8cfc0; border-radius:10px;")
        cap_layout = QVBoxLayout(self.caption)
        self.title_label = QLabel()
        self.title_label.setFont(font(12, bold=True))
        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setFont(font(10))
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color:#7a7268;")
        cap_layout.addWidget(self.title_label)
        cap_layout.addWidget(self.body_label)
        cap_layout.addWidget(self.progress_label)

        buttons = QDialogButtonBox()
        self.back_button = buttons.addButton(
            "Back", QDialogButtonBox.ButtonRole.ActionRole)
        self.next_button = buttons.addButton(
            "Next", QDialogButtonBox.ButtonRole.AcceptRole)
        self.skip_button = buttons.addButton(
            "Skip tour", QDialogButtonBox.ButtonRole.RejectRole)
        self.back_button.clicked.connect(self.back)
        self.next_button.clicked.connect(self.next)
        self.skip_button.clicked.connect(self.finish)
        cap_layout.addWidget(buttons)

        QShortcut(QKeySequence("Escape"), self).activated.connect(self.finish)

    # -- geometry ----------------------------------------------------------

    def _hole_rect(self) -> QRect | None:
        target = self._steps[self.current_index].target
        if target is None:
            return None
        rect = target.rect().translated(target.mapTo(self._window, target.pos()))
        return rect.intersected(self._window.rect())

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        self._place_caption()

    def _place_caption(self) -> None:
        hole = self._hole_rect()
        width = 360
        height = self.caption.sizeHint().height() or 150
        if hole is None:
            x = (self.width() - width) // 2
            y = (self.height() - height) // 2
        else:
            x = min(max(8, hole.center().x() - width // 2),
                    max(8, self.width() - width - 8))
            below = hole.bottom() + 12
            if below + height > self.height() - 8:
                below = max(8, hole.top() - height - 12)
            y = below
        self.caption.setGeometry(x, y, width, height)

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        hole = self._hole_rect()
        if hole is None:
            painter.fillRect(self.rect(), DIM)
        else:
            painter.setClipRegion(QRegion(self.rect()) - QRegion(hole))
            painter.fillRect(self.rect(), DIM)
            painter.setClipRegion(QRegion(self.rect()))
            painter.setPen(QPen(RING, 3))
            painter.drawRoundedRect(hole.adjusted(-4, -4, 4, 4), 10, 10)
        painter.end()

    # -- navigation --------------------------------------------------------

    def start(self) -> None:
        self.current_index = 0
        self.restore_tab = None
        self.show()
        self._apply_step()

    def finish(self) -> None:
        if self.restore_tab is not None:
            self._window.tabs.setCurrentIndex(self.restore_tab)
            self.restore_tab = None
        self.hide()
        self.deleteLater()

    def next(self) -> None:
        if self.current_index < len(self._steps) - 1:
            self.current_index += 1
            self._apply_step()

    def back(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self._apply_step()

    def goto_step(self, index: int) -> None:
        if 0 <= index < len(self._steps):
            self.current_index = index
            self._apply_step()

    def goto_last(self) -> None:
        self.goto_step(len(self._steps) - 1)

    def _apply_step(self) -> None:
        step = self._steps[self.current_index]
        self.title_label.setText(step.title)
        self.body_label.setText(step.body)
        self.progress_label.setText(
            f"Step {self.current_index + 1} of {len(self._steps)}")
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setText(
            "Finish" if self.current_index == len(self._steps) - 1 else "Next")
        if step.on_enter is not None:
            step.on_enter()
        self.caption.adjustSize()
        self._place_caption()
        self.update()

    def keyPressEvent(self, event: QEvent) -> None:
        if event.key() == Qt.Key.Key_Right:
            self.next()
        elif event.key() == Qt.Key.Key_Left:
            self.back()
        else:
            super().keyPressEvent(event)


def build_tour_steps(window) -> list[TourStep]:
    """The tour content, bound to a concrete MainWindow."""
    return [
        TourStep(
            None, "Welcome to KeKar",
            "KeKar keeps your properties, listings, photos and applicant notes "
            "in one place, stored only on this device. This short tour shows "
            "you around. Your own data is not touched."),
        TourStep(
            window.drawer, "Your properties",
            "This is your property list. The search box filters as you type. "
            "Use '+ Add New Property' to add your first listing."),
        TourStep(
            window.property_form, "The details form",
            "Address, rent, deposit and the rest. Fields with a red outline "
            "are needed before a listing can be published."),
        TourStep(
            window.photo_panel, "Photos",
            "Add photos for a property and choose one as the cover. The cover "
            "is what appears in the property list."),
        TourStep(
            window.crm_tab, "Applicants",
            "Track every applicant through the pipeline, from first enquiry to "
            "approved or rejected.",
            on_enter=lambda: _show_applicants(window)),
        TourStep(
            window.chat_pane, "The assistant",
            "Ask questions in plain language, or give an instruction like "
            "'draft a message to John'. It can read and update your records."),
        TourStep(
            window.menuBar(), "Settings and providers",
            "Choose your AI provider and models, manage backups, and control "
            "marketplace auto-fill."),
        TourStep(
            None, "You're in demo mode",
            "Everything you see is sample data. Your own records are safe and "
            "unchanged. Use 'Exit demo mode' in the Help menu when you're "
            "ready to work with your real data."),
    ]


def _show_applicants(window) -> None:
    """Switch to the Applicants tab for the duration of its step."""
    overlay = window.findChild(TourOverlay)
    if overlay is not None and overlay.restore_tab is None:
        overlay.restore_tab = window.tabs.currentIndex()
    window.tabs.setCurrentIndex(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_tour.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/ui/tour.py tests/test_tour.py
git commit -m "KeKar: guided tour overlay with spotlight and navigation"
```

---

## Task 4: Entry points — menu, banner, first-run prompt

**Files:**
- Modify: `src/ui/widgets.py` (add `DemoBanner`)
- Modify: `src/ui/main_window.py` (banner, menu, Settings guard, `set_demo_mode`)
- Modify: `src/config/settings.py` (`tour_completed`)
- Modify: `src/app.py` (`maybe_offer_tour`)
- Modify: `src/main.py` (call it after the wizard)
- Test: `tests/test_demo_mode.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 1-3
- Produces:
  - `widgets.DemoBanner` with signal `exited`
  - `MainWindow.set_demo_mode(active: bool)`
  - `Settings.tour_completed: bool`
  - `Application.maybe_offer_tour() -> None`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_demo_mode.py`:

```python
from PyQt6.QtWidgets import QMessageBox

from src.ui.widgets import DemoBanner


def test_tour_completed_defaults_false(kekar_app):
    assert kekar_app.settings.tour_completed is False


def test_banner_is_hidden_until_demo_mode(kekar_app):
    banner = kekar_app.main_window.demo_banner
    assert isinstance(banner, DemoBanner)
    assert not banner.isVisible()

    kekar_app.enter_demo_mode()
    kekar_app.main_window.set_demo_mode(True)
    assert kekar_app.main_window.demo_mode is True
    kekar_app.exit_demo_mode()
    assert kekar_app.main_window.demo_mode is False


def test_settings_disabled_in_demo_mode(kekar_app):
    window = kekar_app.main_window
    assert window.settings_action.isEnabled() is True
    kekar_app.enter_demo_mode()
    assert window.settings_action.isEnabled() is False
    kekar_app.exit_demo_mode()
    assert window.settings_action.isEnabled() is True


def test_exit_demo_action_visible_only_in_demo(kekar_app):
    window = kekar_app.main_window
    assert window.exit_demo_action.isVisible() is False
    kekar_app.enter_demo_mode()
    assert window.exit_demo_action.isVisible() is True
    kekar_app.exit_demo_mode()
    assert window.exit_demo_action.isVisible() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_demo_mode.py -v`
Expected: FAIL with `ImportError: cannot import name 'DemoBanner'`

- [ ] **Step 3: Write minimal implementation**

Add to `src/ui/widgets.py` (extend the imports first):

```python
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                             QWidget)
```

```python
class DemoBanner(QWidget):
    """Shown while demo mode is active, so it is never a surprise."""

    exited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel(
            "Demo mode — sample data. Your own records are not shown.")
        self.label.setStyleSheet(
            "background:#e3f2fd; color:#0d47a1; padding:8px;")
        exit_button = QPushButton("Exit demo mode")
        exit_button.clicked.connect(self.exited)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(exit_button)
```

In `src/config/settings.py`, add the field:

```python
    tour_completed: bool = False
```

In `src/ui/main_window.py`:
- Add `self.demo_mode = False` in `__init__`.
- Build the banner and insert it below the menu bar.
- Add the menu entries and the Settings guard.

```python
        # in __init__, after the menu is built
        self.demo_banner = DemoBanner(self)
        self.demo_banner.exited.connect(self._exit_demo_mode)
        self.demo_banner.hide()
        self._insert_banner()
```

```python
    def _insert_banner(self) -> None:
        """Put the demo banner directly below the menu bar."""
        container = self.menuBar().parentWidget().layout()
        if container is not None and self.demo_banner not in container:
            container.insertWidget(1, self.demo_banner)
```

In `_build_menu`, extend Help:

```python
        help_menu = menubar.addMenu("&Help")
        tour_action = help_menu.addAction("Guided tour...")
        tour_action.triggered.connect(self._start_tour)
        self.exit_demo_action = help_menu.addAction("Exit demo mode")
        self.exit_demo_action.triggered.connect(self._exit_demo_mode)
        self.exit_demo_action.setVisible(False)
        help_menu.addSeparator()
        about_action = help_menu.addAction("About...")
        about_action.triggered.connect(lambda: AboutDialog(self).exec())
```

Add the handlers:

```python
    def set_demo_mode(self, active: bool) -> None:
        self.demo_mode = active
        self.demo_banner.setVisible(active)
        self.settings_action.setEnabled(not active)
        self.exit_demo_action.setVisible(active)

    def _start_tour(self) -> None:
        if not self.app.demo_mode:
            answer = QMessageBox.question(
                self, "KeKar",
                "The tour uses sample data, so you can see everything working. "
                "Your own records are never touched.\n\n"
                "Start the tour?")
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.app.enter_demo_mode()
        from .tour import TourOverlay, build_tour_steps
        overlay = TourOverlay(self, build_tour_steps(self))
        overlay.resize(self.size())
        overlay.start()
        self._tour = overlay

    def _exit_demo_mode(self) -> None:
        if getattr(self, "_tour", None) is not None:
            self._tour.finish()
            self._tour = None
        self.app.exit_demo_mode()
```

In `src/app.py`, add:

```python
    def maybe_offer_tour(self) -> None:
        """Offer the tour once, after first-run setup."""
        if self.settings.tour_completed:
            return
        from PyQt6.QtWidgets import QMessageBox
        from .ui.tour import TourOverlay, build_tour_steps

        answer = QMessageBox.question(
            self.main_window, "KeKar",
            "Take a quick tour?\n\n"
            "The tour uses sample data, so you can see everything working. "
            "Your own records are never touched.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self.settings.tour_completed = True
        try:
            self.settings.save()
        except Exception:
            pass
        if answer == QMessageBox.StandardButton.Yes:
            self.enter_demo_mode()
            overlay = TourOverlay(self.main_window,
                                  build_tour_steps(self.main_window))
            overlay.resize(self.main_window.size())
            overlay.start()
            self.main_window._tour = overlay
```

In `src/main.py`, after the wizard block and before `show_main_window()`:

```python
    app.maybe_offer_tour()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_demo_mode.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/ui/widgets.py src/ui/main_window.py src/config/settings.py src/app.py src/main.py tests/test_demo_mode.py
git commit -m "KeKar: demo banner, Help menu tour entry, and first-run prompt"
```

---

## Task 5: Documentation

**Files:**
- Modify: `README.md`, `docs/WIRING.md`, `docs/TEST-MATRIX.md`, `docs/SPEC-COVERAGE.md`

- [ ] **Step 1: Re-measure before editing any number**

Run: `.venv/bin/python -m pytest` and `ls src/**/*.py | wc -l`
Record the real test count and module count. Do not copy them from this plan.

- [ ] **Step 2: Add the WIRING sections**

Add to `docs/WIRING.md`:

```markdown
## Demo mode

`paths.demo_database_path()` points at `<data_dir>/demo/database.db`. Everything
else — settings, memory, photos, logs — is shared with the real install.

`Application.enter_demo_mode()` closes the real database, opens the demo one,
seeds it if empty, rebuilds the repositories, and tells the main window to
reload. `exit_demo_mode()` reverses it. Repositories resolve their connection
lazily through the `Database`, so rebuilding is enough; no view is reconstructed.

Demo mode is session-only: nothing on disk records it, so a crash mid-tour
returns the user to real data. The Settings action is disabled while demo mode
is active, because settings are shared.

## Guided tour

`src/ui/tour.py` holds `TourStep`, `TourOverlay` and `build_tour_steps(window)`.
The overlay is a transparent child of the main window; `paintEvent` fills the
window with a dim colour clipped to everything *except* a hole around the
current target, so no composition modes are needed.

The overlay is modal — it captures clicks, so the tour is a guided walkthrough
rather than free play. `Esc` exits, arrow keys navigate, and step 5 switches to
the Applicants tab and restores the previous tab on exit.
```

- [ ] **Step 3: Update README, TEST-MATRIX and SPEC-COVERAGE**

Add the feature to the README feature list and status; add the new test files
to `TEST-MATRIX`; add a spec-coverage row for demo mode and the tour.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/
git commit -m "KeKar: document demo mode and the guided tour"
```

---

## Task 6: Windows release and GitHub publishing

**Files:**
- Create: `tools/make_windows_package.py`
- Create: `.github/workflows/build.yml`
- Modify: `README.md` (download link)

**Interfaces:**
- Consumes: the PyInstaller spec `KeKar.spec`, `tools/make_icons.py`
- Produces: a zipped `KeKar_Windows/` artifact containing `KeKar.exe`,
  `KeKarData/`, and `KeKar.bat`

PyInstaller cannot cross-compile, so the build runs on a GitHub Actions
`windows-latest` runner. The workflow publishes the zip as a release asset when
a release is published, and also uploads it as a build artifact for testing.

- [ ] **Step 1: Write the packaging script**

Create `tools/make_windows_package.py`:

```python
"""Build the Windows portable package from a PyInstaller output directory.

Run this on Windows after `python -m PyInstaller KeKar.spec --noconfirm`.
Produces out/KeKar_Windows/ with the executable, a KeKarData skeleton, and a
double-clickable launcher.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "KeKar"
OUT = ROOT / "out" / "KeKar_Windows"


def main() -> int:
    if not DIST.exists():
        sys.exit(f"missing PyInstaller output: {DIST}")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # The executable and its bundled support files.
    for item in DIST.iterdir():
        target = OUT / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    # Portable data skeleton, so the first run has somewhere to write.
    (OUT / "KeKarData" / "config").mkdir(parents=True, exist_ok=True)
    (OUT / "KeKarData" / "logs").mkdir(parents=True, exist_ok=True)
    (OUT / "KeKarData" / "photos").mkdir(parents=True, exist_ok=True)
    (OUT / "KeKarData" / "applicants").mkdir(parents=True, exist_ok=True)

    launcher = OUT / "KeKar.bat"
    launcher.write_text(
        "@echo off\r\n"
        "start \"\" \"%~dp0KeKar.exe\"\r\n", encoding="ascii")

    readme = OUT / "START-HERE.txt"
    readme.write_text(
        "KeKar Property Manager\n"
        "======================\n\n"
        "Double-click KeKar.bat to start.\n\n"
        "Your data is stored in the KeKarData folder next to the program.\n"
        "Copy the whole KeKar_Windows folder to any PC or USB drive.\n",
        encoding="utf-8")

    print(f"Built: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/build.yml`:

```yaml
name: build

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Build with PyInstaller
        run: python -m PyInstaller KeKar.spec --noconfirm

      - name: Assemble the portable package
        run: python tools/make_windows_package.py

      - name: Zip the package
        shell: pwsh
        run: Compress-Archive -Path out/KeKar_Windows -DestinationPath out/KeKar_Windows.zip

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: KeKar-Windows
          path: out/KeKar_Windows.zip

      - name: Attach to the release
        if: github.event_name == 'release'
        uses: softprops/action-gh-release@v2
        with:
          files: out/KeKar_Windows.zip
```

- [ ] **Step 3: Verify the script locally**

Run: `python tools/make_windows_package.py` from the project root.
Expected: `Built: .../out/KeKar_Windows`, and the directory contains `KeKar`,
`KeKar.bat`, `START-HERE.txt` and `KeKarData/`.

- [ ] **Step 4: Commit and push**

```bash
git add tools/make_windows_package.py .github/workflows/build.yml
git commit -m "KeKar: Windows release build and GitHub Actions workflow"
git push
```

- [ ] **Step 5: Publish a release**

```bash
gh release create v0.1.0 --title "KeKar v0.1.0" --notes "First Windows release"
```

Then confirm the workflow ran and the zip is attached:

```bash
gh run list --workflow=build.yml
gh release view v0.1.0 --json assets
```

Expected: one completed run and `KeKar_Windows.zip` listed under assets.

- [ ] **Step 6: Verify the download**

```bash
gh release view v0.1.0 --json assets --jq '.assets[].url'
```

Expected: a URL the client can open and download.

---

## Distribution & Portability

- **Build environment per platform.** PyInstaller cannot cross-compile. Linux
  builds happen on this machine; Windows builds happen on a GitHub Actions
  `windows-latest` runner.
- **Artifact layout.** `KeKar_Windows/` contains `KeKar.exe` (plus PyInstaller
  support files), `KeKar.bat` (double-click launcher), `START-HERE.txt`, and an
  empty `KeKarData/` skeleton.
- **Portable data location.** `src/paths.py` resolves `KEKAR_DATA_DIR`, then the
  folder beside the executable, then an OS fallback. On Windows the portable
  folder is beside `KeKar.exe`, so the whole directory can be copied to a USB
  drive or another PC.
- **Launcher strategy.** `KeKar.bat` is the double-click entry point. Linux
  uses the existing `tools/install_linux.py` desktop entry.
- **Unsigned-executable friction.** The Windows build is not code-signed, so
  SmartScreen will warn on first run. `START-HERE.txt` must tell the user to
  click "More info" then "Run anyway", and the release notes should say the
  same. Budget for a code-signing certificate if the client finds this
  unacceptable.

---

## Traceability Matrix

| Spec section | Task |
|---|---|
| Decisions (database-only isolation) | Task 1 |
| Consequences of sharing (Settings disabled) | Task 4 |
| Demo database path | Task 1 |
| Entering and leaving demo mode | Task 1 |
| Demo seed data | Task 2 |
| The tour (overlay, caption, navigation, steps) | Task 3 |
| Entry points (menu, banner, first-run) | Task 4 |
| Testing (isolation, idempotency, targets, persistence) | Tasks 1-4 |
| Documentation | Task 5 |
| Windows release (added by the user after spec approval) | Task 6 |

**Deliberate deviations:** none.
