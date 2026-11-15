"""Account management: the plumbing for the client-facing feature.

Opt-in. With `require_login` off (the default) none of this gates the app, so
existing behaviour is unchanged and the feature that needs a login can be built
against real accounts later.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ..data.user_repo import ROLES
from .theme import font


class UsersDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Accounts")
        self.resize(560, 460)
        self.setWindowIcon(self.app.main_window.windowIcon())

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Username", "Name", "Role"])
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        form = QFormLayout()
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("Full name (optional)")
        self.role = QComboBox()
        self.role.addItems(["owner", "member"])
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username", self.username)
        form.addRow("Name", self.display_name)
        form.addRow("Role", self.role)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        actions = QHBoxLayout()
        add_btn = QPushButton("Add account")
        add_btn.clicked.connect(self.add_user)
        reset_btn = QPushButton("Reset password")
        reset_btn.clicked.connect(self.reset_password)
        remove_btn = QPushButton("Remove account")
        remove_btn.clicked.connect(self.remove_user)
        actions.addWidget(add_btn)
        actions.addWidget(reset_btn)
        actions.addWidget(remove_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.require_login = QCheckBox(
            "Ask for a password when KeKar starts")
        self.require_login.setChecked(bool(self.app.settings.require_login))
        self.require_login.toggled.connect(self._on_require_toggled)
        layout.addWidget(self.require_login)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.reload()

    def reload(self) -> None:
        users = self.app.user_repo.list()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0,
                               QTableWidgetItem(user["username"]))
            self.table.setItem(row, 1,
                               QTableWidgetItem(user["display_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(user["role"]))
            self.table.item(row, 0).setData(256, user["id"])
        self.table.blockSignals(False)
        self.require_login.setChecked(bool(self.app.settings.require_login))

    def _on_require_toggled(self, checked: bool) -> None:
        if checked and self.app.user_repo.count_users() == 0:
            QMessageBox.information(
                self, "KeKar",
                "Add an account first. KeKar cannot ask for a password when "
                "there is no account to check it against.")
            self.require_login.setChecked(False)
            return
        self.app.settings.require_login = bool(checked)
        try:
            self.app.settings.save()
        except Exception as exc:
            QMessageBox.warning(self, "KeKar", f"Could not save: {exc}")

    def add_user(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            QMessageBox.information(self, "KeKar",
                                    "A username and password are both needed.")
            return
        if len(password) < 8:
            QMessageBox.information(
                self, "KeKar", "Use at least 8 characters for the password.")
            return
        if self.app.user_repo.get_by_username(username) is not None:
            QMessageBox.information(self, "KeKar",
                                    "That username is already taken.")
            return
        self.app.user_repo.create(
            username, password,
            display_name=self.display_name.text().strip(),
            role=self.role.currentText())
        self.username.clear()
        self.display_name.clear()
        self.password.clear()
        self.reload()
        self.app.main_window.status(f"Account added for {username}.")

    def _selected_user(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(256) if item is not None else None

    def reset_password(self) -> None:
        user_id = self._selected_user()
        if user_id is None:
            QMessageBox.information(self, "KeKar", "Choose an account first.")
            return
        password = self.password.text()
        if len(password) < 8:
            QMessageBox.information(
                self, "KeKar", "Use at least 8 characters for the password.")
            return
        self.app.user_repo.set_password(user_id, password)
        self.password.clear()
        self.app.main_window.status("Password updated.")

    def remove_user(self) -> None:
        user_id = self._selected_user()
        if user_id is None:
            QMessageBox.information(self, "KeKar", "Choose an account first.")
            return
        if self.app.user_repo.count_users() <= 1:
            QMessageBox.information(
                self, "KeKar",
                "Keep at least one account, or turn off 'Ask for a password'.")
            return
        answer = QMessageBox.question(self, "KeKar",
                                      "Remove this account?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.app.user_repo.delete(user_id)
        self.reload()
        self.app.main_window.status("Account removed.")
