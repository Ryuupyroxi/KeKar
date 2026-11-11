from src.data.models import Property
from src.services.listing_compiler import (amenities_line, compile_listing,
                                           listing_title, validate_listing)


def _prop(**kw):
    base = dict(address="123 Main St", city="Pawhuska", zip_code="74056",
                rent_price=850.0, deposit_amount=850.0,
                available_date="2026-12-01", bedrooms=3, bathrooms=2.0,
                sqft=1200, pet_policy="Cats OK", status="Vacant",
                amenity_wd=True, amenity_ac=True, amenity_yard=True,
                amenity_dishwasher=False, amenity_parking=True,
                notes="Quiet street, close to schools.")
    base.update(kw)
    return Property(**base)


def test_title_contains_key_facts():
    t = listing_title(_prop())
    assert "3" in t and "Pawhuska" in t


def test_amenities_line_lists_only_enabled():
    line = amenities_line(_prop())
    assert "Washer" in line
    assert "Dishwasher" not in line
    assert "Fenced yard" in line


def test_compile_contains_all_sections():
    text = compile_listing(_prop())
    for needle in ("123 Main St", "$850", "74056", "Washer",
                   "Quiet street", "Cats OK"):
        assert needle in text


def test_compile_handles_missing_optionals():
    text = compile_listing(_prop(sqft=None, notes=None, pet_policy=None))
    assert "bd |" in text
    assert validate_listing(text) == []


def test_validate_flags_missing_rent():
    problems = validate_listing("no price here")
    assert problems
