"""Cross-platform clipboard access via Qt (works on Windows and Linux)."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from ..data.models import Property
from .listing_compiler import compile_listing


def copy_text(text: str) -> bool:
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("clipboard requires a running QApplication")
    QApplication.clipboard().setText(text)
    return True


def copy_listing(prop: Property) -> str:
    text = compile_listing(prop)
    copy_text(text)
    return text
