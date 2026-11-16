"""Deterministic, offline listing copy generator.

This runs with no network and no AI. The AI assistant can optionally rewrite
the copy later, but the core generator must always work offline.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ..data.models import Property, SHORT_STAY_KIND

AMENITY_LABELS = [
    ("amenity_wd", "Washer & dryer in unit"),
    ("amenity_ac", "Central AC & heat"),
    ("amenity_yard", "Fenced yard"),
    ("amenity_dishwasher", "Dishwasher"),
    ("amenity_parking", "Parking spot"),
]

DEFAULT_TEMPLATE = """{title}

{bedrooms} bd | {bathrooms} ba | {sqft} sqft
{address}, {city}, OK {zip_code}
${rent}/month  |  Security deposit ${deposit}
Available {available_date}

{amenities}

{pet_line}

{notes}

{footer}"""

#: Generic copy for an Airbnb-style unit. The portal channels have their own
#: templates; this is what "Any site (generic)" shows for a short stay.
SHORT_STAY_TEMPLATE = """{title}

{bedrooms} bd | {bathrooms} ba | {sqft} sqft
{address}, {city}, OK {zip_code}
${nightly}/night  |  Cleaning fee ${cleaning_fee}
{min_stay} night minimum  |  Up to {guests} guests
Check-in {check_in}  |  Check-out {check_out}

{amenities}

{pet_line}

{house_rules}

{notes}

{footer}"""

SHORT_STAY_FOOTER = "Message me to book."

FOOTER = ("Message me for a showing. Application required. "
          "Equal Housing Opportunity.")

TEMPLATE_SCHEMA_VERSION = "2026-11-11"

_TEMPLATE_CACHE: dict | None = None


def default_templates_path() -> Path:
    """Locate config/listing_templates.json in dev and inside a bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS",
                            Path(sys.executable).resolve().parent))
        bundled = base / "config" / "listing_templates.json"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parents[2] / "config" / \
        "listing_templates.json"


def load_templates(path: Path | None = None) -> dict:
    """Read the versioned template file. Falls back to DEFAULT_TEMPLATE.

    A missing or malformed file must never stop listing generation, so every
    failure mode returns the built-in default rather than raising.
    """
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is not None:
        return _TEMPLATE_CACHE
    try:
        data = json.loads((path or default_templates_path())
                          .read_text(encoding="utf-8"))
        templates = data["templates"]
        if isinstance(templates, dict) and templates.get("default"):
            _TEMPLATE_CACHE = templates
            return _TEMPLATE_CACHE
    except (OSError, ValueError, KeyError, TypeError):
        pass
    _TEMPLATE_CACHE = {"default": DEFAULT_TEMPLATE}
    return _TEMPLATE_CACHE


def reset_templates() -> None:
    """Drop the cached templates (used by tests)."""
    global _TEMPLATE_CACHE
    _TEMPLATE_CACHE = None


def get_template(name: str | None = None) -> str:
    templates = load_templates()
    if name and name in templates:
        return templates[name]
    return templates["default"]


def list_templates() -> list[str]:
    return sorted(load_templates())


def listing_title(prop: Property) -> str:
    beds = f"{prop.bedrooms} bd" if prop.bedrooms is not None else "Studio"
    baths = f"{_bathrooms(prop.bathrooms)} ba" if prop.bathrooms is not None else ""
    city = prop.city or "Pawhuska"
    if prop.kind == SHORT_STAY_KIND:
        parts = [p for p in (beds, baths) if p]
        prefix = f"{' | '.join(parts)} " if parts else ""
        return f"${_money(prop.nightly_price)}/night | {prefix}{prop.address}"
    parts = [p for p in (beds, baths) if p]
    return f"{' | '.join(parts)} rental in {city} - {prop.address}"


def amenities_line(prop: Property) -> str:
    active = [label for attr, label in AMENITY_LABELS if getattr(prop, attr)]
    return "Amenities: " + (", ".join(active) if active else "None listed")


def _money(value: float | None) -> str:
    if value is None:
        return "Contact for pricing"
    return f"{value:,.0f}"


def _bathrooms(value: float | None) -> str:
    if value is None:
        return "?"
    return f"{value:g}"


def compile_listing(prop: Property, template: str | None = None) -> str:
    short_stay = prop.kind == SHORT_STAY_KIND
    tmpl: str
    if template is not None:
        tmpl = template
    elif short_stay:
        tmpl = load_templates().get("short_stay") or SHORT_STAY_TEMPLATE
    else:
        tmpl = get_template("default")
    pet_line = f"Pet policy: {prop.pet_policy}" if prop.pet_policy else ""
    house_rules = f"House rules: {prop.house_rules}" if prop.house_rules else ""
    text = tmpl_format(
        tmpl,
        title=listing_title(prop),
        bedrooms=prop.bedrooms if prop.bedrooms is not None else "Studio",
        bathrooms=_bathrooms(prop.bathrooms),
        sqft=prop.sqft if prop.sqft is not None else "N/A",
        address=prop.address,
        city=prop.city or "",
        zip_code=prop.zip_code or "",
        rent=_money(prop.rent_price),
        deposit=_money(prop.deposit_amount),
        available_date=prop.available_date or "Contact for date",
        amenities=amenities_line(prop),
        pet_line=pet_line,
        house_rules=house_rules,
        notes=prop.notes or "",
        nightly=_money(prop.nightly_price),
        cleaning_fee=_money(prop.cleaning_fee),
        min_stay=(str(prop.min_stay_nights)
                  if prop.min_stay_nights is not None
                  else "Contact for minimum stay"),
        guests=(str(prop.max_guests)
                if prop.max_guests is not None else "Contact for occupancy"),
        check_in=prop.check_in_time or "Contact for check-in",
        check_out=prop.check_out_time or "Contact for check-out",
        footer=SHORT_STAY_FOOTER if short_stay else FOOTER,
    )
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def tmpl_format(template: str, **values: object) -> str:
    """``str.format`` that leaves unknown markers alone.

    The user-editable template file may still carry a rental marker, and a
    portal template may carry one this property kind does not use. An unknown
    key raises ``KeyError`` from ``format`` and would stop listing generation
    entirely, so the template is rendered with a mapping that returns the key
    in braces.
    """
    return template.format_map(_DefaultDict(values))


class _DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def validate_listing(text: str) -> list[str]:
    problems: list[str] = []
    if not re.search(r"\$\s?\d", text):
        problems.append("Listing has no price.")
    if not re.search(r"\d+\s*bd", text):
        problems.append("Listing has no bedroom count.")
    if len(text) < 80:
        problems.append("Listing is very short.")
    return problems
