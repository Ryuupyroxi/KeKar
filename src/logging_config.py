"""Logging setup: file + rotation, with key redaction."""
from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .paths import logs_dir

_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _KEY_RE.sub("[REDACTED]", record.msg)
        return True


def configure_logging(level: int = logging.INFO) -> Path:
    path = logs_dir() / "kekar.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    return path


def install_exception_hook() -> None:
    def hook(exc_type, exc, tb):
        logging.getLogger("kekar").exception(
            "Unhandled exception", exc_info=(exc_type, exc, tb))
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app:
                QMessageBox.critical(
                    None, "KeKar",
                    "Something went wrong. Your data is safe. "
                    "Please restart KeKar; the details were written to the log.")
        except Exception:
            pass
    sys.excepthook = hook
