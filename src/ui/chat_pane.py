"""Embedded conversational assistant pane."""
from __future__ import annotations

import asyncio

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLineEdit, QPushButton, QTextBrowser,
                             QVBoxLayout, QWidget)

from ..agent.client import LLMBusy
from ..agent.runner import AgentCancelled, AgentStepLimit


class _AgentThread(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, app, message, history):
        super().__init__()
        self.app = app
        self.message = message
        self.history = history

    def run(self):
        try:
            result = asyncio.run(
                self.app.agent_runner.run(self.message, self.history))
            self.finished.emit(result)
        except AgentCancelled:
            self.failed.emit("cancelled")
        except AgentStepLimit:
            self.failed.emit("The assistant got stuck. Please try a shorter request.")
        except LLMBusy:
            self.failed.emit(
                "I can't reach the assistant right now, but your property data "
                "is saved safely on this drive.")
        except Exception as exc:
            self.failed.emit(f"Something went wrong: {exc}")


class ChatPane(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._thread: _AgentThread | None = None
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
        row.addWidget(self.input, 1)
        row.addWidget(send_btn)
        layout.addLayout(row)

    def add_message(self, role: str, text: str) -> None:
        color = "#1565c0" if role == "user" else "#2e7d32"
        name = "You" if role == "user" else "KeKar"
        self.view.append(f'<p><b style="color:{color}">{name}:</b> {text}</p>')

    def send(self) -> None:
        message = self.input.text().strip()
        if not message or self._thread is not None:
            return
        self.input.clear()
        self.add_message("user", message)
        self._last_user = message
        # remember where the placeholder starts so it can be replaced cleanly
        self._pending_from = len(self.view.toPlainText())
        self.add_message("assistant", "Thinking...")
        history = self.app.chat_repo.history(limit=30)
        self._thread = _AgentThread(self.app, message, history)
        self._thread.finished.connect(self._on_finished)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _on_finished(self, result) -> None:
        self._replace_pending(result.text or "(no response)")
        self.app.chat_repo.add("user", self._last_user)
        self.app.chat_repo.add("assistant", result.text)
        self._thread = None

    def _on_failed(self, message: str) -> None:
        self._replace_pending(message)
        self._thread = None

    def _replace_pending(self, text: str) -> None:
        plain = self.view.toPlainText()
        self.view.setPlainText(plain[:self._pending_from])
        self.add_message("assistant", text)
