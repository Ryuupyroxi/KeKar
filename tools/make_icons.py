#!/usr/bin/env python3
"""Extract PNG icons for the icon theme from the master .ico.

Linux launchers look for icons under ~/.local/share/icons/hicolor/<size>/apps/,
so the single .ico has to be expanded into the sizes the theme expects. Run
this whenever src/resources/icons/kekar.ico changes, then commit the PNGs.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "src" / "resources" / "icons"
MASTER = ICON_DIR / "kekar.ico"

# hicolor theme sizes launchers actually look for.
SIZES = (16, 32, 48, 64, 128, 256)


def main() -> int:
    master = Image.open(MASTER).convert("RGBA")
    for size in SIZES:
        # Downscale from the largest embedded frame with a proper filter;
        # nearest-neighbour would leave visible jaggies at 16 px.
        frame = master.resize((size, size), Image.LANCZOS)
        out = ICON_DIR / f"kekar-{size}.png"
        frame.save(out, "PNG")
        print(f"wrote {out.relative_to(ROOT)} ({size}x{size})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
