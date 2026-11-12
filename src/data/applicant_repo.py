from __future__ import annotations

import sqlite3

from .models import Applicant

STAGES = ("Inquiry Received", "Questionnaire Sent",
          "Background Check", "Approved", "Rejected")

_INSERT = """
INSERT INTO applicants (property_id, applicant_name, contact_info,
                        screening_stage, notes)
VALUES (?, ?, ?, ?, ?)
"""
_UPDATE = """
UPDATE applicants SET property_id=?, applicant_name=?, contact_info=?,
  screening_stage=?, notes=?,
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE id=?
"""


def _row_to_applicant(row: sqlite3.Row) -> Applicant:
    return Applicant(
        id=row["id"], property_id=row["property_id"],
        applicant_name=row["applicant_name"],
        contact_info=row["contact_info"],
        screening_stage=row["screening_stage"], notes=row["notes"],
    )


class ApplicantRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        """A connection owned by the calling thread (see PropertyRepo)."""
        db = self._db
        return db.conn if hasattr(db, "conn") else db

    def create(self, a: Applicant) -> int:
        cur = self.conn.execute(
            _INSERT, (a.property_id, a.applicant_name, a.contact_info,
                      a.screening_stage, a.notes))
        return int(cur.lastrowid)

    def update(self, a: Applicant) -> None:
        if a.id is None:
            raise ValueError("cannot update an applicant without an id")
        self.conn.execute(
            _UPDATE, (a.property_id, a.applicant_name, a.contact_info,
                      a.screening_stage, a.notes, a.id))

    def get(self, applicant_id: int) -> Applicant | None:
        row = self.conn.execute(
            "SELECT * FROM applicants WHERE id=?", (applicant_id,)).fetchone()
        return _row_to_applicant(row) if row else None

    def list(self, property_id: int | None = None,
             stage: str | None = None) -> list[Applicant]:
        sql = "SELECT * FROM applicants WHERE 1=1"
        params: list = []
        if property_id is not None:
            sql += " AND property_id=?"
            params.append(property_id)
        if stage is not None:
            sql += " AND screening_stage=?"
            params.append(stage)
        sql += " ORDER BY created_at DESC"
        return [_row_to_applicant(r) for r in self.conn.execute(sql, params)]

    def set_stage(self, applicant_id: int, stage: str) -> None:
        if stage not in STAGES:
            raise ValueError(f"invalid stage: {stage}")
        self.conn.execute(
            "UPDATE applicants SET screening_stage=?, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (stage, applicant_id))

    def delete(self, applicant_id: int) -> None:
        self.conn.execute("DELETE FROM applicants WHERE id=?", (applicant_id,))

    def add_document(self, applicant_id: int, rel_path: str,
                     kind: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO applicant_docs (applicant_id, rel_path, kind) "
            "VALUES (?, ?, ?)", (applicant_id, rel_path, kind))
        return int(cur.lastrowid)

    def documents(self, applicant_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, rel_path, kind, created_at FROM applicant_docs "
            "WHERE applicant_id=? ORDER BY created_at", (applicant_id,))
        return [dict(r) for r in rows]
