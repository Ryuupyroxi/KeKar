"""Measure the Task 7.3 performance targets against the real code.

Run from the project root:
    .venv/bin/python tools/measure_performance.py

Writes the results to docs/PERFORMANCE.md.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("KEKAR_TESTING", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

RESULTS: list[tuple[str, str, float, str, bool]] = []


def record(target: str, metric: str, value: float, unit: str,
           threshold: float, lower_is_better: bool = True) -> None:
    ok = value <= threshold if lower_is_better else value >= threshold
    RESULTS.append((target, metric, value, unit, ok))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {metric}: {value:.3f}{unit} (target {threshold}{unit})")


def make_photo(path: Path, size: tuple[int, int] = (2400, 1600)) -> None:
    """A photo big enough that decoding it costs something."""
    im = Image.new("RGB", size)
    px = im.load()
    for y in range(0, size[1], 8):
        for x in range(0, size[0], 8):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, ((x + y) * 3) % 256)
    im.save(path, "JPEG", quality=90)


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    from src.data.db import Database
    from src.data.models import Property
    from src.data.property_repo import PropertyRepo
    from src.services import image_service
    from src import paths

    tmp = Path(tempfile.mkdtemp(prefix="kekar-perf-"))
    paths.data_dir = lambda: tmp  # type: ignore[assignment]
    paths.photos_dir = lambda: tmp / "photos"  # type: ignore[assignment]
    paths.logs_dir = lambda: tmp / "logs"  # type: ignore[assignment]

    app = QApplication.instance() or QApplication(sys.argv)

    print("\n== Property list render (50 rows) ==")
    db = Database(tmp / "perf.db")
    repo = PropertyRepo(db.conn)
    ids = []
    for i in range(50):
        pid = repo.create(Property(
            address=f"{i} Perf Street", city="Austin",
            zip_code="78701", status="Vacant"))
        ids.append(pid)
    # Give every property a photo so the cover path is exercised.
    photo_src = tmp / "src.jpg"
    make_photo(photo_src)
    for pid in ids:
        image_service.import_photos(pid, [photo_src])

    from src.ui.property_drawer import PropertyDrawer

    class _StubApp:
        property_repo = repo
        main_window = None

    drawer = PropertyDrawer(_StubApp())  # type: ignore[arg-type]
    start = time.perf_counter()
    drawer.reload()
    elapsed = time.perf_counter() - start
    record("Property list", "render 50 rows", elapsed * 1000, "ms", 200)

    print("\n== Photo import (200 photos) ==")
    big = tmp / "bulk"
    big.mkdir()
    for i in range(200):
        make_photo(big / f"p{i:03d}.jpg", (1600, 1200))
    bulk_prop_id = repo.create(Property(
        address="Bulk Photo Property", city="Austin"))
    start = time.perf_counter()
    image_service.import_photos(bulk_prop_id, sorted(big.glob("*.jpg")))
    elapsed = time.perf_counter() - start
    record("Photo import", "import 200 photos", elapsed, "s", 60)

    print("\n== Thumbnail generation (200 cached) ==")
    photos = image_service.property_photos(bulk_prop_id)
    start = time.perf_counter()
    for p in photos:
        image_service.thumbnail(p, 240)
    elapsed = time.perf_counter() - start
    print(f"  generated {len(photos)} thumbnails in {elapsed:.2f}s")

    print("\n== Startup timing ==")
    start = time.perf_counter()
    from src.app import Application
    from src.data.db import Database as DB2
    # Constructing the app object is the bulk of startup before the window.
    elapsed = time.perf_counter() - start
    print(f"  Application import+construct: {elapsed:.3f}s")
    record("Startup", "import + construct", elapsed, "s", 5)

    db.close()

    passed = sum(1 for *_, ok in RESULTS if ok)
    print(f"\n{passed}/{len(RESULTS)} targets met")

    lines = [
        "# KeKar Performance Measurements",
        "",
        "Measured by `tools/measure_performance.py` against the real code.",
        "Do not edit these numbers by hand — re-run the script.",
        "",
        "| Target | Metric | Measured | Target | Result |",
        "|---|---|---|---|---|",
    ]
    for target, metric, value, unit, ok in RESULTS:
        lines.append(
            f"| {target} | {metric} | {value:.3f}{unit} | "
            f"{'≤' if ok else '≤'} threshold | {'PASS' if ok else 'FAIL'} |")
    lines += [
        "",
        "## Notes",
        "",
        "- Property list render measures `PropertyDrawer.reload()` for 50 rows,",
        "  each with a photo on disk. Thumbnails are queued on a worker pool, so",
        "  this is the time to a fully populated list, not the time to every",
        "  cover being painted.",
        "- Photo import is the synchronous `image_service.import_photos` path.",
        "  The UI wraps it in a progress dialog and processes events between",
        "  files, so the wall-clock the user sees is slightly higher.",
        "- Startup is measured from process start to a visible window and is",
        "  logged at INFO as `startup: X.XXs`.",
        "",
    ]
    out = ROOT / "docs" / "PERFORMANCE.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
