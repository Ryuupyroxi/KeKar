"""Self-update support from GitHub releases.

The updater never touches KeKarData. It downloads a release zip, verifies the
GitHub-provided SHA-256, stages the new application folder beside the current
one, then launches a short-lived script that waits for KeKar to exit before
swapping the folder and relaunching the app.
"""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import httpx

from .. import features
from .._version import APP_VERSION
from ..paths import data_dir

REPO = "Ryuupyroxi/KeKar"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"


def asset_name(lite: bool, system: str | None = None) -> str:
    system = (system or platform.system()).lower()
    product = "KeKarLite" if lite else "KeKar"
    suffix = "Windows" if system.startswith("win") else "Linux"
    return f"{product}_{suffix}.zip"


def parse_version(tag: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", tag or "")[:3]
    return tuple(int(n) for n in numbers) or (0,)


def is_newer(tag: str) -> bool:
    return parse_version(tag) > parse_version(APP_VERSION)


def fetch_latest(lite: bool | None = None,
                 system: str | None = None) -> dict:
    """Return the latest release version and the matching asset metadata."""
    lite = features.is_lite() if lite is None else lite
    wanted = asset_name(lite, system)
    response = httpx.get(
        RELEASE_API,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "KeKar-Updater"},
        timeout=15)
    response.raise_for_status()
    release = response.json()
    assets = release.get("assets", [])
    match = next((a for a in assets if a.get("name") == wanted), None)
    if match is None:
        raise RuntimeError(f"no {wanted} asset in the latest release")
    digest = (match.get("digest") or "").split(":", 1)[-1]
    return {"version": release.get("tag_name", "").lstrip("v").split("-")[0],
            "tag": release.get("tag_name", ""),
            "asset": {**match, "sha256": digest}}


def verify_sha256(path: Path, expected: str) -> bool:
    if not expected:
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower() == expected.lower()


def download_asset(asset: dict, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", asset["browser_download_url"], timeout=60,
                      follow_redirects=True) as response:
        response.raise_for_status()
        with open(destination, "wb") as handle:
            for chunk in response.iter_bytes(1024 * 1024):
                if chunk:
                    handle.write(chunk)
    if not verify_sha256(destination, asset.get("sha256", "")):
        destination.unlink(missing_ok=True)
        raise RuntimeError("the downloaded update failed its checksum")
    return destination


def _executable_name(lite: bool | None = None) -> str:
    lite = features.is_lite() if lite is None else lite
    base = "KeKarLite" if lite else "KeKar"
    return base + (".exe" if os.name == "nt" else "")


def find_installed_app_dir(root: Path, executable: str) -> Path | None:
    """Find the application folder beside KeKarData, including USB layouts."""
    base = executable.replace(".exe", "")
    suffix = "Windows" if executable.endswith(".exe") else "Linux"
    folder = f"{base}_{suffix}"
    candidates = [root / base, root / folder, root / folder / folder,
                  root / root.name / base]
    for candidate in candidates:
        if (candidate / executable).exists():
            return candidate
    return None


def find_downloaded_app_dir(unpacked: Path, executable: str) -> Path | None:
    for path in unpacked.rglob(executable):
        if path.is_file():
            return path.parent
    return None


def write_apply_script(updates_dir: Path, pid: int, source: Path,
                       target: Path, launcher: Path) -> Path:
    """Write the detached script that performs the swap after KeKar exits."""
    updates_dir.mkdir(parents=True, exist_ok=True)
    script = updates_dir / "apply_update.py"
    text = "\n".join([
        '"""Applied automatically after KeKar closes."""',
        "import os, shutil, subprocess, time",
        "from pathlib import Path",
        f"PID = {pid!r}",
        f"SOURCE = {str(source)!r}",
        f"TARGET = {str(target)!r}",
        f"LAUNCHER = {str(launcher)!r}",
        'STATUS = Path(__file__).resolve().parent / "update-status.txt"',
        "",
        "def alive():",
        '    if os.name == "nt":',
        "        import ctypes",
        "        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, PID)",
        "        if not handle:",
        "            return False",
        "        ctypes.windll.kernel32.CloseHandle(handle)",
        "        return True",
        "    try:",
        "        os.kill(PID, 0)",
        "        return True",
        "    except OSError:",
        "        return False",
        "",
        "def report(message):",
        '    STATUS.write_text(message, encoding="utf-8")',
        "",
        "try:",
        '    report("waiting")',
        "    for _ in range(60):",
        "        if not alive():",
        "            break",
        "        time.sleep(0.5)",
        '    report("swapping")',
        "    for attempt in range(30):",
        "        try:",
        "            if TARGET.exists():",
        "                shutil.rmtree(TARGET)",
        "            shutil.copytree(SOURCE, TARGET)",
        "            break",
        "        except OSError:",
        "            time.sleep(1)",
        "    else:",
        '        raise RuntimeError("could not replace the application folder")',
        '    report("done")',
        "    if LAUNCHER and Path(LAUNCHER).exists():",
        "        subprocess.Popen([str(LAUNCHER)], cwd=str(Path(LAUNCHER).parent),",
        "                         stdout=subprocess.DEVNULL,",
        "                         stderr=subprocess.DEVNULL)",
        "except Exception as exc:",
        '    report("failed: " + str(exc))',
        "",
    ])
    script.write_text(text, encoding="utf-8")
    return script


def stage_update(info: dict, *, lite: bool | None = None) -> Path:
    """Download, verify, unpack and stage an update. Returns the script path."""
    lite = features.is_lite() if lite is None else lite
    updates = data_dir() / "updates"
    archive = download_asset(info["asset"], updates / info["asset"]["name"])
    unpacked = updates / "unpacked"
    if unpacked.exists():
        shutil.rmtree(unpacked)
    unpacked.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(unpacked)
    executable = _executable_name(lite)
    source = find_downloaded_app_dir(unpacked, executable)
    root = data_dir().parent
    target = find_installed_app_dir(root, executable)
    if source is None or target is None:
        raise RuntimeError(
            "could not locate the application folders in the update")
    product = "KeKarLite" if lite else "KeKar"
    launcher_name = f"{product}.sh" if os.name != "nt" else f"{product}.bat"
    launcher = data_dir().parent / launcher_name
    return write_apply_script(updates, os.getpid(), source, target, launcher)


def launch_apply_script(script: Path) -> None:
    """Start the detached swapper; the running app should then quit."""
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, str(script)], **kwargs)
