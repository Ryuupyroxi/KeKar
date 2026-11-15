"""Application settings, persisted encrypted at KeKarData/config/settings.enc."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..paths import config_dir
from . import crypto

SETTINGS_FILE = "settings.enc"
SALT_FILE = "settings.salt"


@dataclass
class Settings:
    api_key: str = ""
    provider: str = "openrouter"         # providers.Provider.id, or "custom"
    api_base: str = "https://openrouter.ai/api/v1"
    model_chain: list[str] = field(default_factory=lambda: [
        "meta-llama/llama-3.1-8b-instruct",
        "google/gemini-2.5-flash-lite",
        "deepseek/deepseek-v4.1-flash-1017",
    ])
    request_timeout_s: int = 45
    max_agent_steps: int = 8
    browser_kind: str = "auto"          # auto | chrome | edge
    autofill_enabled: bool = False      # opt-in, experimental
    backup_keep_days: int = 30
    passphrase_protected: bool = False
    tour_completed: bool = False
    # system | light | dark | oled — see src/ui/palette.py
    theme: str = "system"
    # Panel layout, remembered between runs. True = collapsed to the edge.
    sidebar_collapsed: bool = False
    chat_collapsed: bool = False
    # The client's example lease. Empty means "use the built-in template".
    lease_template: str = ""
    landlord_name: str = ""
    # Accounts. Off by default, so nothing about the app changes until the user
    # turns it on in File -> Accounts.
    require_login: bool = False
    auto_lock_minutes: int = 0
    session_token: str = ""

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Settings":
        return cls(**json.loads(text))

    def save(self) -> Path:
        out = config_dir() / SETTINGS_FILE
        out.parent.mkdir(parents=True, exist_ok=True)
        if self.passphrase_protected:
            raise RuntimeError("passphrase mode requires an interactive prompt")
        out.write_bytes(crypto.encrypt(self.to_json().encode("utf-8"),
                                      crypto.load_app_key()))
        return out

    @classmethod
    def load(cls) -> "Settings":
        path = config_dir() / SETTINGS_FILE
        if not path.exists():
            return cls()
        plain = crypto.decrypt(path.read_bytes(), crypto.load_app_key())
        return cls.from_json(plain.decode("utf-8"))
