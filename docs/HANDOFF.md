# Handoff — panels, leases, listing channels

Written 2026-11-14. State of the tree at the end of this working session.
Nothing is committed yet, by request: the features were finished as a set so the
tour could be updated to match, and the commits land afterwards.

## Where it stands

- `pytest -q` → **308 passed**, exit 0.
- Source: 55 modules, 6,772 lines (`find src -name '*.py' | wc -l`,
  `find src -name '*.py' -exec cat {} + | wc -l`).
- Test modules: 36.
- Every UI change below was launched on the real display (`DISPLAY=:0`) and
  screenshotted, not just unit-tested.

## What was built

### 1. Collapsible sidebar and chat panels

- `CollapsibleSplitter` in `src/ui/main_window.py`; panes collapse to zero and
  restore the *remembered* pre-collapse sizes.
- The collapse control is a `QToolButton` pair in
  `menuBar().setCornerWidget(...)`: `sidebar_toggle`, `chat_toggle`. Their
  arrows show which way the panel will move (`◀ Properties` / `▶ Properties`,
  `▼ Chat` / `▲ Chat`).
- The same two actions exist in **View**.
- `sidebar_collapsed` / `chat_collapsed` persist in Settings.
- `tests/test_layout.py` (15 tests).

**The handle is deliberately paint-only.** An earlier attempt made the splitter
handle itself the click target by overriding `mousePressEvent` /
`mouseMoveEvent` / `mouseReleaseEvent`. Qt's splitter owns those events and the
base press synthesises a release, so a click collapsed the pane *and* a
measured 80 px drag returned the panes to their exact original sizes —
drag-to-resize silently died. The handle now only draws a grip, and
`test_handle_leaves_mouse_events_to_qt` guards the regression.

### 2. Leases tab

- New tab on the main window: `src/ui/lease_tab.py`.
- The client's example lease is the **template**. Load it by pasting or with
  "Load example lease…" (`QFileDialog`, `.txt`/`.md`); "Save as template" writes
  it to `settings.lease_template` (encrypted with the rest of Settings).
  "Use built-in template" restores `lease_builder.DEFAULT_TEMPLATE`.
- Markers are `{{address}}`, `{{city}}`, `{{zip}}`, `{{rent}}`, `{{deposit}}`,
  `{{bedrooms}}`, `{{bathrooms}}`, `{{sqft}}`, `{{sqft_clause}}`,
  `{{available_date}}`, `{{pet_policy}}`, `{{status}}`, `{{tenant}}`,
  `{{landlord}}`, `{{date}}`, `{{term}}`.
- Substitution is plain string replacement in `src/services/lease_builder.py` —
  no `eval`, no `exec`. **Unknown markers are left in place** and listed in the
  "KeKar does not fill" note, so a client's own markers are never mangled.
- Generate → **Copy** (`clipboard.copy_text`), **Print…**
  (`QPrintDialog` + `QTextDocument.print(QPrinter)`), **Email…**
  (`QDesktopServices.openUrl("mailto:…")`), **Save lease** (`leases` table).
- Email deliberately holds no SMTP credentials: it opens the user's own mail
  app with subject and body pre-filled. Warns when the body passes
  `MAILTO_SOFT_LIMIT` (1500 chars) because some clients truncate.
- `src/data/lease_repo.py` + a `leases` table. `LeaseRepo` resolves its
  connection lazily through `Database`, so it is worker-thread safe.
- `tests/test_leases.py` (25 tests).

### 3. Zillow and apartments.com listings

- `src/services/listing_channels.py` builds a **per-channel package**: a title
  (with the site's length limit), a body in that site's wording, every field the
  site's form asks for separately, and warnings (title too long, rent or
  square footage missing, site-specific notes).
- `src/ui/listing_dialog.py` gained a **Channel** dropdown: Any site (generic),
  Zillow, apartments.com. Switching re-renders the preview.
- `tests/test_listing_channels.py` (14 tests).

**Direct posting is not offered, and that is a decision, not an omission.**
Neither Zillow nor apartments.com exposes an API for creating a rental listing,
and both sit behind a logged-in session with anti-automation. Copy-and-paste is
what the user asked for as an acceptable option, so that is what was built and
the dialog says so. Facebook Marketplace keeps its opt-in CDP autofill, which
still stops before Publish.

## Bugs found and fixed while building

- `TourOverlay` painted with `theme=None` when a caller constructed it directly
  and skipped `apply_theme` → `AttributeError: 'NoneType' object has no
  attribute 'accent'`. The overlay now reads the app's theme at construction.
- Remembered expanded splitter sizes were stored as the *same list object* that
  was then zeroed, so restoring brought back `[0, …]`. Now copied.
- `LeaseTab` kept a stale `_editing_id` after the portfolio was cleared, so the
  next save ran `UPDATE` on a deleted row and silently saved nothing.
  `reload()` now resets it.
- `leases` list ordering tied on `created_at` (same timestamp) and came back in
  insertion order; now `ORDER BY created_at DESC, id DESC`.
- Five lease header fields in one row squeezed the boxes so typed values read
  as "n Doe" and "mith". Split into two rows.
- `channel_fields` called `compile_channel`, which called `channel_fields` —
  infinite recursion. Restructured so fields are built inside `compile_channel`.

## Schema note

`leases` was added to `src/data/_schema_embedded.py` (the authoritative copy)
and `src/data/schema.sql` was regenerated from it with
`embedded_schema()`. `tests/test_bundle_safety.py::test_on_disk_schema_matches_embedded_copy`
proves the two are byte-identical. The change is additive and
`embedded_schema()` is re-applied idempotently on every connection, so existing
databases gain the table with no migration step. `SCHEMA_VERSION` stayed at 1.

## How to re-check

```bash
cd "/home/Ryuu/Documents/kekar project"
.venv/bin/pytest -q                      # 308 passed
.venv/bin/pytest tests/test_layout.py tests/test_leases.py \
                 tests/test_listing_channels.py -q
```

Real-display checks (X on `:0`):

```bash
DISPLAY=:0 KEKAR_DATA_DIR=/tmp/kekar-check .venv/bin/python - <<'PY'
import sys; sys.path.insert(0, ".")
from src.app import Application
app = Application([]); app.show_main_window()
PY
```

### 4. Supplied icon and logo

- `src/resources/icons/kekar-mark.png` (228x269, alpha) is the mark;
  `tools/build_icon_assets.py` centres it on a 256x256 transparent square and
  writes `kekar.ico`; `tools/make_icons.py` regenerates the hicolor PNGs.
- `src/resources/icons/kekar-logo.png` (1408x768, alpha) is the wordmark.
- `paths.resource_path()` / `icon_path()` / `logo_path()` resolve either
  location, frozen or dev.
- `Application` and `MainWindow` set the window icon; `MainWindow` shows the
  logo in a 44 px left-aligned strip at the top; `AboutDialog` shows it at 96 px.
- `tests/test_branding.py` (11 tests), including a check that the `.ico` really
  carries 7 frames — the first build silently produced a single 16x16 frame.
- `tests/test_branding.py` also asserts the header strip is not taller than
  64 px, after a centred 56 px logo in a full-width band read as dead space.

### 5. Tour brought up to date, and accounts built

- `build_tour_steps` is now 10 steps and describes the real app: the drawer, the
  details form (naming the Zillow/apartments.com preview), photos, Applicants,
  Leases (copy/print/email), the assistant, panels/themes/accounts, the brand,
  and demo mode. Two tests guard it — one fails if a tab has no step, one fails
  if the wording drifts from the feature set.
- Accounts: `src/services/auth.py` (PBKDF2-HMAC-SHA256, 310k iterations, 7-day
  session tokens) and `src/data/user_repo.py` (`users`, `sessions`), plus
  `LoginDialog`, `UsersDialog`, `Application.login/logout/lock/unlock_with_dialog`
  and `MainWindow.set_locked/is_locked`.
- Opt-in: `require_login` defaults to false, Accounts refuses to enable it with
  zero accounts, and the last account cannot be removed.

**Bug found by the cross-file suite:** Qt hides a central widget when it is
swapped out and does *not* unhide it when it is swapped back. `set_locked(False)`
therefore left the whole portfolio invisible — no exception, no warning, just a
blank window for every test that ran afterwards. `set_locked` now calls
`show()` on the restored widget, and
`test_unlocking_restores_a_visible_portfolio` guards it.

## Still outstanding

- Nothing is committed. `git status` shows 22 modified and 12 new files.
- The branding pass was **not** re-checked on a real display after the header
  and About-dialog fixes: the screenshot command was blocked by an approval
  timeout and was deliberately not retried. The icon and logo are verified by
  `test_branding.py` (files exist, `.ico` frames, pixmap non-null) and by the
  earlier screenshot of the un-fixed layout; the *fixed* layout still needs eyes.
- `docs/TEST-MATRIX.md` scenarios 19-25 (leases, channels, panels, themes,
  branding, accounts) need a human on real hardware.
- The guided tour now has 10 steps; step 6 is the Leases tab. It was walked on
  a real display and screenshotted at the Leases and Panels/accounts steps; the
  tab switches and the captions match the shipped feature set.

## Packaging pass, 2026-11-15

The logo and icon were in the source but not in the packages. Closed that:

- `packaging/linux/kekar.desktop` now says `Icon=kekar` (was the
  `utilities-terminal` placeholder), and `packaging/linux/kekar.png` (the
  square 256 px master) sits beside it for the AppImage builder.
- `packaging/windows/KeKar_Installer.nsi` carries `MUI_ICON` / `MUI_UNICON`
  (via `${__FILEDIR__}`) and both shortcuts point at the package-root
  `kekar.ico`. `tools/make_usb_package.py` stages that `.ico` into
  `KeKar_Windows/`, so the installer is independent of PyInstaller's internal
  layout. CI stages it too, because the Windows job calls the same tool.
- New tests: Windows `.ico` staging, AppImage `.desktop` icon, square AppImage
  PNG, and drift guards between the packaging copies and the generated art
  (`tests/test_usb_packaging.py`).
- **Bug found by the real-display check:** the About dialog was a fixed
  460x340, which clipped the last paragraph by 14 px. `AboutDialog` now sizes
  itself from `layout.totalSizeHint()` (460x354 here) so a larger system font
  grows the window instead of cutting text. Guarded by
  `test_about_dialog_body_is_not_clipped`.

Re-check:

```bash
cd "/home/Ryuu/Documents/kekar project"
.venv/bin/python -m pytest -q          # 356 passed
bash build.sh                          # rebuild + package + verify
```

Real-display evidence (X on `:0`, 1280x800): the built `dist/KeKar/KeKar` shows
the wordmark in the header strip and the icon in the title bar; Help → About
shows the logo with the body fully inside the dialog.

Still open: the NSIS installer itself is not built by CI (it never was) — it is
a manual `makensis packaging/windows/KeKar_Installer.nsi` step on Windows. The
icon is staged for it, but no CI job compiles or attaches the installer.
