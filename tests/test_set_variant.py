"""The build variant stamp is temporary and always restored."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool(monkeypatch, stamp_path: Path):
    spec = importlib.util.spec_from_file_location(
        "set_variant", ROOT / "tools" / "set_variant.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["set_variant"] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STAMP", stamp_path)
    return module


def test_stamp_writes_a_valid_python_module(monkeypatch, tmp_path):
    stamp = tmp_path / "src" / "_variant.py"
    stamp.parent.mkdir()
    tool = _tool(monkeypatch, stamp)
    tool.stamp("lite")
    assert 'VARIANT = "lite"' in stamp.read_text(encoding="utf-8")


def test_main_restores_an_absent_stamp(monkeypatch, tmp_path):
    stamp = tmp_path / "src" / "_variant.py"
    stamp.parent.mkdir()
    tool = _tool(monkeypatch, stamp)
    monkeypatch.setattr(sys, "argv", ["set_variant.py", "lite"])
    assert tool.main() == 0
    assert not stamp.exists()


def test_main_restores_previous_contents(monkeypatch, tmp_path):
    stamp = tmp_path / "src" / "_variant.py"
    stamp.parent.mkdir()
    stamp.write_text("VARIANT = 'full'  # keep me\n", encoding="utf-8")
    tool = _tool(monkeypatch, stamp)
    monkeypatch.setattr(sys, "argv", ["set_variant.py", "lite"])
    assert tool.main() == 0
    assert stamp.read_text(encoding="utf-8") == "VARIANT = 'full'  # keep me\n"
