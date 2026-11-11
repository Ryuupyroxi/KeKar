#!/usr/bin/env python3
"""Verify a KeKar USB package: structure, file counts, no host-path leaks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

LEAK_MARKERS = [b"/home/", b"C:\\Users\\", b"/mnt/usb", b"Ryuu"]
TEXT_SUFFIXES = (".py", ".sh", ".bat", ".json", ".txt", ".desktop", ".nsi")


def verify(root: Path, platform: str | None = None) -> list[str]:
    problems: list[str] = []

    if not root.exists():
        return [f"package directory does not exist: {root}"]

    builds = [b for b in ("KeKar_Windows", "KeKar_Linux")
              if (root / b).is_dir()]
    if not builds:
        problems.append("no build folder found (expected KeKar_Windows or KeKar_Linux)")
    if platform == "linux" and "KeKar_Linux" not in builds:
        problems.append("missing KeKar_Linux/")
    if platform == "windows" and "KeKar_Windows" not in builds:
        problems.append("missing KeKar_Windows/")

    for build in builds:
        count = sum(1 for p in (root / build).rglob("*") if p.is_file())
        if count < 100:
            problems.append(f"{build}: only {count} files (copy incomplete?)")
        binary = "KeKar.exe" if build.endswith("Windows") else "KeKar"
        if not (root / build / binary).exists():
            problems.append(f"{build}: missing {binary}")

    for rel in ("KeKarData", "README.txt", "KeKar.sh", "KeKar.bat"):
        if not (root / rel).exists():
            problems.append(f"missing: {rel}")

    for path in root.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            try:
                data = path.read_bytes()
            except OSError:
                continue
            for marker in LEAK_MARKERS:
                if marker in data:
                    problems.append(
                        f"{path.relative_to(root)} contains {marker!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--platform", choices=["linux", "windows"])
    args = parser.parse_args()
    problems = verify(args.root, args.platform)
    if problems:
        print("FAILED:")
        for p in problems:
            print(" -", p)
        return 1
    print(f"OK: {args.root} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
