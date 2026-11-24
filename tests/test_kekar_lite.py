"""End-to-end checks for the Lite composition: assistant yes, direct portals no."""
import os
import subprocess
import sys


def _run_lite(code: str, tmp_path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(KEKAR_VARIANT="lite", KEKAR_TESTING="1",
               QT_QPA_PLATFORM="offscreen",
               KEKAR_DATA_DIR=str(tmp_path / "KeKarData"))
    return subprocess.run([sys.executable, "-c", code], env=env,
                          capture_output=True, text=True, timeout=60)


def test_lite_application_keeps_the_assistant(tmp_path):
    proc = _run_lite(
        "from src import features\n"
        "from src.app import Application\n"
        "a = Application([])\n"
        "assert features.chat_enabled()\n"
        "assert not features.marketplace_enabled()\n"
        "assert not features.portal_sync_enabled()\n"
        "assert not features.maps_enabled()\n"
        "assert hasattr(a, 'agent_runner')\n"
        "assert a.chat_repo is not None\n"
        "assert a.main_window.chat_pane is not None\n"
        "a.main_window.close()\n"
        "print('OK')\n", tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_full_application_still_has_the_agent(kekar_app):
    from src import features
    if features.is_lite():
        return
    assert kekar_app.agent_runner is not None
    assert kekar_app.client is not None
    assert kekar_app.chat_repo is not None
