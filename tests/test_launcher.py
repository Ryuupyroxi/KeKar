from pathlib import Path

from src.services.browser import launcher


def test_find_browser_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(launcher, "_candidate_paths", lambda kind: [Path("/nope")])
    assert launcher.find_browser("chrome") is None


def test_launch_builds_expected_flags(monkeypatch, tmp_path):
    recorded = {}

    class FakePopen:
        def __init__(self, args, **kw):
            recorded["args"] = args

    monkeypatch.setattr(launcher.subprocess, "Popen", FakePopen)
    # find_browser() rejects paths that do not exist, so patch the lookup rather
    # than feeding it a fake path.
    monkeypatch.setattr(launcher, "find_browser",
                        lambda kind: Path("/fake/chrome"))
    launcher.launch_browser("chrome", profile_dir=tmp_path, port=9333)
    args = recorded["args"]
    assert args[0] == "/fake/chrome"
    assert "--remote-debugging-port=9333" in args
    assert any(str(tmp_path) in a for a in args)
    assert "--no-first-run" in args


def test_find_browser_detects_real_binary(monkeypatch):
    monkeypatch.setattr(launcher, "_candidate_paths",
                        lambda kind: [Path("/usr/bin/chromium")])
    assert launcher.find_browser("chrome") == Path("/usr/bin/chromium")


def test_is_debug_port_open_false_when_closed():
    assert launcher.is_debug_port_open(59999) is False
