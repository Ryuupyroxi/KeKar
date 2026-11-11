"""Applicant tracking table with screening stages and quick templates."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ..data.applicant_repo import STAGES
from ..services.clipboard import copy_text
from .theme import font

PRE_SCREENING_QUESTIONS = """Thanks for your interest! Please reply with:
1. Desired move-in date
2. Total number of occupants (and names)
3. Pets (type, breed, weight) or "no pets"
4. Smoking? (yes/no)
5. Monthly household income and employer
6. Do you authorize a background and credit check?
"""

# Colour per screening stage, so the pipeline reads at a glance.
STAGE_COLORS = {
    "Inquiry Received": "#8a8f98",
    "Questionnaire Sent": "#3f7fbf",
    "Background Check": "#b07a2a",
    "Approved": "#2e7d32",
    "Rejected": "#c62828",
}


class CrmTab(QWidget):
    applicant_selected = pyqtSignal(int)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        layout = QVBoxLayout(self)

        actions = QHBoxLayout()
        add_btn = QPushButton("Add applicant")
        add_btn.clicked.connect(self.add_applicant)
        questions_btn = QPushButton("Copy pre-screening questions")
        questions_btn.clicked.connect(self.copy_questions)
        self.remove_btn = QPushButton("Remove selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        actions.addWidget(add_btn)
        actions.addWidget(questions_btn)
        actions.addStretch(1)
        actions.addWidget(self.remove_btn)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Property", "Contact", "Stage", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def reload(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        props = {p.id: p for p in self.app.property_repo.list()}
        for applicant in self.app.applicant_repo.list():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0,
                               QTableWidgetItem(applicant.applicant_name))
            prop = props.get(applicant.property_id)
            self.table.setItem(row, 1, QTableWidgetItem(
                prop.address if prop else ""))
            self.table.setItem(row, 2, QTableWidgetItem(
                applicant.contact_info or ""))
            stage = QComboBox()
            stage.addItems(STAGES)
            stage.setCurrentText(applicant.screening_stage)
            stage.setProperty("row", row)
            stage.currentTextChanged.connect(self._on_stage_changed)
            self.table.setCellWidget(row, 3, stage)
            self.table.setItem(row, 4, QTableWidgetItem(applicant.notes or ""))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole,
                                            applicant.id)
            self._tint_stage(row, applicant.screening_stage)
        self.table.blockSignals(False)

    def _tint_stage(self, row: int, stage: str) -> None:
        """Colour the stage cell so the pipeline reads at a glance."""
        color = QColor(STAGE_COLORS.get(stage, "#8a8f98"))
        for column in range(self.table.columnCount()):
            item = self.table.item(row, column)
            if item is not None:
                item.setForeground(color)

    def add_applicant(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        from ..data.models import Applicant

        properties = self.app.property_repo.list()
        options = ["(no property)"] + [p.address for p in properties]
        choice, ok = QInputDialog.getItem(
            self, "Add applicant", "Which property?", options, 0, False)
        if not ok:
            return
        property_id = None
        if choice != "(no property)":
            property_id = properties[options.index(choice) - 1].id
        self.app.applicant_repo.create(Applicant(
            applicant_name="New applicant", property_id=property_id))
        self.reload()

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "KeKar", "Choose an applicant first.")
            return
        item = self.table.item(row, 0)
        applicant_id = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()
        answer = QMessageBox.question(
            self, "KeKar", f"Remove {name} from the applicant list?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.app.applicant_repo.delete(applicant_id)
        self.reload()
        self.app.main_window.status(f"Removed {name}.")

    def copy_questions(self) -> None:
        copy_text(PRE_SCREENING_QUESTIONS)
        self.app.main_window.status("Pre-screening questions copied.")

    def _on_stage_changed(self, text: str) -> None:
        combo = self.sender()
        row = combo.property("row")
        applicant_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.app.applicant_repo.set_stage(applicant_id, text)
        self._tint_stage(row, text)
        self.app.main_window.status(f"Stage updated to {text}.")

    def _on_cell_changed(self, row: int, column: int) -> None:
        if column not in (0, 2, 4):
            return
        applicant_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        applicant = self.app.applicant_repo.get(applicant_id)
        if applicant is None:
            return
        applicant.applicant_name = self.table.item(row, 0).text()
        applicant.contact_info = self.table.item(row, 2).text()
        applicant.notes = self.table.item(row, 4).text()
        self.app.applicant_repo.update(applicant)
