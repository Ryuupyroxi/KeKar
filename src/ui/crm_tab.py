"""Applicant tracking table with screening stages and quick templates."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ..data.applicant_repo import STAGES
from ..services.clipboard import copy_text

PRE_SCREENING_QUESTIONS = """Thanks for your interest! Please reply with:
1. Desired move-in date
2. Total number of occupants (and names)
3. Pets (type, breed, weight) or "no pets"
4. Smoking? (yes/no)
5. Monthly household income and employer
6. Do you authorize a background and credit check?
"""


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
        actions.addWidget(add_btn)
        actions.addWidget(questions_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Property", "Contact", "Stage", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch)
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table)

    def reload(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        props = {p.id: p for p in self.app.property_repo.list()}
        for a in self.app.applicant_repo.list():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(a.applicant_name))
            prop = props.get(a.property_id)
            self.table.setItem(row, 1, QTableWidgetItem(
                prop.address if prop else ""))
            self.table.setItem(row, 2, QTableWidgetItem(a.contact_info or ""))
            stage = QComboBox()
            stage.addItems(STAGES)
            stage.setCurrentText(a.screening_stage)
            stage.setProperty("row", row)
            stage.currentTextChanged.connect(self._on_stage_changed)
            self.table.setCellWidget(row, 3, stage)
            self.table.setItem(row, 4, QTableWidgetItem(a.notes or ""))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, a.id)
        self.table.blockSignals(False)

    def add_applicant(self) -> None:
        from ..data.models import Applicant
        self.app.applicant_repo.create(Applicant(applicant_name="New applicant"))
        self.reload()

    def copy_questions(self) -> None:
        copy_text(PRE_SCREENING_QUESTIONS)
        self.app.main_window.status("Pre-screening questions copied.")

    def _on_stage_changed(self, text: str) -> None:
        combo = self.sender()
        row = combo.property("row")
        aid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.app.applicant_repo.set_stage(aid, text)
        self.app.main_window.status(f"Stage updated to {text}.")

    def _on_cell_changed(self, row: int, column: int) -> None:
        if column not in (0, 2, 4):
            return
        aid = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        applicant = self.app.applicant_repo.get(aid)
        if applicant is None:
            return
        applicant.applicant_name = self.table.item(row, 0).text()
        applicant.contact_info = self.table.item(row, 2).text()
        applicant.notes = self.table.item(row, 4).text()
        self.app.applicant_repo.update(applicant)
