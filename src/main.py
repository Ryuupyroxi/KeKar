"""KeKar command-line entry point.

This file is the PyInstaller entry point. Inside the bundle it runs as
``__main__``, so it must use ABSOLUTE imports (``src.*``). A relative import
here raises "attempted relative import with no known parent package".
"""
from __future__ import annotations

import logging
import sys
import time

from src import features
from src._version import APP_VERSION, display_name

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
    print(f"{display_name()} {APP_VERSION}")
    return 0


def _print_help() -> int:
    print(f"{display_name()} {APP_VERSION} - portable rental property manager")
    print()
    print(f"Usage: {display_name()} [option]")
    print("  --version, -V   show the version and exit")
    print("  --help,   -h    show this help and exit")
    print()
    print(f"{display_name()} is a GUI app; with no options it opens the "
          "main window.")
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
    #
    # `start` is a local copy: reassigning the module-level _START here would
    # make it a local for the whole function and break the reads below.
    start = _START
    if features.chat_enabled() and not app.settings.is_configured():
        from src.ui.wizard import FirstRunWizard
        wizard = FirstRunWizard(app)
        # The wizard is the first window the user sees, so it is where the
        # cold-start measurement belongs. Timing past it would count however
        # long they spent typing their key.
        logger.info("startup: %.2fs to the first window (setup wizard)",
                    time.perf_counter() - start)
        if wizard.exec() != FirstRunWizard.DialogCode.Accepted:
            return 0
        start = time.perf_counter()

    app.show_main_window()
    # Accounts are opt-in: this locks the window only when the user asked for a
    # login and no saved session is still valid.
    app.maybe_require_login()
    # Offer the tour once, after the window is visible so the overlay has
    # something to cover.
    app.maybe_offer_tour()
    if app.provider_note:
        logger.info("provider: %s", app.provider_note)
        app.main_window.status(app.provider_note)
    logger.info("startup: %.2fs to a visible window",
                time.perf_counter() - start)
    try:
        return app.exec()
    finally:
        # Never leave a worker thread running when the process tears down.
        from src.ui import worker
        worker.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
