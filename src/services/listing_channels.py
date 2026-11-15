"""Channel-specific listing packages for Zillow and apartments.com.

Neither Zillow nor apartments.com offers a public API for creating a rental
listing, and both sit behind a logged-in session with anti-automation, so this
module does not attempt to post. It produces a package shaped the way each
site's form is shaped — a title, a body, and the individual fields the site
asks for separately — so the user pastes once per field instead of retyping.

The generic compiler in ``listing_compiler`` stays the fallback for any other
site.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..data.models import Property
from .listing_compiler import (amenities_line, listing_title, _bathrooms,
                               _money)


@dataclass
class ChannelListing:
    channel: str
    label: str
    title: str
    body: str
    #: (field label, value) pairs for sites that want them one at a time.
    fields: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        """The whole package as one block, for a single copy."""
        lines = [f"[{self.label}]", "", f"Title: {self.title}", "", self.body]
        if self.fields:
            lines += ["", "Fields:"]
            lines += [f"  {label}: {value}" for label, value in self.fields]
        if self.warnings:
            lines += ["", "Before you post:"] + [f"  - {w}" for w in self.warnings]
        return "\n".join(lines).strip()


#: Human names and the title conventions each site expects.
CHANNELS = {
    "zillow": {
        "label": "Zillow",
        "title_template": "{beds} bd {baths} ba in {city} | {address}",
        "max_title": 60,
        "body_template": (
            "{address}, {city}, {zip}\n"
            "${rent}/month\n"
            "{bedrooms} bd | {bathrooms} ba | {sqft} sqft\n"
            "Available {available_date}\n"
            "Security deposit: ${deposit}\n\n"
            "{amenities}\n\n"
            "{pet_line}\n\n"
            "{notes}\n\n"
            "Application required. Equal Housing Opportunity."
        ),
    },
    "apartments_com": {
        "label": "apartments.com",
        "title_template": "{bedrooms} bd {bathrooms} ba rental in {city}",
        "max_title": 80,
        "body_template": (
            "{title}\n\n"
            "{address}, {city}, {zip}\n"
            "Monthly rent: ${rent}\n"
            "Bedrooms: {bedrooms} | Bathrooms: {bathrooms} | Square feet: {sqft}\n"
            "Available: {available_date}\n"
            "Security deposit: ${deposit}\n\n"
            "{amenities}\n\n"
            "{pet_line}\n\n"
            "{notes}\n\n"
            "Message me to schedule a showing. Application required. "
            "Equal Housing Opportunity."
        ),
    },
}

#: What the user must check by hand before posting, per site.
SITE_NOTES = {
    "zillow": [
        "Zillow posts through Rental Manager; the address field may reformat "
        "the street name.",
        "Zillow requires its own application flow, so the 'Application "
        "required' line is kept.",
    ],
    "apartments_com": [
        "apartments.com limits the description length; trim the body if the "
        "preview warns it is too long.",
        "apartments.com asks for the deposit and availability separately — "
        "they are in the field list below.",
    ],
}


def _substitute(template: str, prop: Property) -> str:
    pet_line = (f"Pet policy: {prop.pet_policy}" if prop.pet_policy else "")
    return template.format(
        title=listing_title(prop),
        bedrooms=prop.bedrooms if prop.bedrooms is not None else "Studio",
        beds=prop.bedrooms if prop.bedrooms is not None else "Studio",
        bathrooms=_bathrooms(prop.bathrooms),
        baths=_bathrooms(prop.bathrooms),
        sqft=prop.sqft if prop.sqft is not None else "Contact for size",
        address=prop.address,
        city=prop.city or "",
        zip=prop.zip_code or "",
        zip_code=prop.zip_code or "",
        rent=_money(prop.rent_price),
        deposit=_money(prop.deposit_amount),
        available_date=prop.available_date or "Contact for date",
        amenities=amenities_line(prop),
        pet_line=pet_line,
        notes=prop.notes or "",
    )


def _common_fields(prop: Property) -> list[tuple[str, str]]:
    beds = (str(prop.bedrooms) if prop.bedrooms is not None else "Studio")
    return [
        ("Street address", prop.address),
        ("City", prop.city or ""),
        ("ZIP", prop.zip_code or ""),
        ("Monthly rent", _money(prop.rent_price)),
        ("Bedrooms", beds),
        ("Bathrooms", _bathrooms(prop.bathrooms)),
        ("Square feet", str(prop.sqft) if prop.sqft else ""),
        ("Security deposit", _money(prop.deposit_amount)),
        ("Available date", prop.available_date or ""),
        ("Pet policy", prop.pet_policy or ""),
    ]


def compile_channel(prop: Property, channel: str) -> ChannelListing:
    """Build the package for one channel."""
    config = CHANNELS.get(channel)
    if config is None:
        raise ValueError(f"unknown channel: {channel}")

    title = _substitute(config["title_template"], prop).strip()
    body = _substitute(config["body_template"], prop).strip()

    fields = _common_fields(prop)
    if channel == "apartments_com":
        fields = fields + [("Description", body)]

    warnings: list[str] = []
    if len(title) > config["max_title"]:
        warnings.append(
            f"Title is {len(title)} characters; {config['label']} shows about "
            f"{config['max_title']}.")
    if not prop.rent_price:
        warnings.append("No rent is set, so the price is missing.")
    if not prop.sqft:
        warnings.append("No square footage is set.")
    warnings.extend(SITE_NOTES.get(channel, []))

    return ChannelListing(
        channel=channel, label=config["label"], title=title, body=body,
        fields=fields, warnings=warnings)


def channel_fields(prop: Property, channel: str) -> list[tuple[str, str]]:
    """The individual fields the site's form asks for, one at a time."""
    return compile_channel(prop, channel).fields


def known_channels() -> list[str]:
    return sorted(CHANNELS)


def channel_label(channel: str) -> str:
    return CHANNELS.get(channel, {}).get("label", channel)
