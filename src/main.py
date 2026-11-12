"""KeKar command-line entry point.

This file is the PyInstaller entry point. Inside the bundle it runs as
``__main__``, so it must use ABSOLUTE imports (``src.*``). A relative import
here raises "attempted relative import with no known parent package".
"""
from __future__ import annotations

import logging
import sys
import time

from src._version import APP_NAME, APP_VERSION

# Set at import time so the startup measurement covers everything the app does
# between process launch and a visible window.
_START = time.perf_counter()

logger = logging.getLogger("kekar")

# Flags that must work with no display, no data directory, and no network.
# They are handled before Qt is imported so `KeKar --version` succeeds on a
# headless machine (build plan Task 0.3 requires exactly that).
_VERSION_FLAGS = {"--version", "-V"}
_HELP_FLAGS = {"--help", "-h"}


def _print_version() -> int:
    print(f"{APP_NAME} {APP_VERSION}")
    return 0


def _print_help() -> int:
    print(f"{APP_NAME} {APP_VERSION} - portable rental property manager")
    print()
    print("Usage: KeKar [option]")
    print("  --version, -V   show the version and exit")
    print("  --help,   -h    show this help and exit")
    print()
    print("KeKar is a GUI app; with no options it opens the main window.")
    return 0


def _build_application(argv):
    """Construct the QApplication. Imported lazily so --version stays cheap."""
    from src.app import Application

    return Application(argv)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)

    # Handle the informational flags first: they must never require a display.
    if any(a in _VERSION_FLAGS for a in args[1:]):
        return _print_version()
    if any(a in _HELP_FLAGS for a in args[1:]):
        return _print_help()

    from src.logging_config import configure_logging, install_exception_hook
    configure_logging()
    install_exception_hook()

    if sys.platform.startswith("win"):
        try:  # high-DPI correctness on Windows
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = _build_application(args)

    # First run: run the setup wizard before showing the main window. Kept here
    # (not in Application.__init__) so the app object can be constructed in
    # tests without a modal dialog blocking the suite.
    if not app.settings.is_configured():
        from src.ui.wizard import FirstRunWizard
        if FirstRunWizard(app).exec() != FirstRunWizard.DialogCode.Accepted:
            return 0

    app.show_main_window()
    logger.info("startup: %.2fs to a visible window", time.perf_counter() - _START)
    try:
        return app.exec()
    finally:
        # Never leave a worker thread running when the process tears down.
        from src.ui import worker
        worker.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
