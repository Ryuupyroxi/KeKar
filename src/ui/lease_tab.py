"""Lease tab: draw up a lease from the client's example lease.

The client supplies an example lease as plain text. It is kept as a template
with ``{{markers}}``, and the tab fills a copy for the selected property and
tenant. The finished lease can be copied or stored; the template is never
modified by generating one.
"""
from __future__ import annotations

from urllib.parse import urlencode

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QPlainTextEdit,
                             QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..data.models import Lease
from ..services import lease_builder
from ..services.clipboard import copy_text
from .palette import Theme
from .theme import font

#: Some mail clients truncate a mailto: body well before this.
MAILTO_SOFT_LIMIT = 1500


class LeaseTab(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._theme: Theme | None = None

        layout = QVBoxLayout(self)

        # -- who and where -------------------------------------------------
        self.property_combo = QComboBox()
        self.property_combo.currentIndexChanged.connect(
            self._on_property_changed)
        self.tenant_edit = QLineEdit()
        self.tenant_edit.setPlaceholderText("Tenant name")
        self.landlord_edit = QLineEdit()
        self.landlord_edit.setPlaceholderText("Landlord name")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Tenant email (optional)")
        self.term_spin = QSpinBox()
        self.term_spin.setRange(1, 60)
        self.term_spin.setValue(12)
        self.term_spin.setSuffix(" months")
        # Two rows: five fields in one row squeezed the boxes so typed values
        # were cut off ("n Doe", "mith").
        row_one = QHBoxLayout()
        row_two = QHBoxLayout()
        for widget, label, row in (
                (self.property_combo, "Property", row_one),
                (self.tenant_edit, "Tenant", row_one),
                (self.landlord_edit, "Landlord", row_one),
                (self.email_edit, "Tenant email", row_two),
                (self.term_spin, "Term", row_two)):
            row.addWidget(QLabel(label))
            row.addWidget(widget, 1)
        layout.addLayout(row_one)
        layout.addLayout(row_two)

        # -- template ------------------------------------------------------
        template_bar = QHBoxLayout()
        self.load_example_btn = QPushButton("Load example lease…")
        self.load_example_btn.clicked.connect(self.load_example)
        self.save_template_btn = QPushButton("Save as template")
        self.save_template_btn.clicked.connect(self.save_template)
        self.reset_template_btn = QPushButton("Use built-in template")
        self.reset_template_btn.clicked.connect(self.reset_template)
        self.unknown_label = QLabel("")
        self.unknown_label.setWordWrap(True)
        for widget in (self.load_example_btn, self.save_template_btn,
                       self.reset_template_btn):
            template_bar.addWidget(widget)
        template_bar.addStretch(1)
        layout.addLayout(template_bar)
        layout.addWidget(self.unknown_label)

        self.template_edit = QPlainTextEdit()
        self.template_edit.setPlaceholderText(
            "Paste the example lease the client provided, or load it from a "
            "file. {{address}}, {{rent}} and other markers are filled in when "
            "you generate.")
        self.template_edit.setFont(font(10))
        layout.addWidget(self.template_edit, 1)

        # -- actions -------------------------------------------------------
        actions = QHBoxLayout()
        self.generate_btn = QPushButton("Generate lease")
        self.generate_btn.clicked.connect(self.generate)
        self.copy_btn = QPushButton("Copy to clipboard")
        self.copy_btn.clicked.connect(self.copy_lease)
        self.print_btn = QPushButton("Print…")
        self.print_btn.clicked.connect(self.print_lease)
        self.email_btn = QPushButton("Email…")
        self.email_btn.clicked.connect(self.email_lease)
        self.save_btn = QPushButton("Save lease")
        self.save_btn.clicked.connect(self.save_lease)
        self.new_btn = QPushButton("New lease")
        self.new_btn.clicked.connect(self.new_lease)
        for widget in (self.generate_btn, self.copy_btn, self.print_btn,
                       self.email_btn, self.save_btn, self.new_btn):
            actions.addWidget(widget)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(font(10))
        layout.addWidget(self.preview, 2)

        # -- saved -----------------------------------------------------
        saved_bar = QHBoxLayout()
        self.saved_combo = QComboBox()
        self.saved_combo.currentIndexChanged.connect(self._load_saved)
        self.delete_lease_btn = QPushButton("Delete saved lease")
        self.delete_lease_btn.clicked.connect(self.delete_saved)
        saved_bar.addWidget(QLabel("Saved leases"))
        saved_bar.addWidget(self.saved_combo, 1)
        saved_bar.addWidget(self.delete_lease_btn)
        layout.addLayout(saved_bar)

        self._loading = False
        self._editing_id: int | None = None
        self.reset_template()

    # -- template ----------------------------------------------------------

    def template(self) -> str:
        return self.template_edit.toPlainText()

    def set_template(self, text: str) -> None:
        self._loading = True
        self.template_edit.setPlainText(text)
        self._loading = False
        self._warn_unknown()

    def reset_template(self) -> None:
        """Fall back to the built-in template, or the saved client one."""
        saved = self.app.settings.lease_template
        self.set_template(saved if saved.strip()
                          else lease_builder.DEFAULT_TEMPLATE)

    def load_example(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose the example lease", "",
            "Text files (*.txt *.md);;All files (*)")
        if not path:
            return
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as exc:
            QMessageBox.warning(self, "KeKar", f"Could not read that file:\n{exc}")
            return
        self.set_template(text)
        self.app.main_window.status(f"Loaded example lease from {path}.")

    def save_template(self) -> None:
        self.app.settings.lease_template = self.template()
        try:
            self.app.settings.save()
        except Exception as exc:
            QMessageBox.warning(self, "KeKar", f"Could not save the template:\n{exc}")
            return
        self.app.main_window.status("Example lease saved as the template.")

    def _warn_unknown(self) -> None:
        unknown = lease_builder.unknown_tokens(self.template())
        if unknown:
            shown = ", ".join("{{" + name + "}}" for name in unknown)
            self.unknown_label.setText(
                "This template uses markers KeKar does not fill: " + shown)
        else:
            self.unknown_label.setText("")

    # -- properties --------------------------------------------------------

    def reload(self) -> None:
        # The views were rebuilt against a different set of rows; an id held
        # from before may no longer exist, and saving it would silently
        # update nothing.
        self._editing_id = None
        props = self.app.property_repo.list()
        self._loading = True
        self.property_combo.clear()
        for prop in props:
            label = prop.address
            if prop.city:
                label += f", {prop.city}"
            self.property_combo.addItem(label, prop.id)
        self._loading = False
        self._on_property_changed()
        self._reload_saved()

    def _reload_saved(self) -> None:
        leases = self.app.lease_repo.list()
        self.saved_combo.clear()
        self.saved_combo.addItem("(no saved lease)", None)
        for lease in leases:
            who = lease.tenant_name or "(unnamed tenant)"
            prop = None
            if lease.property_id is not None:
                prop = self.app.property_repo.get(lease.property_id)
            where = prop.address if prop else "no property"
            self.saved_combo.addItem(f"{who} — {where}", lease.id)

    def _load_saved(self) -> None:
        lease_id = self.saved_combo.currentData()
        if not lease_id:
            return
        lease = self.app.lease_repo.get(int(lease_id))
        if lease is None:
            return
        self._editing_id = lease.id
        self.preview.setPlainText(lease.body)
        self.tenant_edit.setText(lease.tenant_name)
        if lease.property_id is not None:
            index = self.property_combo.findData(lease.property_id)
            if index >= 0:
                self._loading = True
                self.property_combo.setCurrentIndex(index)
                self._loading = False

    def delete_saved(self) -> None:
        lease_id = self.saved_combo.currentData()
        if not lease_id:
            QMessageBox.information(self, "KeKar", "Choose a saved lease first.")
            return
        answer = QMessageBox.question(
            self, "KeKar", "Delete this saved lease?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.app.lease_repo.delete(int(lease_id))
        self._editing_id = None
        self.preview.clear()
        self._reload_saved()
        self.app.main_window.status("Saved lease deleted.")

    def _on_property_changed(self) -> None:
        if self._loading:
            return
        self.landlord_edit.setText(self.app.settings.landlord_name)

    def _selected_property(self):
        prop_id = self.property_combo.currentData()
        if prop_id is None:
            return None
        return self.app.property_repo.get(int(prop_id))

    # -- generation -------------------------------------------------------

    def _fields(self) -> dict[str, str]:
        return lease_builder.tokens_for(
            self._selected_property(),
            tenant=self.tenant_edit.text().strip(),
            landlord=self.landlord_edit.text().strip(),
            term_months=self.term_spin.value(),
        )

    def generate(self) -> None:
        prop = self._selected_property()
        if prop is None:
            QMessageBox.information(
                self, "KeKar", "Add a property first, then generate its lease.")
            return
        if not self.tenant_edit.text().strip():
            QMessageBox.information(
                self, "KeKar", "Enter the tenant's name before generating.")
            return
        body = lease_builder.render(self.template(), self._fields())
        self.preview.setPlainText(body)
        self.app.main_window.status(f"Lease generated for {prop.address}.")

    def copy_lease(self) -> None:
        text = self.preview.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "KeKar", "Generate a lease first.")
            return
        copy_text(text)
        self.app.main_window.status("Lease copied to the clipboard.")

    def print_lease(self) -> None:
        """Send the finished lease to the system print dialog."""
        text = self.preview.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "KeKar", "Generate a lease first.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return
        document = QTextDocument()
        document.setPlainText(text)
        document.print(printer)
        self.app.main_window.status("Lease sent to the printer.")

    def email_lease(self) -> None:
        """Hand the lease to the mail application via a mailto: link.

        KeKar has no SMTP credentials and must not hold any, so it opens the
        user's own mail client with the lease pre-filled rather than sending
        anything itself.
        """
        text = self.preview.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "KeKar", "Generate a lease first.")
            return
        prop = self._selected_property()
        subject = f"Lease agreement — {prop.address if prop else 'your rental'}"
        recipient = self.email_edit.text().strip()
        query = urlencode({"subject": subject, "body": text})
        url = QUrl(f"mailto:{recipient}?{query}" if recipient
                   else f"mailto:?{query}")
        opened = QDesktopServices.openUrl(url)
        if opened:
            if len(text) > MAILTO_SOFT_LIMIT:
                self.app.main_window.status(
                    "Opened your mail app. Some clients truncate a long "
                    "message — check it before sending.")
            else:
                self.app.main_window.status("Opened your mail app with the lease.")
        else:
            QMessageBox.warning(
                self, "KeKar",
                "No mail application could be opened. Copy the lease instead.")

    def save_lease(self) -> None:
        text = self.preview.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "KeKar", "Generate a lease first.")
            return
        prop = self._selected_property()
        lease = Lease(property_id=prop.id if prop else None,
                      tenant_name=self.tenant_edit.text().strip(),
                      body=text)
        if self._editing_id is not None:
            lease.id = self._editing_id
            self.app.lease_repo.update(lease)
        else:
            self._editing_id = self.app.lease_repo.create(lease)
        self.app.main_window.status("Lease saved.")
        self._reload_saved()

    def new_lease(self) -> None:
        self._editing_id = None
        self.preview.clear()

    # -- theme -------------------------------------------------------------

    def apply_theme(self, theme: Theme) -> None:
        self._theme = theme
