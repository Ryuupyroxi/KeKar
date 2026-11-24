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
    # Hidden .thumb_* files are caches, not photos. Treating them as photos
    # made "Set as cover" swap a thumbnail and hid the real image.
    return sorted(p for p in d.iterdir()
                  if not p.name.startswith(".")
                  and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))


def delete_property_photos(property_id: int) -> None:
    shutil.rmtree(_property_dir(property_id), ignore_errors=True)


def delete_photo(property_id: int, path: Path) -> bool:
    """Remove a single photo and its cached thumbnails."""
    path = Path(path)
    if not path.exists():
        return False
    path.unlink()
    for thumb in path.parent.glob(f".thumb_*_{path.name}"):
        thumb.unlink(missing_ok=True)
    return True


def set_cover(property_id: int, path: Path) -> bool:
    """Make the given photo the first (cover) image by swapping positions.

    Photos are ordered by filename, so the cover is whichever sorts first.
    Swapping the two filenames moves the chosen photo to the front without
    renaming every file.
    """
    photos = property_photos(property_id)
    if len(photos) < 2:
        return False
    first, target = photos[0], Path(path)
    if target == first:
        return False
    tmp = first.parent / f".swap_{first.name}"
    first.rename(tmp)
    target.rename(first.parent / first.name)
    tmp.rename(target.parent / target.name)
    for thumb in first.parent.glob(".thumb_*"):
        thumb.unlink(missing_ok=True)
    return True


def cover_photo(property_id: int) -> Path | None:
    """The property's cover photo, or None when it has no photos."""
    photos = property_photos(property_id)
    return photos[0] if photos else None



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
