import json
from pathlib import Path

import pytest

from src.data.models import Property
from src.services.browser import marketplace


class FakeCDP:
    def __init__(self):
        self.filled = {}
        self.uploaded = []
        self.clicked = []

    async def navigate(self, url):
        return True

    async def fill(self, selector, value):
        self.filled[selector] = value
        return True

    async def click(self, selector):
        self.clicked.append(selector)
        return True

    async def upload_files(self, selector, files):
        self.uploaded.extend(files)
        return True


def _prop():
    return Property(id=1, address="1 Market Way", city="Pawhuska",
                    zip_code="74056", rent_price=850.0, bedrooms=3,
                    bathrooms=2.0, sqft=1200, amenity_ac=True)


def _selectors():
    return json.loads(Path("config/marketplace_selectors.json").read_text())


async def test_autofill_fills_fields_and_stops(monkeypatch, tmp_path):
    selectors = _selectors()
    cdp = FakeCDP()
    monkeypatch.setattr(marketplace.image_service, "property_photos",
                        lambda pid: [tmp_path / "a.jpg"])
    result = await marketplace.MarketplaceAutomation(
        cdp, selectors).autofill_listing(_prop())
    assert result["status"] == "autofilled"
    assert cdp.filled[selectors["title"]]
    assert cdp.filled[selectors["price"]] == "850"
    assert selectors["publish"] not in cdp.clicked


async def test_missing_selector_reports_needs_review(monkeypatch, tmp_path):
    selectors = {"listing_url": "https://example.test/new",
                 "title": "#missing", "price": "#missing",
                 "description": "#missing", "photos": "#missing",
                 "publish": "#publish"}
    cdp = FakeCDP()

    async def _fail_fill(selector, value):
        return False

    cdp.fill = _fail_fill
    monkeypatch.setattr(marketplace.image_service, "property_photos",
                        lambda pid: [])
    result = await marketplace.MarketplaceAutomation(
        cdp, selectors).autofill_listing(_prop())
    assert result["status"] == "needs_review"


def test_selectors_are_versioned():
    assert _selectors()["selector_schema_version"] == \
        marketplace.SELECTOR_SCHEMA_VERSION


def test_missing_selector_file_falls_back_to_embedded(tmp_path):
    missing = tmp_path / "absent.json"
    selectors = marketplace.load_selectors(missing)
    assert selectors["listing_url"].startswith("https://")
    assert selectors["title"]


def test_malformed_selector_file_falls_back_to_embedded(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    selectors = marketplace.load_selectors(bad)
    assert selectors == marketplace.DEFAULT_SELECTORS


def test_embedded_fallback_keeps_publish_selector():
    """The safety-critical Publish selector must exist even in fallback."""
    assert "Publish" in marketplace.DEFAULT_SELECTORS["publish"]


def test_autofill_never_clicks_publish_even_when_selector_matches():
    """Defence in depth: the flow never issues a click on the Publish control."""
    src = Path(marketplace.__file__).read_text(encoding="utf-8")
    body = src.split("async def autofill_listing")[1]
    assert "self.cdp.click" not in body

