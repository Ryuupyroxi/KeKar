"""Sample data for demo mode.

Seeded into the demo database only. Never touches the user's real database.
"""
from __future__ import annotations

from .applicant_repo import ApplicantRepo
from .models import Applicant, Property
from .property_repo import PropertyRepo

PROPERTIES = [
    Property(address="123 Main Street", city="Springfield", zip_code="62701",
             rent_price=1200.0, deposit_amount=1200.0, bedrooms=2,
             bathrooms=1.0, sqft=900, status="Vacant",
             amenity_wd=True, amenity_ac=True),
    Property(address="456 Oak Avenue", city="Springfield", zip_code="62704",
             rent_price=950.0, deposit_amount=950.0, bedrooms=1,
             bathrooms=1.0, sqft=650, status="Rented",
             amenity_parking=True),
    Property(address="789 Elm Lane", city="Shelbyville", zip_code="62565",
             rent_price=1450.0, deposit_amount=1450.0, bedrooms=3,
             bathrooms=2.0, sqft=1400, status="Vacant",
             amenity_yard=True, amenity_dishwasher=True),
    Property(address="321 Pine Court", city="Capital City", zip_code="62707",
             rent_price=2100.0, deposit_amount=2100.0, bedrooms=4,
             bathrooms=2.5, sqft=2000, status="Rented",
             amenity_wd=True, amenity_ac=True, amenity_yard=True,
             amenity_dishwasher=True, amenity_parking=True),
]

# (name, property address, contact, stage) — the address is resolved to the
# id the property got when it was inserted, so the seed never guesses at ids.
APPLICANTS = [
    ("John Doe", "123 Main Street", "555-0101", "Inquiry Received"),
    ("Jane Smith", "456 Oak Avenue", "555-0102", "Background Check"),
    ("Bob Johnson", "789 Elm Lane", "555-0103", "Approved"),
    ("Alice Brown", "321 Pine Court", "555-0104", "Rejected"),
]


def seed_if_empty(db) -> bool:
    """Populate an empty demo database. Returns True if it seeded.

    Idempotent: an existing property means the demo is already set up.
    """
    properties = PropertyRepo(db)
    applicants = ApplicantRepo(db)
    if properties.list():
        return False

    ids = {prop.address: properties.create(prop) for prop in PROPERTIES}
    for name, address, contact, stage in APPLICANTS:
        applicants.create(Applicant(
            applicant_name=name, property_id=ids[address],
            contact_info=contact, screening_stage=stage))
    return True
