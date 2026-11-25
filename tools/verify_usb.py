#!/usr/bin/env python3
"""Verify a KeKar USB package: structure, file counts, no host-path leaks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

LEAK_MARKERS = [b"/home/", b"C:\\Users\\", b"/mnt/usb", b"Ryuu"]
TEXT_SUFFIXES = (".py", ".sh", ".bat", ".json", ".txt", ".desktop", ".nsi")


def verify(root: Path, platform: str | None = None,
           variant: str = "full") -> list[str]:
    problems: list[str] = []

    if not root.exists():
        return [f"package directory does not exist: {root}"]

    name = "KeKarLite" if variant == "lite" else "KeKar"
    builds = [b for b in (f"{name}_Windows", f"{name}_Linux")
              if (root / b).is_dir()]
    if not builds:
        problems.append(f"no build folder found (expected {name}_Windows or {name}_Linux)")
    if platform == "linux" and f"{name}_Linux" not in builds:
        problems.append(f"missing {name}_Linux/")
    if platform == "windows" and f"{name}_Windows" not in builds:
        problems.append(f"missing {name}_Windows/")

    for build in builds:
        count = sum(1 for p in (root / build).rglob("*") if p.is_file())
        if count < 100:
            problems.append(f"{build}: only {count} files (copy incomplete?)")
        binary = f"{name}.exe" if build.endswith("Windows") else name
        if not (root / build / binary).exists():
            problems.append(f"{build}: missing {binary}")

    required = ["KeKarData", "README.txt", "INSTRUCTIONS.txt"]
    if platform in (None, "windows"):
        required.append(f"{name}.bat")
    if platform in (None, "linux"):
        required += [f"{name}.sh", "install_linux.py"]
    for rel in required:
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
    parser.add_argument("--variant", choices=["full", "lite"], default="full")
    args = parser.parse_args()
    problems = verify(args.root, args.platform, args.variant)
    if problems:
        print("FAILED:")
        for p in problems:
            print(" -", p)
        return 1
    print(f"OK: {args.root} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
