from src.agent.memory import MemoryStore, condense_memory, MEMORY_MAX_CHARS


def test_memory_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path))
    store = MemoryStore()
    store.write("# Memory\n\n- 123 Main St rents for $850")
    assert "123 Main St" in store.read()
    store.append("- New note")
    assert "New note" in store.read()


def test_memory_survives_reopen(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path))
    MemoryStore().write("persistent")
    assert MemoryStore().read() == "persistent"


def test_write_read_roundtrips_exactly(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path))
    store = MemoryStore()
    for text in ("one line", "multi\nline\nnote", "  padded  "):
        store.write(text)
        assert store.read() == text.strip()


def test_condense_short_circuits_when_small(tmp_path, monkeypatch):
    monkeypatch.setenv("KEKAR_DATA_DIR", str(tmp_path))
    store = MemoryStore()
    store.write("small")
    assert condense_memory(None, store) == "small"
