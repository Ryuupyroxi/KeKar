"""Photo import, EXIF orientation, resize/compress, and thumbnails."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageOps

from ..paths import photos_dir

MAX_DIMENSION = 1920
JPEG_QUALITY = 85


def _property_dir(property_id: int) -> Path:
    return photos_dir() / str(property_id)


def import_photos(property_id: int, paths: list[Path]) -> list[Path]:
    target_dir = _property_dir(property_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []
    for i, src in enumerate(paths, start=1):
        src = Path(src)
        if not src.exists():
            continue
        target = target_dir / f"{i:02d}_{src.stem}.jpg"
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            im.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
            im.save(target, "JPEG", quality=JPEG_QUALITY, optimize=True)
        imported.append(target)
    return imported


def property_photos(property_id: int) -> list[Path]:
    d = _property_dir(property_id)
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir()
                  if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))


def delete_property_photos(property_id: int) -> None:
    shutil.rmtree(_property_dir(property_id), ignore_errors=True)


def thumbnail(path: Path, size: int = 240) -> Path:
    path = Path(path)
    thumb_path = path.parent / f".thumb_{size}_{path.name}"
    if thumb_path.exists() and thumb_path.stat().st_mtime >= path.stat().st_mtime:
        return thumb_path
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((size, size), Image.LANCZOS)
        im.save(thumb_path, "JPEG", quality=80, optimize=True)
    return thumb_path
