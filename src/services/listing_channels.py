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
        "kind": "rental",
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
        "kind": "rental",
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
    "airbnb": {
        "label": "Airbnb",
        "kind": "short_stay",
        "title_template": "${nightly}/night in {city} · {address}",
        "max_title": 50,
        "body_template": (
            "{title}\n\n"
            "{address}, {city}, {zip}\n\n"
            "${nightly}/night | Cleaning fee ${cleaning_fee}\n"
            "{min_stay} night minimum | Up to {guests} guests\n"
            "Check-in {check_in} | Check-out {check_out}\n"
            "Instant Book: {instant_book}\n"
            "Cancellation: {cancellation}\n\n"
            "{amenities}\n\n"
            "{pet_line}\n\n"
            "{house_rules}\n\n"
            "{notes}"
        ),
    },
    "vrbo": {
        "label": "Vrbo",
        "kind": "short_stay",
        "title_template": "{address} - ${nightly}/night, sleeps {guests}",
        "max_title": 75,
        "body_template": (
            "{title}\n\n"
            "{address}, {city}, {zip}\n\n"
            "Nightly rate: ${nightly}\n"
            "Cleaning fee: ${cleaning_fee}\n"
            "Extra guest fee: ${extra_guest_fee}\n"
            "Minimum stay: {min_stay} nights\n"
            "Sleeps: {guests}\n"
            "Check-in: {check_in} | Check-out: {check_out}\n\n"
            "{amenities}\n\n"
            "{house_rules}\n\n"
            "{notes}"
        ),
    },
    "booking_com": {
        "label": "Booking.com",
        "kind": "short_stay",
        "title_template": "{address} - ${nightly} per night in {city}",
        "max_title": 60,
        "body_template": (
            "{title}\n\n"
            "{address}, {city}, {zip}\n\n"
            "Price per night: ${nightly}\n"
            "Cleaning fee: ${cleaning_fee}\n"
            "Minimum stay: {min_stay} nights\n"
            "Max guests: {guests}\n"
            "Check-in: {check_in} | Check-out: {check_out}\n"
            "Cancellation policy: {cancellation}\n\n"
            "{amenities}\n\n"
            "{house_rules}\n\n"
            "{notes}"
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
    "airbnb": [
        "Airbnb has no posting API, so this is a copy-and-paste package; "
        "posting stays with you.",
        "Airbnb titles are short — the preview warns when this one runs long.",
    ],
    "vrbo": [
        "Vrbo has no posting API; copy the package into the owner dashboard.",
        "Vrbo shows the cleaning fee separately from the nightly rate — both "
        "are in the field list below.",
    ],
    "booking_com": [
        "Booking.com has no public posting API for an independent host; copy "
        "the package into the extranet.",
        "Booking.com asks for the minimum stay and occupancy per rate plan — "
        "they are in the field list below.",
    ],
}


def _substitute(template: str, prop: Property, *,
                nightly: float | None = None,
                min_stay_nights: int | None = None) -> str:
    """Fill one template.

    ``nightly`` / ``min_stay_nights`` are the *effective* values for this
    package: a portal's override when it sets one, otherwise the property's
    own. ``None`` means "use the property's value".
    """
    rate = prop.nightly_price if nightly is None else nightly
    stay = prop.min_stay_nights if min_stay_nights is None else min_stay_nights
    pet_line = (f"Pet policy: {prop.pet_policy}" if prop.pet_policy else "")
    house_rules = f"House rules: {prop.house_rules}" if prop.house_rules else ""
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
        nightly=_money(rate),
        cleaning_fee=_money(prop.cleaning_fee),
        extra_guest_fee=_money(prop.extra_guest_fee),
        min_stay=(str(stay) if stay is not None
                  else "Contact for minimum stay"),
        guests=(str(prop.max_guests)
                if prop.max_guests is not None else "Contact for occupancy"),
        check_in=prop.check_in_time or "Contact for check-in",
        check_out=prop.check_out_time or "Contact for check-out",
        instant_book="on" if prop.instant_book else "off",
        cancellation=prop.cancellation_policy or "Contact for policy",
        house_rules=house_rules,
    )


def _common_fields(prop: Property, kind: str, *,
                   nightly: float | None = None,
                   min_stay_nights: int | None = None) -> list[tuple[str, str]]:
    """The individual fields a site's form asks for, one at a time."""
    if kind == "short_stay":
        rate = prop.nightly_price if nightly is None else nightly
        stay = prop.min_stay_nights if min_stay_nights is None \
            else min_stay_nights
        return [
            ("Street address", prop.address),
            ("City", prop.city or ""),
            ("ZIP", prop.zip_code or ""),
            ("Nightly rate", _money(rate)),
            ("Cleaning fee", _money(prop.cleaning_fee)),
            ("Extra guest fee", _money(prop.extra_guest_fee)),
            ("Minimum stay (nights)", str(stay) if stay else ""),
            ("Max guests", str(prop.max_guests) if prop.max_guests else ""),
            ("Check-in time", prop.check_in_time or ""),
            ("Check-out time", prop.check_out_time or ""),
            ("Cancellation policy", prop.cancellation_policy or ""),
            ("House rules", prop.house_rules or ""),
        ]
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


def compile_channel(prop: Property, channel: str, *,
                    price_override: float | None = None,
                    min_stay_override: int | None = None) -> ChannelListing:
    """Build the package for one channel.

    ``price_override`` / ``min_stay_override`` are the per-portal settings
    from the Portals group: 0 or None means "no override", so the property's
    own nightly rate and minimum stay are used.
    """
    config = CHANNELS.get(channel)
    if config is None:
        raise ValueError(f"unknown channel: {channel}")

    rate = price_override or prop.nightly_price
    stay = min_stay_override or prop.min_stay_nights
    title = _substitute(config["title_template"], prop, nightly=rate,
                         min_stay_nights=stay).strip()
    body = _substitute(config["body_template"], prop, nightly=rate,
                       min_stay_nights=stay).strip()

    fields = _common_fields(prop, config["kind"], nightly=rate,
                            min_stay_nights=stay)
    if channel == "apartments_com":
        fields = fields + [("Description", body)]

    warnings: list[str] = []
    if len(title) > config["max_title"]:
        warnings.append(
            f"Title is {len(title)} characters; {config['label']} shows about "
            f"{config['max_title']}.")
    if config["kind"] == "short_stay":
        if not rate:
            warnings.append("No nightly rate is set, so the price is missing.")
        if not prop.max_guests:
            warnings.append("No maximum occupancy is set.")
        if not stay:
            warnings.append("No minimum stay is set.")
    else:
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


def known_channels(kind: str | None = None) -> list[str]:
    """Channel keys, optionally limited to one property kind."""
    return sorted(key for key, config in CHANNELS.items()
                  if kind is None or config.get("kind") == kind)


def channel_kind(channel: str) -> str | None:
    """The property kind a channel belongs to, or None for a generic package."""
    return CHANNELS.get(channel, {}).get("kind")


def channel_label(channel: str) -> str:
    return CHANNELS.get(channel, {}).get("label", channel)
