"""Tests for the USB packaging tools.

The launchers exist twice: as editable sources in assets/launchers/ and as
string constants inside tools/make_usb_package.py. This test fails if they
drift apart, so there is exactly one thing to edit.

The .desktop entry is deliberately not shipped: the Desktop Entry
Specification cannot express a portable Exec, so tools/install_linux.py
writes one with the real absolute path. These tests check that the installer
travels with the package and produces a valid entry.
"""
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "launchers"
INSTALLER = ROOT / "tools" / "install_linux.py"


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


def test_launcher_sources_exist():
    for name in ("KeKar.bat", "KeKar.sh"):
        assert (ASSETS / name).is_file(), f"missing assets/launchers/{name}"


def test_no_stale_desktop_file_is_shipped():
    """A .desktop baked into the package would need a machine-specific path."""
    assert not (ASSETS / "KeKar.desktop").exists()
    assert not hasattr(_load_tool(), "DESKTOP")


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
    # The one-click installer travels with the package.
    assert (out / "install_linux.py").is_file()
    assert (out / "install_linux.py").stat().st_mode & 0o111, \
        "install_linux.py must be executable to run from the drive"
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


def _load_installer():
    spec = importlib.util.spec_from_file_location("install_linux", INSTALLER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["install_linux"] = module
    spec.loader.exec_module(module)
    return module


def test_installer_uses_desktop_entry_quoting_not_shell_quoting():
    """shlex.quote emits single quotes, which desktop-file-validate rejects."""
    inst = _load_installer()
    plain = inst.desktop_exec(Path("/opt/kekar/KeKar"))
    assert plain == "/opt/kekar/KeKar"

    spaced = inst.desktop_exec(Path("/media/usb/KeKar App/KeKar"))
    assert spaced.startswith('"') and spaced.endswith('"')
    assert "'" not in spaced, "single quotes are not valid Exec quoting"
    assert spaced == '"/media/usb/KeKar App/KeKar"'


def test_generated_entry_names_the_icon_and_the_real_binary(tmp_path):
    inst = _load_installer()
    entry = inst.desktop_entry(tmp_path / "KeKar")
    assert "Icon=kekar" in entry
    assert f"Exec={tmp_path / 'KeKar'}" in entry
    assert "Terminal=false" in entry


def test_install_writes_an_entry_and_icons(tmp_path):
    inst = _load_installer()
    binary = tmp_path / "KeKar"
    binary.write_text("binary", encoding="utf-8")

    icon_dir = tmp_path / "icons"
    icon_dir.mkdir()
    for size in inst.ICON_SIZES:
        (icon_dir / f"kekar-{size}.png").write_bytes(b"\x89PNG\r\n")

    apps = tmp_path / "applications"
    written = inst.install(binary, icon_dir, desktop=False,
                           locations=[apps], home=tmp_path)

    entry = (apps / "kekar.desktop").read_text(encoding="utf-8")
    assert f"Exec={binary}" in entry
    assert str(apps / "kekar.desktop") in written
    for size in inst.ICON_SIZES:
        target = (tmp_path / ".local" / "share" / "icons" / "hicolor"
                  / f"{size}x{size}" / "apps" / "kekar.png")
        assert target.is_file(), f"icon {size}x{size} not installed"


def test_uninstall_removes_what_install_wrote(tmp_path):
    inst = _load_installer()
    binary = tmp_path / "KeKar"
    binary.write_text("binary", encoding="utf-8")
    apps = tmp_path / "applications"
    inst.install(binary, None, desktop=False, locations=[apps],
                 home=tmp_path)
    assert (apps / "kekar.desktop").is_file()

    removed = inst.uninstall([apps], home=tmp_path)
    assert not (apps / "kekar.desktop").exists()
    assert any("kekar.desktop" in path for path in removed)


def test_installer_validates_clean_when_the_tool_is_present():
    """Skip quietly where desktop-file-validate is not installed."""
    if not shutil.which("desktop-file-validate"):
        pytest.skip("desktop-file-validate not installed")
    inst = _load_installer()
    complaints = inst.validate(Path.home() / ".local" / "share"
                               / "applications" / "kekar.desktop")
    assert complaints == []


def test_windows_package_stages_the_installer_icon(tool, tmp_path):
    """The NSIS installer points its shortcuts at the package-root .ico."""
    source = tmp_path / "dist" / "KeKar"
    source.mkdir(parents=True)
    (source / "KeKar.exe").write_text("binary", encoding="utf-8")

    out = tmp_path / "out"
    tool.make_platform_package("windows", source, out)

    staged = out / "KeKar_Windows" / "kekar.ico"
    assert staged.is_file(), "Windows package must carry kekar.ico at its root"
    assert staged.read_bytes() == (ROOT / "src" / "resources" / "icons"
                                   / "kekar.ico").read_bytes()


def test_appimage_desktop_entry_names_the_kekar_icon():
    desktop = (ROOT / "packaging" / "linux" / "kekar.desktop").read_text(
        encoding="utf-8")
    assert "Icon=kekar" in desktop
    assert "utilities-terminal" not in desktop, "placeholder icon still wired"


def test_appimage_icon_is_a_square_png():
    from PIL import Image

    path = ROOT / "packaging" / "linux" / "kekar.png"
    assert path.is_file(), "AppImage needs packaging/linux/kekar.png"
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.width == image.height, "launcher icons must be square"


def test_packaged_icons_match_the_source_art():
    """The packaging copies must not drift from the generated assets."""
    icons = ROOT / "src" / "resources" / "icons"
    assert (ROOT / "packaging" / "windows" / "kekar.ico").read_bytes() \
        == (icons / "kekar.ico").read_bytes()
    assert (ROOT / "packaging" / "linux" / "kekar.png").read_bytes() \
        == (icons / "kekar-master.png").read_bytes()


def test_ci_builds_and_attaches_the_windows_installer():
    """A Windows release must carry the NSIS installer, not just the zip."""
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8")
    assert "makensis" in workflow, "CI never compiles the NSIS installer"
    assert "KeKar_Setup_" in workflow, "CI never attaches the installer"
    assert "choco install nsis" in workflow, "no fallback if NSIS is absent"
    assert "GITHUB_WORKSPACE" in workflow, (
        "makensis needs an absolute script path, or ${__FILEDIR__} resolves "
        "against the CWD and the icon is not found")


def test_installer_attach_step_is_not_pinned_to_one_version():
    """The filename carries the version, so the attach step must glob it."""
    nsi = (ROOT / "packaging" / "windows" / "KeKar_Installer.nsi").read_text(
        encoding="utf-8")
    assert 'KEKAR_OUT_FILE "KeKar_Setup_${VERSION}.exe"' in nsi, (
        "the default output name must still carry the version")
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8")
    assert "KeKar_Setup_*.exe" in workflow, (
        "attach the produced installer by glob, not a hard-coded version")
    assert "KEKAR_PACKAGE_DIR" in workflow and "KEKAR_PACKAGE_DIR" in nsi, (
        "the source folder must be a define: NSIS anchors a relative File "
        "path to the script, not the working directory")
    assert "KEKAR_OUT_FILE" in workflow and "KEKAR_OUT_FILE" in nsi, (
        "the output path must be a define too: NSIS anchors a relative "
        "OutFile to the script as well")
