"""Tests for the versioned listing template loader."""
import json

from src.data.models import Property
from src.services import listing_compiler
from src.services.listing_compiler import (compile_listing, get_template,
                                           list_templates, load_templates,
                                           reset_templates)


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


def teardown_function():
    reset_templates()


def test_default_template_is_used_when_unconfigured():
    reset_templates()
    assert compile_listing(_prop()).startswith("3 bd | 2 ba rental in Pawhuska")


def test_load_templates_reads_bundled_file():
    templates = load_templates()
    assert "default" in templates
    assert "short" in templates
    assert "{address}" in templates["default"]


def test_get_template_by_name():
    assert get_template("short").startswith("{title}")


def test_get_template_unknown_name_falls_back_to_default():
    assert get_template("does-not-exist") == get_template("default")


def test_compile_with_named_template_is_shorter():
    long_text = compile_listing(_prop(), template=get_template("default"))
    short_text = compile_listing(_prop(), template=get_template("short"))
    assert len(short_text) < len(long_text)
    assert "123 Main St" in short_text


def test_list_templates_returns_sorted_names():
    assert list_templates() == sorted(list_templates())


def test_bundled_templates_file_is_valid_json():
    from src.services.listing_compiler import default_templates_path
    data = json.loads(default_templates_path().read_text(encoding="utf-8"))
    assert data["schema_version"]
    assert isinstance(data["templates"], dict)


def test_compiler_survives_a_missing_templates_file(tmp_path, monkeypatch):
    """A missing or broken file must never break listing generation."""
    monkeypatch.setattr(listing_compiler, "default_templates_path",
                        lambda: tmp_path / "nope.json")
    reset_templates()
    text = compile_listing(_prop())
    assert "123 Main St" in text


def test_compiler_survives_malformed_templates_file(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(listing_compiler, "default_templates_path",
                        lambda: bad)
    reset_templates()
    text = compile_listing(_prop())
    assert "123 Main St" in text
