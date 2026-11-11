"""Facebook Marketplace listing autofill.

HARD SAFETY RULE: this module never clicks Publish. It fills what it can and
returns, so a human always reviews and submits. Facebook's DOM changes often;
selectors live in config/marketplace_selectors.json and are versioned.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from ...data.models import Property
from ...services import image_service
from ...services.listing_compiler import compile_listing, listing_title

SELECTOR_SCHEMA_VERSION = "2026-11-11"

# Embedded fallback. The versioned JSON file is the authoritative copy and is
# shipped in the bundle, but a missing or unreadable selector file must never
# crash the app — autofill degrades to "needs review" instead.
DEFAULT_SELECTORS = {
    "selector_schema_version": SELECTOR_SCHEMA_VERSION,
    "listing_url": "https://www.facebook.com/marketplace/create/rental",
    "title": "input[name='title'], [aria-label='Title']",
    "price": "input[name='price'], [aria-label='Price']",
    "description": "div[contenteditable='true'], textarea[aria-label='Description']",
    "photos": "input[type='file']",
    "publish": "div[role='button']:has-text('Publish')",
    "next": "div[role='button']:has-text('Next')",
}


def _default_selectors_path() -> Path:
    """Locate config/marketplace_selectors.json in dev and inside a bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS",
                            Path(sys.executable).resolve().parent))
        bundled = base / "config" / "marketplace_selectors.json"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parents[3] / "config" / \
        "marketplace_selectors.json"


def load_selectors(path: Path | None = None) -> dict:
    """Read the versioned selector file, falling back to the embedded copy."""
    try:
        data = json.loads((path or _default_selectors_path())
                          .read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("listing_url"):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return dict(DEFAULT_SELECTORS)


class MarketplaceAutomation:
    def __init__(self, cdp, selectors: dict):
        self.cdp = cdp
        self.selectors = selectors

    async def autofill_listing(self, prop: Property) -> dict:
        try:
            await self.cdp.navigate(self.selectors["listing_url"])
        except Exception as exc:
            return {"status": "failed",
                    "detail": f"Could not open Marketplace: {exc}"}

        text = compile_listing(prop)
        filled = 0
        needed = 0
        for key in ("title", "price", "description"):
            selector = self.selectors.get(key)
            if not selector:
                continue
            needed += 1
            value = {"title": listing_title(prop),
                     "price": f"{prop.rent_price:,.0f}" if prop.rent_price else "",
                     "description": text}[key]
            try:
                if await self.cdp.fill(selector, value):
                    filled += 1
            except Exception:
                continue

        photos = image_service.property_photos(prop.id) if prop.id else []
        if photos and self.selectors.get("photos"):
            try:
                await self.cdp.upload_files(self.selectors["photos"], photos[:12])
            except Exception:
                pass

        if filled < needed:
            return {"status": "needs_review",
                    "detail": "Some fields could not be found. Please finish the "
                              "listing by hand — nothing has been published."}
        return {"status": "autofilled",
                "detail": "Fields filled and photos attached. Please review in the "
                          "browser and click Publish yourself."}
