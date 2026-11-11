from __future__ import annotations

import sqlite3

from .models import Property

COLUMNS = [
    "id", "address", "city", "zip_code", "rent_price", "deposit_amount",
    "available_date", "bedrooms", "bathrooms", "sqft", "pet_policy", "status",
    "amenity_wd", "amenity_ac", "amenity_yard", "amenity_dishwasher",
    "amenity_parking", "notes",
]

_INSERT = """
INSERT INTO properties
 (address, city, zip_code, rent_price, deposit_amount, available_date,
  bedrooms, bathrooms, sqft, pet_policy, status,
  amenity_wd, amenity_ac, amenity_yard, amenity_dishwasher, amenity_parking, notes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE = """
UPDATE properties SET
  address=?, city=?, zip_code=?, rent_price=?, deposit_amount=?,
  available_date=?, bedrooms=?, bathrooms=?, sqft=?, pet_policy=?, status=?,
  amenity_wd=?, amenity_ac=?, amenity_yard=?, amenity_dishwasher=?,
  amenity_parking=?, notes=?,
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE id=?
"""


def _row_to_property(row: sqlite3.Row) -> Property:
    return Property(
        id=row["id"], address=row["address"], city=row["city"],
        zip_code=row["zip_code"], rent_price=row["rent_price"],
        deposit_amount=row["deposit_amount"],
        available_date=row["available_date"], bedrooms=row["bedrooms"],
        bathrooms=row["bathrooms"], sqft=row["sqft"],
        pet_policy=row["pet_policy"], status=row["status"],
        amenity_wd=bool(row["amenity_wd"]), amenity_ac=bool(row["amenity_ac"]),
        amenity_yard=bool(row["amenity_yard"]),
        amenity_dishwasher=bool(row["amenity_dishwasher"]),
        amenity_parking=bool(row["amenity_parking"]), notes=row["notes"],
    )


class PropertyRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, p: Property) -> int:
        cur = self.conn.execute(_INSERT, _values(p))
        return int(cur.lastrowid)

    def update(self, p: Property) -> None:
        if p.id is None:
            raise ValueError("cannot update a property without an id")
        self.conn.execute(_UPDATE, _values(p) + [p.id])

    def get(self, property_id: int) -> Property | None:
        row = self.conn.execute(
            f"SELECT {', '.join(COLUMNS)} FROM properties WHERE id=?",
            (property_id,)).fetchone()
        return _row_to_property(row) if row else None

    def list(self, status: str | None = None) -> list[Property]:
        sql = f"SELECT {', '.join(COLUMNS)} FROM properties"
        params: list = []
        if status:
            sql += " WHERE status=?"
            params.append(status)
        sql += " ORDER BY status='Vacant' DESC, address COLLATE NOCASE"
        return [_row_to_property(r) for r in self.conn.execute(sql, params)]

    def set_status(self, property_id: int, status: str) -> None:
        if status not in ("Vacant", "Rented"):
            raise ValueError(f"invalid status: {status}")
        self.conn.execute(
            "UPDATE properties SET status=?, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (status, property_id))

    def delete(self, property_id: int) -> None:
        self.conn.execute("DELETE FROM properties WHERE id=?", (property_id,))


def _values(p: Property) -> list:
    return [
        p.address, p.city, p.zip_code, p.rent_price, p.deposit_amount,
        p.available_date, p.bedrooms, p.bathrooms, p.sqft, p.pet_policy,
        p.status, int(p.amenity_wd), int(p.amenity_ac), int(p.amenity_yard),
        int(p.amenity_dishwasher), int(p.amenity_parking), p.notes,
    ]
