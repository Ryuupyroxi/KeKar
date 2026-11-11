"""Find and launch Chrome/Edge with a dedicated KeKar profile and CDP enabled."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

from ...paths import browser_profile_dir

DEBUG_PORT = 9222


def _windows_candidates(kind: str) -> list[Path]:
    pf = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    pf86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    if kind == "chrome":
        return [pf / "Google/Chrome/Application/chrome.exe",
                pf86 / "Google/Chrome/Application/chrome.exe",
                local / "Google/Chrome/Application/chrome.exe"]
    if kind == "edge":
        return [pf86 / "Microsoft/Edge/Application/msedge.exe",
                pf / "Microsoft/Edge/Application/msedge.exe"]
    return []


def _linux_candidates(kind: str) -> list[Path]:
    names = {"chrome": ["google-chrome", "google-chrome-stable",
                        "chromium", "chromium-browser"],
             "edge": ["microsoft-edge", "microsoft-edge-stable"]}.get(kind, [])
    found = []
    for name in names:
        path = shutil.which(name)
        if path:
            found.append(Path(path))
    return found


def _candidate_paths(kind: str) -> list[Path]:
    if os.name == "nt":
        return _windows_candidates(kind)
    return _linux_candidates(kind)


def find_browser(kind: str = "auto") -> Path | None:
    kinds = ["chrome", "edge"] if kind == "auto" else [kind]
    for k in kinds:
        for path in _candidate_paths(k):
            if path and path.exists():
                return path
    return None


def is_debug_port_open(port: int = DEBUG_PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def launch_browser(kind: str = "auto", profile_dir: Path | None = None,
                   port: int = DEBUG_PORT) -> subprocess.Popen:
    exe = find_browser(kind)
    if exe is None:
        raise FileNotFoundError(
            "No supported browser found. Please install Google Chrome or "
            "Microsoft Edge.")
    profile = profile_dir or browser_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    args = [
        str(exe),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "about:blank",
    ]
    return subprocess.Popen(args, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
