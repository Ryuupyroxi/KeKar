#!/usr/bin/env python3
"""Install a one-click KeKar launcher on this Linux machine.

Writes a real .desktop entry plus icon-theme PNGs, so KeKar appears in the
application menu and can sit on the Desktop as a double-click icon.

The .desktop entry records an absolute path to the binary. If the binary
lives on a USB drive whose mount point changes between sessions, re-run this
script after plugging it in — or pass --binary again with the new path.

Usage:
    tools/install_linux.py                      # install from dist/KeKar/KeKar
    tools/install_linux.py --binary /path/KeKar --desktop
    tools/install_linux.py --uninstall
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "kekar"
APP_NAME = "KeKar Property Manager"
APP_COMMENT = "Manage rental properties offline"
ICON_SIZES = (16, 32, 48, 64, 128, 256)

ROOT = Path(__file__).resolve().parent.parent

# Where the binary might live, in priority order. Covers a source checkout
# (dist/KeKar/KeKar) and a USB package (KeKar_Linux/KeKar, or the nested
# layout produced by an older packaging run).
BINARY_CANDIDATES = (
    ROOT / "dist" / "KeKar" / "KeKar",
    ROOT / "KeKar_Linux" / "KeKar",
    ROOT / "KeKar_Linux" / "KeKar_Linux" / "KeKar",
    ROOT / "dist" / "KeKar" / "KeKar.exe",
)


def find_binary(explicit: Path | None = None) -> Path | None:
    """Locate the KeKar executable, preferring an explicit path."""
    if explicit is not None:
        resolved = explicit.expanduser().resolve()
        return resolved if resolved.exists() else None
    for candidate in BINARY_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def find_icon_dir(explicit: Path | None = None) -> Path | None:
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.append(ROOT / "src" / "resources" / "icons")
    candidates.append(ROOT / "resources" / "icons")
    # A frozen build ships the icons under _internal/resources/icons.
    for build_dir in (ROOT / "dist" / "KeKar",
                      ROOT / "KeKar_Linux",
                      ROOT / "KeKar_Linux" / "KeKar_Linux"):
        candidates.append(build_dir / "_internal" / "resources" / "icons")
    for package in ROOT.glob("out/*"):
        candidates.append(package / "_internal" / "resources" / "icons")
        candidates.append(package / "KeKar_Linux" / "_internal"
                          / "resources" / "icons")
    for candidate in candidates:
        if (candidate / "kekar-256.png").exists():
            return candidate
    return None


def desktop_exec(path: Path) -> str:
    """Format a path for the Exec key.

    The Desktop Entry Specification has its own quoting rules — it is not a
    shell. Arguments are separated by spaces and quoted with double quotes;
    inside them, " \\ $ and ` must be backslash-escaped. Using shlex.quote
    here produces single quotes, which desktop-file-validate rejects.
    """
    text = str(path)
    if not any(c in text for c in ' \t\n"\\$`'):
        return text
    escaped = (text.replace("\\", "\\\\")
                   .replace('"', '\\"')
                   .replace("$", "\\$")
                   .replace("`", "\\`"))
    return f'"{escaped}"'


def desktop_entry(binary: Path, icon_name: str = APP_ID) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Version=1.0\n"
        f"Name={APP_NAME}\n"
        "GenericName=Property Manager\n"
        f"Comment={APP_COMMENT}\n"
        f"Exec={desktop_exec(binary.resolve())}\n"
        f"Icon={icon_name}\n"
        "Terminal=false\n"
        "Categories=Office;\n"
        "Keywords=property;rental;landlord;housing;\n"
        "StartupNotify=true\n"
    )


def install(binary: Path, icon_dir: Path | None, desktop: bool,
            locations: list[Path], home: Path | None = None) -> list[str]:
    """Install icons and the .desktop entry. Returns the paths written.

    `home` is injectable so the test suite never touches the real one.
    """
    written: list[str] = []
    home = Path.home() if home is None else home

    if icon_dir is not None:
        for size in ICON_SIZES:
            source = icon_dir / f"kekar-{size}.png"
            target = (home / ".local" / "share" / "icons" / "hicolor"
                      / f"{size}x{size}" / "apps" / f"{APP_ID}.png")
            if not source.exists():
                print(f"  ! missing icon {source.name}, skipped")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            written.append(str(target))

    entry = desktop_entry(binary)
    for directory in locations:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{APP_ID}.desktop"
        target.write_text(entry, encoding="utf-8")
        # Desktop launchers are only offered as "Run" when executable, and
        # GTK additionally refuses to launch a .desktop from the Desktop
        # unless it carries the trusted metadata flag.
        if directory.name == "Desktop":
            target.chmod(0o755)
            mark_trusted(target)
        written.append(str(target))

    return written


def mark_trusted(desktop_path: Path) -> None:
    """Flag a Desktop .desktop file as trusted so GTK will run it.

    Silently skipped where gio is unavailable or the filesystem does not
    support extended attributes.
    """
    if not shutil.which("gio"):
        return
    try:
        subprocess.run(
            ["gio", "set", str(desktop_path), "metadata::trusted", "true"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def refresh_caches() -> None:
    """Tell the desktop and icon caches a new app/icon exists."""
    for command, args in (
        ("update-desktop-database",
         [str(Path.home() / ".local" / "share" / "applications")]),
        ("gtk-update-icon-cache",
         ["-f", "-t", str(Path.home() / ".local" / "share" / "icons"
                          / "hicolor")]),
    ):
        if shutil.which(command):
            try:
                subprocess.run([command, *args], check=False,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except OSError:
                pass


def uninstall(locations: list[Path], home: Path | None = None) -> list[str]:
    removed: list[str] = []
    home = Path.home() if home is None else home
    for directory in locations:
        target = directory / f"{APP_ID}.desktop"
        if target.exists():
            target.unlink()
            removed.append(str(target))
    icon_root = home / ".local" / "share" / "icons" / "hicolor"
    if icon_root.exists():
        for size in ICON_SIZES:
            target = icon_root / f"{size}x{size}" / "apps" / f"{APP_ID}.png"
            if target.exists():
                target.unlink()
                removed.append(str(target))
    refresh_caches()
    return removed


def validate(desktop_path: Path) -> list[str]:
    """Run desktop-file-validate when available; return any complaints."""
    tool = shutil.which("desktop-file-validate")
    if not tool:
        return []
    proc = subprocess.run([tool, str(desktop_path)],
                          capture_output=True, text=True)
    lines = (proc.stdout + proc.stderr).splitlines()
    # desktop-file-validate repeats some errors on both streams.
    return list(dict.fromkeys(line for line in lines if line.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=None,
                        help="path to the KeKar executable (default: "
                             "auto-detect in dist/ or a USB package)")
    parser.add_argument("--icons", type=Path, default=None,
                        help="directory holding kekar-<size>.png")
    parser.add_argument("--desktop", action="store_true",
                        help="also place an icon on the Desktop")
    parser.add_argument("--uninstall", action="store_true",
                        help="remove the launcher and icons")
    args = parser.parse_args()

    home = Path.home()
    locations = [home / ".local" / "share" / "applications"]
    if args.desktop:
        locations.append(home / "Desktop")

    if args.uninstall:
        removed = uninstall(locations)
        if not removed:
            print("Nothing to remove — KeKar was not installed.")
            return 0
        print("Removed:")
        for path in removed:
            print("  -", path)
        return 0

    binary = find_binary(args.binary)
    if binary is None:
        sys.exit("no KeKar executable found.\n"
                 "Build first (bash build.sh) or pass --binary PATH.")

    icon_dir = find_icon_dir(args.icons)
    if icon_dir is None:
        print("No icon set found; installing the launcher without icons.")
    else:
        print(f"Icons: {icon_dir}")

    written = install(binary, icon_dir, args.desktop, locations)
    refresh_caches()

    print(f"KeKar launcher -> {binary}")
    for path in written:
        print("  wrote", path)

    complaints = validate(locations[0] / f"{APP_ID}.desktop")
    if complaints:
        print("\ndesktop-file-validate:")
        for line in complaints:
            print("  ", line)
    else:
        print("\ndesktop-file-validate: clean")

    print("\nSingle-click is ready:")
    print("  - Application menu: search for 'KeKar'")
    if args.desktop:
        print("  - Desktop: double-click the KeKar icon")
    print("Log out and back in if the menu entry does not appear at once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
