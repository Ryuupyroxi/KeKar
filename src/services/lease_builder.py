"""Turn a client-supplied example lease into a filled-in lease.

The example is a plain-text template. ``{{token}}`` markers are replaced with
values from the selected property and the tenant details; everything else is
copied verbatim. Markers are simple string substitutions — nothing is executed
or interpreted — and unknown markers are left in place so a template is never
silently mangled.
"""
from __future__ import annotations

import re
from datetime import date

from ..data.models import Property

TOKEN_RE = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}")

#: Refundable pet deposit used when a property allows pets. A client can edit
#: the marker text in their own template; this is the fill value.
PET_DEPOSIT_AMOUNT = 300.0
_NO_PETS = {"no", "none", "no pet", "no pets"}

#: Markers this module knows how to fill. Anything else in a template is left
#: alone on purpose.
TOKEN_NAMES = (
    "address", "city", "zip", "rent", "deposit", "bedrooms", "bathrooms",
    "sqft", "sqft_clause", "available_date", "pet_policy", "pet_deposit",
    "pet_clause", "status", "tenant", "landlord", "date", "term",
)

DEFAULT_TEMPLATE = """RESIDENTIAL LEASE AGREEMENT

This lease is made on {{date}} between {{landlord}} ("Landlord") and
{{tenant}} ("Tenant").

1. PROPERTY. Landlord rents to Tenant the premises at {{address}},
   {{city}}, {{zip}}.

2. TERM. The lease runs for {{term}} months from the move-in date.

3. RENT. Tenant pays ${{rent}} per month, due on the first day of each month.

4. SECURITY DEPOSIT. Tenant pays a security deposit of ${{deposit}} before
   move-in.

5. OCCUPANCY. The premises have {{bedrooms}} bedroom(s) and {{bathrooms}}
   bathroom(s){{sqft_clause}}.

6. PETS. Pet policy: {{pet_policy}}{{pet_clause}}.

7. CONDITION. The premises are rented as at {{available_date}}, in good
   repair, and Tenant will keep them clean and return them in the same
   condition, fair wear and tear excepted.

Signed: ________________________   Landlord

Signed: ________________________   Tenant
"""


def money(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:,.2f}"


def _pets_allowed(prop: Property) -> bool:
    policy = (prop.pet_policy or "").strip().lower()
    return bool(policy) and policy not in _NO_PETS


def _pet_clause(prop: Property) -> str:
    if not _pets_allowed(prop):
        return ""
    return (f" Tenant shall pay a refundable pet deposit of "
            f"${money(PET_DEPOSIT_AMOUNT)} before move-in.")


def _sqft_clause(prop: Property) -> str:
    if prop.sqft:
        return f", approximately {prop.sqft:,} square feet"
    return ""


def tokens_for(prop: Property | None, tenant: str = "",
               landlord: str = "", lease_date: str | None = None,
               term_months: int = 12) -> dict[str, str]:
    """The fill values for one property and one tenant."""
    return {
        "address": prop.address if prop else "",
        "city": prop.city or "" if prop else "",
        "zip": prop.zip_code or "" if prop else "",
        "rent": money(prop.rent_price) if prop else "",
        "deposit": money(prop.deposit_amount) if prop else "",
        "bedrooms": "" if not prop or prop.bedrooms is None
                    else str(prop.bedrooms),
        "bathrooms": "" if not prop or prop.bathrooms is None
                     else str(prop.bathrooms),
        "sqft": "" if not prop or prop.sqft is None else f"{prop.sqft:,}",
        "sqft_clause": _sqft_clause(prop) if prop else "",
        "available_date": prop.available_date if prop else "",
        "pet_policy": prop.pet_policy or "No pets" if prop else "",
        "pet_deposit": (money(PET_DEPOSIT_AMOUNT)
                        if prop and _pets_allowed(prop) else "0.00"),
        "pet_clause": _pet_clause(prop) if prop else "",
        "status": prop.status if prop else "",
        "tenant": tenant,
        "landlord": landlord,
        "date": lease_date or date.today().isoformat(),
        "term": str(term_months),
    }


def render(template: str, fields: dict[str, str]) -> str:
    """Substitute every known marker; leave unknown ones untouched."""
    return TOKEN_RE.sub(lambda m: fields.get(m.group(1), m.group(0)),
                        template)


def unknown_tokens(template: str) -> list[str]:
    """Markers present in the template that this module cannot fill.

    Surfaced in the UI so a client's own markers are not mistaken for a
    broken template.
    """
    seen: list[str] = []
    for match in TOKEN_RE.finditer(template):
        name = match.group(1)
        if name not in TOKEN_NAMES and name not in seen:
            seen.append(name)
    return seen
