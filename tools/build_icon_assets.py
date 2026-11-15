#!/usr/bin/env python3
"""Build the application icon from the supplied mark.

The mark (`kekar-mark.png`, from the Kekar artwork) is not square, and window
and launcher icons are. Squaring it by stretching would distort the house, so
it is centred on a transparent square canvas instead. Run this whenever the
mark changes, then run `tools/make_icons.py` for the hicolor PNGs.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "src" / "resources" / "icons"
MARK = ICON_DIR / "kekar-mark.png"
MASTER = ICON_DIR / "kekar-master.png"
ICO = ICON_DIR / "kekar.ico"

#: Frame sizes a Windows .ico carries. 24 and 96 are the ones modern Windows
#: actually pulls for the taskbar and the start menu.
SIZES = (16, 24, 32, 48, 64, 128, 256)
CANVAS = 256


def square_mark() -> Image.Image:
    """Centre the mark on a transparent square, keeping its proportions."""
    mark = Image.open(MARK).convert("RGBA")
    scale = CANVAS / max(mark.size)
    size = (max(1, round(mark.width * scale)), max(1, round(mark.height * scale)))
    mark = mark.resize(size, Image.LANCZOS)
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(mark, ((CANVAS - mark.width) // 2,
                        (CANVAS - mark.height) // 2), mark)
    return canvas


def main() -> int:
    master = square_mark()
    master.save(MASTER, "PNG")
    # `sizes=` makes PIL write one frame per size from the master. Passing
    # `append_images` as well silently produces a single 16x16 frame.
    master.save(ICO, format="ICO",
                sizes=[(size, size) for size in SIZES])
    print(f"wrote {MASTER.relative_to(ROOT)} ({CANVAS}x{CANVAS})")
    print(f"wrote {ICO.relative_to(ROOT)} ({len(SIZES)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
