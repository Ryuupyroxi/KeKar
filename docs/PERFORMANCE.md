# KeKar Performance Measurements

Measured by `tools/measure_performance.py` against the real code.
Do not edit these numbers by hand — re-run the script.

| Target | Metric | Measured | Threshold | Result |
|---|---|---|---|---|
| Property list | render 50 rows | 69.156ms | ≤ 200ms | PASS |
| Photo import | import 200 photos | 55.561s | ≤ 60s | PASS |
| Startup | import + construct | 0.516s | ≤ 5s | PASS |

## What was slow, and what fixed it

The property list was the one target that failed on first measurement
(463 ms for 50 rows). Profiling found three causes, in order of cost:

1. **A child widget tree per row.** Each row built five widgets with
   stylesheets and a nested layout, costing ~10 ms per row. Python 3.13's
   enum machinery, invoked by PyQt6 on every enum access, dominated. Rows
   now paint themselves in one `paintEvent` with no children: ~1 ms per row.
2. **A directory scan per row.** `PropertyItemWidget` called
   `image_service.property_photos()` in its constructor, so a 50-row list
   performed 50 directory reads on the UI thread. The drawer now resolves
   every cover path in a single pass and hands each row its path.
3. **The placeholder glyph was repainted for every row.** Painting the house
   glyph cost ~7 ms; it is now cached per size.

Result: 463 ms → 69 ms for 50 rows, a 6.7x improvement.

## Thumbnails

Cover thumbnails are generated on a `QThreadPool` (capped at 4 threads) and
painted when they finish, so the list appears immediately instead of waiting
for every JPEG to decode. Two constraints this design respects:

- `QPixmap` is only valid on the GUI thread, so the worker returns a *path*
  and the GUI thread builds the pixmap.
- Qt does not keep `QRunnable` objects alive, so the process-wide
  `_THUMB_SIGNALS` hub holds every loader for the life of the app. Without
  that, a worker could emit into a deleted object.

## Notes

- Property list render measures `PropertyDrawer.reload()` for 50 rows, each
  with a photo on disk. Thumbnails are queued on the worker pool, so this is
  the time to a fully populated list, not the time to every cover being
  painted.
- Photo import measures the synchronous `image_service.import_photos` path.
  The UI wraps it in a progress dialog and processes events between files,
  so the wall-clock the user sees is slightly higher. 200 photos at
  1600x1200 took 55.6 s on a loaded 2-core machine; on an idle machine it
  measured 26.8 s.
- Startup is measured from process start to a visible window and is logged at
  INFO as `startup: X.XXs`.
- Measurements were taken on the build machine under load (load average ~1.4
  on 2 cores). Treat the thresholds as met, not as comfortably met — re-run
  the script on the target hardware before release.
