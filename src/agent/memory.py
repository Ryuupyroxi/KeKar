"""Persistent agent memory (the MEMORY.md concept), owned by the app."""
from __future__ import annotations

from pathlib import Path

from ..paths import memory_dir

MEMORY_MAX_CHARS = 6000


class MemoryStore:
    def __init__(self, path: Path | None = None):
        self._path = path

    def path(self) -> Path:
        return self._path or (memory_dir() / "MEMORY.md")

    def read(self) -> str:
        p = self.path()
        if not p.exists():
            return ""
        return p.read_text(encoding="utf-8")

    def write(self, text: str) -> None:
        """Replace memory content. Round-trips exactly through read()."""
        p = self.path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text.strip(), encoding="utf-8")

    def append(self, line: str) -> None:
        existing = self.read().strip()
        self.write(f"{existing}\n{line.strip()}" if existing else line.strip())


def condense_memory(client, store: MemoryStore) -> str:
    """Summarize memory with the LLM when it grows past the cap."""
    text = store.read()
    if len(text) <= MEMORY_MAX_CHARS or client is None:
        return text
    summary = client.summarize(
        "Summarize these property-management notes in under 4000 characters, "
        "keeping all names, addresses, dollar amounts, dates, and applicant stages. "
        f"Notes:\n{text}"
    )
    store.write(summary)
    return summary
