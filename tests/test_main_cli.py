"""Tests for the command-line entry point."""
import sys

import pytest

import src.main as main_module


def test_version_flag_prints_version(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["KeKar", "--version"])
    assert main_module.main() == 0
    out = capsys.readouterr().out
    assert "KeKar" in out and "1.6.0" in out


def test_version_flag_supports_short_form(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["KeKar", "-V"])
    assert main_module.main() == 0
    assert "1.6.0" in capsys.readouterr().out


def test_help_flag_prints_usage(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["KeKar", "--help"])
    assert main_module.main() == 0
    assert "--version" in capsys.readouterr().out


def test_version_flag_does_not_construct_the_app(monkeypatch):
    """--version must work on a machine with no display and no data dir."""
    called = []
    monkeypatch.setattr(sys, "argv", ["KeKar", "--version"])
    monkeypatch.setattr(main_module, "_build_application",
                        lambda argv: called.append(True))
    assert main_module.main() == 0
    assert called == []


def test_version_flag_does_not_import_qt(monkeypatch):
    """Qt must not be needed for --version (headless build machines)."""
    import builtins

    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("PyQt6"):
            raise AssertionError("PyQt6 imported during --version")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(sys, "argv", ["KeKar", "--version"])
    monkeypatch.setattr(builtins, "__import__", guarded)
    assert main_module.main() == 0


def test_main_accepts_explicit_argv(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["KeKar"])
    assert main_module.main(["KeKar", "--version"]) == 0
    assert "1.6.0" in capsys.readouterr().out


def test_app_version_matches_nsi_installer():
    """The Windows installer and the app must not disagree on version."""
    from pathlib import Path

    nsi = Path("packaging/windows/KeKar_Installer.nsi")
    if not nsi.exists():
        pytest.skip("NSIS script not present")
    text = nsi.read_text(encoding="utf-8")
    assert main_module.APP_VERSION in text


def test_lite_version_flag_prints_lite_name(monkeypatch, capsys):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    from src.main import main
    from src._version import APP_VERSION
    assert main(["KeKarLite", "--version"]) == 0
    assert capsys.readouterr().out.strip() == f"KeKar Lite {APP_VERSION}"


def test_lite_help_still_works_headless(monkeypatch, capsys):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    from src.main import main
    assert main(["KeKarLite", "--help"]) == 0
    out = capsys.readouterr().out
    assert "KeKar Lite" in out
    assert "--version" in out
