"""Zillow and apartments.com listing packages."""
import pytest

from src.data.models import Property
from src.services.listing_channels import (CHANNELS, channel_fields,
                                           channel_label, compile_channel,
                                           known_channels)


def _property(**overrides):
    base = dict(address="123 Main Street", city="Springfield", zip_code="62701",
                rent_price=1200.0, deposit_amount=1200.0, bedrooms=2,
                bathrooms=1.0, sqft=900, pet_policy="Cats OK",
                available_date="2026-12-01", status="Vacant",
                amenity_ac=True, notes="Recently renovated.")
    base.update(overrides)
    return Property(**base)


def test_known_channels():
    assert "zillow" in known_channels()
    assert "apartments_com" in known_channels()
    assert set(known_channels()) == set(CHANNELS)


def test_channel_labels():
    assert channel_label("zillow") == "Zillow"
    assert channel_label("apartments_com") == "apartments.com"
    assert channel_label("nope") == "nope"


def test_zillow_package_is_filled():
    pkg = compile_channel(_property(), "zillow")
    assert pkg.label == "Zillow"
    assert "123 Main Street" in pkg.title
    assert "Springfield" in pkg.body
    assert "$1,200" in pkg.body
    assert "Cats OK" in pkg.body
    assert "{" not in pkg.body


def test_apartments_package_carries_a_description_field():
    pkg = compile_channel(_property(), "apartments_com")
    labels = [label for label, _ in pkg.fields]
    assert "Description" in labels
    description = dict(pkg.fields)["Description"]
    assert "123 Main Street" in description
    assert "Monthly rent: $1,200" in description


def test_fields_cover_the_site_form():
    fields = dict(channel_fields(_property(), "zillow"))
    for label in ("Street address", "City", "ZIP", "Monthly rent",
                  "Bedrooms", "Bathrooms", "Square feet",
                  "Security deposit", "Available date", "Pet policy"):
        assert label in fields, f"missing {label}"


def test_unknown_channel_raises():
    with pytest.raises(ValueError):
        compile_channel(_property(), "craigslist")


def test_missing_rent_warns():
    pkg = compile_channel(_property(rent_price=None), "zillow")
    assert any("rent" in w.lower() for w in pkg.warnings)


def test_missing_sqft_warns():
    pkg = compile_channel(_property(sqft=None), "apartments_com")
    assert any("square footage" in w.lower() for w in pkg.warnings)


def test_long_title_warns():
    pkg = compile_channel(_property(address="A very long street name " * 4),
                           "zillow")
    assert any("Title is" in w for w in pkg.warnings)


def test_as_text_includes_title_body_fields_and_warnings():
    pkg = compile_channel(_property(rent_price=None), "zillow")
    text = pkg.as_text()
    assert text.startswith("[Zillow]")
    assert f"Title: {pkg.title}" in text
    assert "Street address: 123 Main Street" in text
    assert "No rent is set" in text


def test_as_text_has_no_substitution_leftovers():
    pkg = compile_channel(_property(), "apartments_com")
    assert "{{" not in pkg.as_text()


def test_dialog_offers_every_channel(kekar_app):
    from src.ui.listing_dialog import ListingDialog

    prop = _property(id=1)
    dialog = ListingDialog(kekar_app, prop)
    labels = [dialog.channel.itemText(i)
              for i in range(dialog.channel.count())]
    assert "Any site (generic)" in labels
    assert "Zillow" in labels
    assert "apartments.com" in labels


def test_dialog_switching_channel_changes_the_preview(kekar_app):
    from src.ui.listing_dialog import ListingDialog

    prop = _property(id=1)
    dialog = ListingDialog(kekar_app, prop)
    dialog.channel.setCurrentIndex(0)
    generic = dialog.text.toPlainText()
    assert generic.startswith("2 bd | 1 ba rental in Springfield")

    zillow_index = dialog.channel.findData("zillow")
    dialog.channel.setCurrentIndex(zillow_index)
    assert dialog.text.toPlainText().startswith("[Zillow]")
    assert dialog.text.toPlainText() != generic


def test_dialog_shows_warnings_for_incomplete_property(kekar_app):
    from src.ui.listing_dialog import ListingDialog

    dialog = ListingDialog(kekar_app, _property(id=1, rent_price=None))
    dialog.channel.setCurrentIndex(dialog.channel.findData("apartments_com"))
    assert "No rent is set" in dialog.problems.text()
