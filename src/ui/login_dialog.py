"""Login dialog. The dialog is dumb: the app validates, the dialog reports."""
from __future__ import annotations

from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel,
                             QLineEdit, QVBoxLayout)

from .theme import font


class LoginDialog(QDialog):
    """Ask for a username and password, and hand them to `app.login`.

    `exec()` returns True only when the app accepted the credentials, so the
    caller can treat a rejected dialog as "no session", never as "logged in".
    """

    def __init__(self, app, parent=None, title: str = "Log in"):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle(title)
        self.setMinimumWidth(340)
        self.setWindowIcon(self.app.main_window.windowIcon())

        layout = QVBoxLayout(self)
        self.message = QLabel("Enter your username and password.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        form = QFormLayout()
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        self.username.returnPressed.connect(self._try_login)
        self.password.returnPressed.connect(self._try_login)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Log in")
        buttons.accepted.connect(self._try_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _try_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self._warn("Enter both a username and a password.")
            return
        if not self.app.login(username, password):
            # Deliberately vague: saying which half was wrong tells an attacker
            # which usernames exist.
            self._warn("That username and password were not recognised.")
            self.password.clear()
            self.password.setFocus()
            return
        self.accept()

    def _warn(self, text: str) -> None:
        self.message.setText(text)
        self.message.setStyleSheet(
            f"color:{self.app.current_theme().warn_text};")
        self.message.setFont(font(10))
