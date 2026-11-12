"""Embedded conversational assistant pane."""
from __future__ import annotations

import asyncio

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLineEdit, QMessageBox, QPushButton,
                             QTextBrowser, QVBoxLayout, QWidget)

from ..agent.client import LLMBusy
from ..agent.runner import (AgentCancelled, AgentStepLimit, CancelFlag)
from . import worker


class _AgentThread(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, app, message, history, cancel: CancelFlag):
        super().__init__()
        self.app = app
        self.message = message
        self.history = history
        self.cancel = cancel

    def run(self):
        try:
            result = asyncio.run(
                self.app.agent_runner.run(self.message, self.history,
                                          cancel=self.cancel))
            self.finished.emit(result)
        except AgentCancelled:
            self.failed.emit("cancelled")
        except AgentStepLimit:
            self.failed.emit(
                "The assistant got stuck. Please try a shorter request.")
        except LLMBusy as exc:
            # Quote the provider's own reason. LLMBusy carries the last
            # model's error text ("HTTP 429 — You have no credits remaining"),
            # which is the difference between "top up your account" and
            # "check your network" — hiding it made a billing problem look
            # like a connectivity one.
            detail = " ".join(str(exc).split())
            if detail:
                self.failed.emit(
                    f"The assistant could not answer. {detail} "
                    f"Check the key, the credits, or the model in Settings.")
            else:
                self.failed.emit(
                    "I can't reach the assistant right now, but your property "
                    "data is saved safely on this drive.")
        except Exception as exc:
            self.failed.emit(f"Something went wrong: {exc}")


class ChatPane(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._thread: _AgentThread | None = None
        self._cancel: CancelFlag | None = None
        self._last_user = ""
        self._pending_from = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        layout.addWidget(self.view, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText(
            'Ask about a property, or say "draft a message to John"...')
        self.input.returnPressed.connect(self.send)
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send)
        self.cancel_btn = QPushButton("Stop")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_run)
        row.addWidget(self.input, 1)
        row.addWidget(send_btn)
        row.addWidget(self.cancel_btn)
        layout.addLayout(row)

        tools = QHBoxLayout()
        clear_btn = QPushButton("Clear conversation")
        clear_btn.clicked.connect(self.clear_history)
        tools.addWidget(clear_btn)
        tools.addStretch(1)
        layout.addLayout(tools)

    # -- history -----------------------------------------------------------

    def load_history(self) -> None:
        """Show the stored conversation. Call once after the UI is built."""
        self.view.clear()
        for message in self.app.chat_repo.history(limit=50):
            self.add_message(message["role"], message["content"])

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self, "KeKar",
            "Clear the whole conversation?\n\n"
            "Your properties, photos and applicants are not affected.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.app.chat_repo.clear()
        self.view.clear()
        self.app.main_window.status("Conversation cleared.")

    # -- sending -----------------------------------------------------------

    def add_message(self, role: str, text: str) -> None:
        color = "#1565c0" if role == "user" else "#2e7d32"
        name = "You" if role == "user" else "KeKar"
        self.view.append(f'<p><b style="color:{color}">{name}:</b> {text}</p>')

    def send(self) -> None:
        message = self.input.text().strip()
        if not message or self._thread is not None:
            return
        if not self.app.settings.api_key:
            QMessageBox.information(
                self, "KeKar",
                "The assistant needs an API key.\n\n"
                "Open File → Settings and paste the key for KeKar's account. "
                "Everything else in KeKar works without one.")
            return
        self.input.clear()
        self.add_message("user", message)
        self._last_user = message
        self._pending_from = len(self.view.toPlainText())
        self.add_message("assistant", "Thinking...")
        self._cancel = CancelFlag()
        self.cancel_btn.setEnabled(True)
        history = self.app.chat_repo.history(limit=30)
        self._thread = worker.register(
            _AgentThread(self.app, message, history, self._cancel))
        self._thread.finished.connect(self._on_finished)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _cancel_run(self) -> None:
        if self._cancel is not None:
            self._cancel.cancel()
            self.cancel_btn.setEnabled(False)

    def _on_finished(self, result) -> None:
        self._replace_pending(result.text or "(no response)")
        self.app.chat_repo.add("user", self._last_user)
        self.app.chat_repo.add("assistant", result.text)
        worker.reap(self._thread)
        self._thread = None
        self._cancel = None
        self.cancel_btn.setEnabled(False)

    def _on_failed(self, message: str) -> None:
        if message == "cancelled":
            self._replace_pending("")
            self.app.main_window.status("Stopped.")
        else:
            self._replace_pending(message)
        worker.reap(self._thread)
        self._thread = None
        self._cancel = None
        self.cancel_btn.setEnabled(False)

    def _replace_pending(self, text: str) -> None:
        plain = self.view.toPlainText()
        self.view.setPlainText(plain[:self._pending_from])
        if text:
            self.add_message("assistant", text)
