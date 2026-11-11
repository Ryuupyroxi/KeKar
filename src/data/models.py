from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Property:
    address: str
    city: str | None = None
    zip_code: str | None = None
    rent_price: float | None = None
    deposit_amount: float | None = None
    available_date: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    pet_policy: str | None = None
    status: str = "Vacant"
    amenity_wd: bool = False
    amenity_ac: bool = False
    amenity_yard: bool = False
    amenity_dishwasher: bool = False
    amenity_parking: bool = False
    notes: str | None = None
    id: int | None = None


@dataclass
class Applicant:
    applicant_name: str
    property_id: int | None = None
    contact_info: str | None = None
    screening_stage: str = "Inquiry Received"
    notes: str | None = None
    id: int | None = None
