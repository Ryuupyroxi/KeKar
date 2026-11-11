"""Central typography and widget sizing.

Every screen pulls its fonts from here. Before this module existed nothing in
the app set a font at all, so Qt fell back to a tiny default and the property
form was effectively unreadable on a 1280x800 display.
"""
from __future__ import annotations

from PyQt6.QtGui import QFont

# DejaVu Sans ships with Debian/MX and degrades gracefully elsewhere; on
# Windows, Qt substitutes a comparable sans face if it is missing.
FAMILY = "DejaVu Sans"
BASE_POINTS = 11


def app_font() -> QFont:
    """The one font the whole application uses."""
    font = QFont(FAMILY, BASE_POINTS)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def font(points: int, bold: bool = False) -> QFont:
    """A sized variant for headings and emphasis."""
    result = QFont(FAMILY, points)
    result.setBold(bold)
    return result
