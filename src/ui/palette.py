"""Colour palettes for the light, dark and OLED themes.

One palette drives everything: the generated QSS, the widgets that paint their
own colours, and the status tints. Nothing outside this module hardcodes a hex
value, so a theme is a single switch rather than a hunt.

Status colours (vacant, rented, the CRM stages) keep their meaning in every
theme — only their brightness moves, so they stay legible on a dark background.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    window: str
    panel: str
    input_bg: str
    text: str
    text_secondary: str
    border: str
    border_input: str
    accent: str
    accent_hover: str
    accent_pressed: str
    #: Text drawn on top of the accent colour (default buttons, selections).
    on_accent: str
    selection: str
    scroll_handle: str
    tooltip_bg: str
    tooltip_text: str
    vacant: str
    rented: str
    neutral: str
    online: str
    offline: str
    warn_bg: str
    warn_text: str
    info_bg: str
    info_text: str
    chat_user: str
    chat_assistant: str
    stages: dict[str, str] = field(default_factory=dict)


LIGHT = Theme(
    key="light", name="Light",
    window="#f5f4f1", panel="#ffffff", input_bg="#ffffff",
    text="#2b2b28", text_secondary="#6b655c",
    border="#ddd8d0", border_input="#8f8880",
    accent="#2e5e4e", accent_hover="#265042", accent_pressed="#1f4236",
    on_accent="#ffffff",
    selection="#e3efe9", scroll_handle="#9a948a",
    tooltip_bg="#2b2b28", tooltip_text="#ffffff",
    vacant="#2e7d32", rented="#c62828", neutral="#616161",
    online="#2e7d32", offline="#c8860d",
    warn_bg="#fff3cd", warn_text="#664d03",
    info_bg="#e3f2fd", info_text="#0d47a1",
    chat_user="#1565c0", chat_assistant="#2e7d32",
    stages={
        "Inquiry Received": "#8a8f98",
        "Questionnaire Sent": "#3f7fbf",
        "Background Check": "#b07a2a",
        "Approved": "#2e7d32",
        "Rejected": "#c62828",
    },
)

DARK = Theme(
    key="dark", name="Dark",
    window="#1e1c1a", panel="#2a2724", input_bg="#232019",
    text="#ece7e0", text_secondary="#a8a098",
    border="#3d3833", border_input="#7a7268",
    accent="#4c9a82", accent_hover="#5aae94", accent_pressed="#3d7d69",
    on_accent="#0b1a15",
    selection="#2f4a41", scroll_handle="#8a8178",
    tooltip_bg="#ece7e0", tooltip_text="#1e1c1a",
    vacant="#5cb860", rented="#e57373", neutral="#9a938a",
    online="#5cb860", offline="#d8a24a",
    warn_bg="#4a3f22", warn_text="#f0d48a",
    info_bg="#1d3548", info_text="#9cc8ee",
    chat_user="#6aa6e8", chat_assistant="#5cb860",
    stages={
        "Inquiry Received": "#9aa0aa",
        "Questionnaire Sent": "#6fa8d8",
        "Background Check": "#d0a05a",
        "Approved": "#5cb860",
        "Rejected": "#e57373",
    },
)

OLED = Theme(
    key="oled", name="OLED",
    window="#000000", panel="#0a0a0a", input_bg="#000000",
    text="#f2f2f2", text_secondary="#9a9a9a",
    border="#262626", border_input="#5a5a5a",
    accent="#4c9a82", accent_hover="#5aae94", accent_pressed="#3d7d69",
    on_accent="#0b1a15",
    selection="#16211d", scroll_handle="#6a6a6a",
    tooltip_bg="#f2f2f2", tooltip_text="#000000",
    vacant="#5cb860", rented="#e57373", neutral="#9a9a9a",
    online="#5cb860", offline="#d8a24a",
    warn_bg="#3a3018", warn_text="#f0d48a",
    info_bg="#12212e", info_text="#9cc8ee",
    chat_user="#6aa6e8", chat_assistant="#5cb860",
    stages={
        "Inquiry Received": "#9aa0aa",
        "Questionnaire Sent": "#6fa8d8",
        "Background Check": "#d0a05a",
        "Approved": "#5cb860",
        "Rejected": "#e57373",
    },
)

THEMES: dict[str, Theme] = {
    "light": LIGHT,
    "dark": DARK,
    "oled": OLED,
}

#: Valid values for Settings.theme, in the order the UI should offer them.
CHOICES = ("system", "light", "dark", "oled")


def is_valid(key: str) -> bool:
    return key in CHOICES


def _os_scheme() -> str:
    """Read the operating system's light/dark preference. Defaults to light."""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is None:
            return "light"
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except Exception:
        pass
    return "light"


def resolve(key: str) -> Theme:
    """Map a stored preference to a concrete palette.

    ``system`` follows the OS; an unknown value falls back to light rather than
    raising, so a corrupted settings file cannot stop the app from starting.
    """
    if key == "system":
        return THEMES[_os_scheme()]
    return THEMES.get(key, LIGHT)


def _channel(value: float) -> float:
    value /= 255.0
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return 0.0
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two hex colours (1..21)."""
    a, b = luminance(foreground), luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def text_on(background: str) -> str:
    """Black or white, whichever reads better on the given colour."""
    dark = contrast("#111111", background)
    light = contrast("#ffffff", background)
    return "#111111" if dark >= light else "#ffffff"


def required_pairs(theme: Theme) -> list[tuple[str, str, float]]:
    """The colour pairs that must stay readable, with their minimum ratio.

    4.5:1 is the WCAG AA threshold for body text; 3:0:1 applies to large text
    and UI affordances such as borders.
    """
    return [
        ("body text on window", theme.text, theme.window, 4.5),
        ("body text on panel", theme.text, theme.panel, 4.5),
        ("secondary text on window", theme.text_secondary, theme.window, 4.5),
        ("accent on window", theme.accent, theme.window, 3.0),
        ("text on accent", theme.on_accent, theme.accent, 4.5),
        ("input text", theme.text, theme.input_bg, 4.5),
        # An input's boundary has to be identifiable without colour, so it is
        # held to the WCAG non-text ratio. The group border is decorative.
        ("input border", theme.border_input, theme.input_bg, 3.0),
        ("decorative border", theme.border, theme.window, 1.2),
        ("warn text", theme.warn_text, theme.warn_bg, 4.5),
        ("info text", theme.info_text, theme.info_bg, 4.5),
        ("status stripe", theme.vacant, theme.window, 3.0),
        ("rented stripe", theme.rented, theme.window, 3.0),
    ]
