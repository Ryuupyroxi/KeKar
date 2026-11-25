from __future__ import annotations

import sqlite3

from .models import Property

COLUMNS = [
    "id", "address", "city", "zip_code", "rent_price", "deposit_amount",
    "available_date",    "bedrooms", "bathrooms", "sqft", "pet_policy", "pet_deposit_amount",
    "status",
    "kind", "amenity_wd", "amenity_ac", "amenity_yard", "amenity_dishwasher",
    "amenity_parking", "notes", "nightly_price", "cleaning_fee",
    "extra_guest_fee", "min_stay_nights", "max_guests", "check_in_time",
    "check_out_time", "instant_book", "cancellation_policy", "house_rules",
    "move_in_date", "move_out_date", "garage_spaces", "parking_type",
]

_INSERT = """
INSERT INTO properties
 (address, city, zip_code, rent_price, deposit_amount, available_date,
  bedrooms, bathrooms, sqft, pet_policy, pet_deposit_amount, status, kind,
  amenity_wd, amenity_ac, amenity_yard, amenity_dishwasher, amenity_parking, notes,
  nightly_price, cleaning_fee, extra_guest_fee, min_stay_nights, max_guests,
  check_in_time, check_out_time, instant_book, cancellation_policy, house_rules,
  move_in_date, move_out_date, garage_spaces, parking_type)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE = """
UPDATE properties SET
  address=?, city=?, zip_code=?, rent_price=?, deposit_amount=?,
  available_date=?, bedrooms=?, bathrooms=?, sqft=?, pet_policy=?,
  pet_deposit_amount=?, status=?,
  kind=?, amenity_wd=?, amenity_ac=?, amenity_yard=?, amenity_dishwasher=?,
  amenity_parking=?, notes=?, nightly_price=?, cleaning_fee=?,
  extra_guest_fee=?, min_stay_nights=?, max_guests=?, check_in_time=?,
  check_out_time=?, instant_book=?, cancellation_policy=?, house_rules=?,
  move_in_date=?, move_out_date=?, garage_spaces=?, parking_type=?,
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
        pet_policy=row["pet_policy"],
        pet_deposit_amount=row["pet_deposit_amount"], status=row["status"],
        kind=row["kind"],
        amenity_wd=bool(row["amenity_wd"]), amenity_ac=bool(row["amenity_ac"]),
        amenity_yard=bool(row["amenity_yard"]),
        amenity_dishwasher=bool(row["amenity_dishwasher"]),
        amenity_parking=bool(row["amenity_parking"]), notes=row["notes"],
        nightly_price=row["nightly_price"], cleaning_fee=row["cleaning_fee"],
        extra_guest_fee=row["extra_guest_fee"],
        min_stay_nights=row["min_stay_nights"], max_guests=row["max_guests"],
        check_in_time=row["check_in_time"],
        check_out_time=row["check_out_time"],
        instant_book=bool(row["instant_book"]),
        cancellation_policy=row["cancellation_policy"],
        house_rules=row["house_rules"],
        move_in_date=row["move_in_date"],
        move_out_date=row["move_out_date"],
        garage_spaces=row["garage_spaces"] or 0,
        parking_type=row["parking_type"],
    )


class PropertyRepo:
    def __init__(self, db):
        self._db = db

    @property
    def conn(self) -> sqlite3.Connection:
        """A connection owned by the calling thread.

        ``db`` is normally a Database, which hands each thread its own
        connection — SQLite requires that, and the agent's tools run in a
        worker thread. A raw connection is also accepted, which is what the
        tests and one-off scripts pass.
        """
        db = self._db
        return db.conn if hasattr(db, "conn") else db

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

    def list(self, status: str | None = None,
             kind: str | None = None) -> list[Property]:
        sql = f"SELECT {', '.join(COLUMNS)} FROM properties"
        clauses: list[str] = []
        params: list = []
        if status:
            clauses.append("status=?")
            params.append(status)
        if kind:
            clauses.append("kind=?")
            params.append(kind)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
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
        p.pet_deposit_amount, p.status, p.kind, int(p.amenity_wd), int(p.amenity_ac),
        int(p.amenity_yard), int(p.amenity_dishwasher), int(p.amenity_parking),
        p.notes, p.nightly_price, p.cleaning_fee, p.extra_guest_fee,
        p.min_stay_nights, p.max_guests, p.check_in_time, p.check_out_time,
        int(p.instant_book), p.cancellation_policy, p.house_rules,
        p.move_in_date, p.move_out_date, p.garage_spaces, p.parking_type,
    ]
