"""GitHub release updater: offline unit checks with mocked network calls."""
import hashlib
import json
from pathlib import Path

import pytest

from src.services import updater


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_asset_name_matches_variant_and_platform():
    assert updater.asset_name(True, "linux") == "KeKarLite_Linux.zip"
    assert updater.asset_name(True, "windows") == "KeKarLite_Windows.zip"
    assert updater.asset_name(False, "linux") == "KeKar_Linux.zip"
    assert updater.asset_name(False, "windows") == "KeKar_Windows.zip"


def test_version_compare_ignores_release_suffix():
    assert updater.parse_version("v1.6.3-production") > updater.parse_version("1.6.2")
    assert updater.parse_version("v1.6.2-production") == updater.parse_version("1.6.2")


def test_find_asset_uses_sha_digest(monkeypatch):
    payload = {
        "tag_name": "v1.6.3-production",
        "assets": [
            {"name": "KeKarLite_Windows.zip",
             "digest": "sha256:aaa", "browser_download_url": "win"},
            {"name": "KeKarLite_Linux.zip",
             "digest": "sha256:bbb", "browser_download_url": "linux"},
        ],
    }
    monkeypatch.setattr(updater.httpx, "get",
                        lambda *a, **k: _Response(payload))
    info = updater.fetch_latest(True, "linux")
    assert info["version"] == "1.6.3"
    assert info["asset"]["browser_download_url"] == "linux"
    assert info["asset"]["sha256"] == "bbb"


def test_help_menu_has_an_update_action(kekar_app):
    texts = [a.text() for a in kekar_app.main_window.help_menu.actions()]
    assert any("update" in (t or "").lower() for t in texts)


def test_update_dialog_reports_a_newer_version(kekar_app):
    from src.ui.update_dialog import UpdateDialog

    dialog = UpdateDialog(kekar_app, auto_check=False)
    try:
        dialog._show_info({"tag": "v9.9.9-production", "version": "9.9.9",
                           "asset": {}})
        assert "9.9.9" in dialog.status.text()
        assert dialog.install_btn.isEnabled()
    finally:
        dialog.close()


def test_verify_sha256(tmp_path):
    path = tmp_path / "asset.zip"
    path.write_bytes(b"hello")
    digest = hashlib.sha256(b"hello").hexdigest()
    assert updater.verify_sha256(path, digest) is True
    assert updater.verify_sha256(path, "0" * 64) is False


def test_find_installed_app_dir_supports_both_layouts(tmp_path):
    root = tmp_path
    (root / "KeKarLite_Linux").mkdir()
    (root / "KeKarLite_Linux" / "KeKarLite").write_text("binary")
    found = updater.find_installed_app_dir(root, "KeKarLite")
    assert found == root / "KeKarLite_Linux"
    nested = root / "portable"
    inner = nested / "KeKarLite_Linux" / "KeKarLite_Linux"
    inner.mkdir(parents=True)
    (inner / "KeKarLite").write_text("binary")
    found = updater.find_installed_app_dir(nested, "KeKarLite")
    assert found == nested / "KeKarLite_Linux" / "KeKarLite_Linux"


def test_stage_writes_an_updater_script(tmp_path, monkeypatch):
    monkeypatch.setattr(updater.os, "getpid", lambda: 4242)
    script = updater.write_apply_script(
        tmp_path, 4242, tmp_path / "new", tmp_path / "old",
        tmp_path / "launch.sh")
    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "4242" in text
    assert "KeKarData" not in text.split("\n")[0]
