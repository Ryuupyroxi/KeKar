import pytest

pytest.importorskip("PyQt6")
from PyQt6.QtWidgets import QApplication

from src.data.models import Property
from src.services.clipboard import copy_listing, copy_text


def test_copy_text_roundtrip(kekar_app):
    assert copy_text("hello kekar") is True
    assert QApplication.clipboard().text() == "hello kekar"


def test_copy_listing_returns_text(kekar_app):
    prop = Property(address="1 Clipboard Way", city="Pawhuska",
                    zip_code="74056", rent_price=800.0, bedrooms=2,
                    bathrooms=1.0, sqft=900)
    text = copy_listing(prop)
    assert "1 Clipboard Way" in text
    assert QApplication.clipboard().text() == text
