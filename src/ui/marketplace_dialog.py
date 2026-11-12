"""Marketplace autofill, with a hard stop before publishing.

The automation fills the listing form and stops. It never clicks Publish —
that is always a human decision. This dialog makes that explicit and reports
plainly what happened.
"""
from __future__ import annotations

import asyncio

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QTextEdit,
                             QVBoxLayout)

from .._version import APP_NAME
from ..data.models import Property
from ..paths import browser_profile_dir
from ..services.browser import launcher
from ..services.browser.cdp_client import CDPClient, CDPUnavailable
from ..services.browser.marketplace import (MarketplaceAutomation,
                                            load_selectors)
from . import worker

DEBUG_PORT = launcher.DEBUG_PORT


class _AutofillThread(QThread):
    """Runs the browser automation off the UI thread."""

    done = pyqtSignal(dict)

    def __init__(self, prop: Property, port: int = DEBUG_PORT):
        super().__init__()
        self.prop = prop
        self.port = port

    def run(self) -> None:
        try:
            if not launcher.is_debug_port_open(self.port):
                launcher.launch_browser(profile_dir=browser_profile_dir(),
                                        port=self.port)
            client = CDPClient(self.port)
            try:
                client.connect()
                result = asyncio.run(
                    MarketplaceAutomation(client, load_selectors())
                    .autofill_listing(self.prop))
            finally:
                client.close()
            self.done.emit(result)
        except CDPUnavailable as exc:
            self.done.emit({"status": "failed", "detail": str(exc)})
        except FileNotFoundError as exc:
            self.done.emit({"status": "failed", "detail": str(exc)})
        except Exception as exc:  # never let a browser quirk crash the app
            self.done.emit({"status": "failed",
                            "detail": f"{type(exc).__name__}: {exc}"})


class MarketplaceDialog(QDialog):
    """Fills a Facebook Marketplace listing draft. Never publishes."""

    def __init__(self, app, prop: Property, parent=None):
        super().__init__(parent)
        self.app = app
        self.prop = prop
        self._thread: _AutofillThread | None = None
        self.setWindowTitle("Publish to Marketplace")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"<b>{prop.address}</b><br>"
            f"KeKar will open Marketplace in its own browser window, fill in "
            f"the details and photos, and then stop.<br>"
            f"<b>Nothing is published without you.</b> You review the draft and "
            f"click Publish yourself."))

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("The result will appear here.")
        layout.addWidget(self.result, 1)

        buttons = QDialogButtonBox()
        self.go_btn = buttons.addButton("Fill the listing",
                                        QDialogButtonBox.ButtonRole.AcceptRole)
        self.go_btn.clicked.connect(self._start)
        close_btn = buttons.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _start(self) -> None:
        if self._thread is not None:
            return
        if not self.app.settings.autofill_enabled:
            self.result.setPlainText(
                "Marketplace auto-fill is turned off.\n\n"
                "It is an experimental feature. To turn it on, open "
                "File → Settings and enable 'Auto-fill Marketplace listings'.\n\n"
                "The listing text is always available with 'Copy listing' — "
                "that works and is the safer option.")
            return
        self.go_btn.setEnabled(False)
        self.result.setPlainText("Opening the browser and filling the form...")
        self._thread = worker.register(_AutofillThread(self.prop))
        self._thread.done.connect(self._on_done)
        self._thread.start()

    def _on_done(self, result: dict) -> None:
        # The thread can outlive this dialog's usefulness, but it must never
        # be destroyed while still running — that aborts the process.
        worker.reap(self._thread)
        self._thread = None
        self.go_btn.setEnabled(True)
        status = result.get("status", "failed")
        detail = result.get("detail", "Nothing happened.")
        if status == "autofilled":
            self.result.setPlainText(
                f"{detail}\n\n"
                f"Review the draft in the browser window, then click Publish "
                f"yourself. KeKar did not publish anything.")
        elif status == "needs_review":
            self.result.setPlainText(
                f"{detail}\n\n"
                f"Nothing has been published. You can finish the listing "
                f"by hand, or use 'Copy listing' and paste it yourself.")
        else:
            self.result.setPlainText(
                f"Auto-fill did not complete.\n\n{detail}\n\n"
                f"Nothing has been published. 'Copy listing' still works.")
