from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Property:
    address: str
    city: str | None = None
    zip_code: str | None = None
    rent_price: float | None = None
    deposit_amount: float | None = None
    available_date: str | None = None
    #: ISO dates entered in the property form; the Calendar tab shows them.
    move_in_date: str | None = None
    move_out_date: str | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    pet_policy: str | None = None
    pet_deposit_amount: float | None = None
    status: str = "Vacant"
    amenity_wd: bool = False
    amenity_ac: bool = False
    amenity_yard: bool = False
    amenity_dishwasher: bool = False
    amenity_parking: bool = False
    #: 0 = no garage, 1 or 2 = garage size. Parking type is a separate
    #: street/driveway choice so a listing can say exactly where to park.
    garage_spaces: int = 0
    parking_type: str | None = None
    notes: str | None = None
    #: 'rental' is a long-term let; 'short_stay' is an Airbnb-style unit.
    kind: str = "rental"
    # Short-stay terms. Only meaningful when kind == 'short_stay'.
    nightly_price: float | None = None
    cleaning_fee: float | None = None
    extra_guest_fee: float | None = None
    min_stay_nights: int | None = None
    max_guests: int | None = None
    check_in_time: str | None = None
    check_out_time: str | None = None
    instant_book: bool = False
    cancellation_policy: str | None = None
    house_rules: str | None = None
    id: int | None = None


#: Valid values for ``Property.kind``.
PROPERTY_KINDS = ("rental", "short_stay")

SHORT_STAY_KIND = "short_stay"


@dataclass
class Applicant:
    applicant_name: str
    property_id: int | None = None
    contact_info: str | None = None
    screening_stage: str = "Inquiry Received"
    notes: str | None = None
    id: int | None = None


@dataclass
class Booking:
    """One reserved or blocked stretch of dates on a short-stay property.

    ``external_uid`` is the iCal ``UID`` the portal assigned, so an imported
    event is updated rather than duplicated on the next sync.
    """

    property_id: int | None = None
    portal: str = ""
    guest_name: str = ""
    guest_contact: str | None = None
    check_in: str = ""
    check_out: str = ""
    nights: int | None = None
    payout: float | None = None
    status: str = "confirmed"
    external_uid: str | None = None
    source: str = "manual"
    notes: str | None = None
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


#: Valid ``Booking.status``.
BOOKING_STATUSES = ("confirmed", "cancelled", "blocked", "inquiry")

#: Where a booking came from.
BOOKING_SOURCES = ("manual", "ical")

#: The short-stay portals KeKar knows how to talk to.
PORTALS = ("airbnb", "vrbo", "booking_com")

PORTAL_LABELS = {
    "airbnb": "Airbnb",
    "vrbo": "Vrbo",
    "booking_com": "Booking.com",
}


@dataclass
class PortalSettings:
    """One short-stay portal's settings for one property."""

    property_id: int | None = None
    portal: str = "airbnb"
    enabled: bool = False
    price_override: float | None = None
    min_stay_override: int | None = None
    external_ical_url: str | None = None
    external_listing_url: str | None = None
    last_sync_at: str | None = None
    id: int | None = None


@dataclass
class Lease:
    """A lease drawn up from the client's example template.

    ``body`` is the finished text, not the template: the template lives in the
    settings so one example lease serves every property.
    """

    tenant_name: str = ""
    property_id: int | None = None
    body: str = ""
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
