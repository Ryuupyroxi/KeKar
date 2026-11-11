from src import paths


def test_data_dir_honors_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path))
    assert paths.data_dir() == tmp_path.resolve()


def test_data_dir_creates_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path / "KeKarData"))
    d = paths.data_dir()
    assert d.is_dir()
    assert paths.database_path().parent == d
    assert paths.photos_dir().parent == d


def test_data_dir_raises_when_nowhere_writable(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path / "missing"))
    monkeypatch.setenv("HOME", str(tmp_path / "nope"))
    monkeypatch.setattr(paths, "_writable", lambda p: False)
    try:
        paths.data_dir()
        raised = False
    except RuntimeError:
        raised = True
    assert raised
