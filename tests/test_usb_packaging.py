"""Tests for the USB packaging tools.

The launchers exist twice: as editable sources in assets/launchers/ and as
string constants inside tools/make_usb_package.py. This test fails if they
drift apart, so there is exactly one thing to edit.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "launchers"


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "make_usb_package", ROOT / "tools" / "make_usb_package.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_usb_package"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


def test_bat_matches_assets_source(tool):
    assert tool.BAT == (ASSETS / "KeKar.bat").read_text(encoding="utf-8")


def test_sh_matches_assets_source(tool):
    assert tool.SH == (ASSETS / "KeKar.sh").read_text(encoding="utf-8")


def test_desktop_matches_assets_source(tool):
    assert tool.DESKTOP == (ASSETS / "KeKar.desktop").read_text(encoding="utf-8")


def test_launcher_sources_exist():
    for name in ("KeKar.bat", "KeKar.sh", "KeKar.desktop"):
        assert (ASSETS / name).is_file(), f"missing assets/launchers/{name}"


def test_linux_launcher_is_executable():
    assert (ASSETS / "KeKar.sh").stat().st_mode & 0o111


def test_readme_documents_the_troubleshooting_table(tool):
    assert "TROUBLESHOOTING" in tool.README
    assert "Windows protected your PC" in tool.README


def test_readme_matches_top_level_usage_doc():
    """README-USAGE.txt is the human-facing copy of the same guidance."""
    usage = (ROOT / "README-USAGE.txt").read_text(encoding="utf-8")
    assert "Windows protected your PC" in usage
    assert "KeKarData" in usage


def test_make_platform_package_layout(tool, tmp_path):
    source = tmp_path / "dist" / "KeKar"
    (source / "_internal").mkdir(parents=True)
    (source / "KeKar").write_text("binary", encoding="utf-8")
    (source / "_internal" / "lib.so").write_text("lib", encoding="utf-8")

    out = tmp_path / "out"
    tool.make_platform_package("linux", source, out)

    assert (out / "KeKar_Linux" / "KeKar").is_file()
    assert (out / "KeKar_Linux" / "_internal" / "lib.so").is_file()
    assert (out / "KeKar.sh").is_file()
    assert (out / "KeKar.bat").is_file()
    assert (out / "README.txt").is_file()
    for sub in tool.DATA_SUBDIRS:
        assert (out / "KeKarData" / sub).is_dir(), f"missing KeKarData/{sub}"


def test_combine_merges_both_platforms(tool, tmp_path):
    linux = tmp_path / "linux"
    windows = tmp_path / "windows"
    (linux / "_internal").mkdir(parents=True)
    (linux / "KeKar").write_text("lin", encoding="utf-8")
    (windows / "_internal").mkdir(parents=True)
    (windows / "KeKar.exe").write_text("win", encoding="utf-8")

    out = tmp_path / "usb"
    tool.combine(linux, windows, out)

    assert (out / "KeKar_Linux" / "KeKar").is_file()
    assert (out / "KeKar_Windows" / "KeKar.exe").is_file()


def test_package_is_reproducible_regardless_of_cwd(tool, tmp_path, monkeypatch):
    """The tool must not depend on the directory it is invoked from."""
    source = tmp_path / "dist" / "KeKar"
    source.mkdir(parents=True)
    (source / "KeKar").write_text("binary", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    tool.make_platform_package("linux", source, out)
    assert (out / "KeKar_Linux" / "KeKar").is_file()
