from __future__ import annotations

import sqlite3

from .models import Lease

_INSERT = """
INSERT INTO leases (property_id, tenant_name, body)
VALUES (?, ?, ?)
"""
_UPDATE = """
UPDATE leases SET property_id=?, tenant_name=?, body=?,
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE id=?
"""


def _row_to_lease(row: sqlite3.Row) -> Lease:
    return Lease(
        id=row["id"], property_id=row["property_id"],
        tenant_name=row["tenant_name"], body=row["body"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


class LeaseRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        """A connection owned by the calling thread (see PropertyRepo)."""
        db = self._db
        return db.conn if hasattr(db, "conn") else db

    def create(self, lease: Lease) -> int:
        cur = self.conn.execute(
            _INSERT, (lease.property_id, lease.tenant_name, lease.body))
        return int(cur.lastrowid)

    def update(self, lease: Lease) -> None:
        if lease.id is None:
            raise ValueError("cannot update a lease without an id")
        self.conn.execute(
            _UPDATE, (lease.property_id, lease.tenant_name, lease.body,
                      lease.id))

    def get(self, lease_id: int) -> Lease | None:
        row = self.conn.execute(
            "SELECT * FROM leases WHERE id=?", (lease_id,)).fetchone()
        return _row_to_lease(row) if row else None

    def list(self, property_id: int | None = None) -> list[Lease]:
        sql = "SELECT * FROM leases WHERE 1=1"
        params: list = []
        if property_id is not None:
            sql += " AND property_id=?"
            params.append(property_id)
        sql += " ORDER BY created_at DESC, id DESC"
        return [_row_to_lease(r) for r in self.conn.execute(sql, params)]

    def delete(self, lease_id: int) -> None:
        self.conn.execute("DELETE FROM leases WHERE id=?", (lease_id,))
