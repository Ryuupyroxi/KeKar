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
   {{city}}, {{zip}} (the "Premises").

2. TERM. The lease runs for {{term}} months from the move-in date, ending on
   the move-out date recorded for the Premises. Any renewal must be agreed in
   writing.

3. RENT. Tenant pays ${{rent}} per month, due on the first day of each month.
   Rent is payable in full and without deduction unless agreed in writing.

4. SECURITY DEPOSIT. Tenant pays a security deposit of ${{deposit}} before
   move-in. The deposit may be applied to unpaid rent or damage beyond fair
   wear and tear, and the remaining balance will be returned after move-out
   in accordance with applicable law.

5. OCCUPANCY. The Premises have {{bedrooms}} bedroom(s) and {{bathrooms}}
   bathroom(s){{sqft_clause}}. The Premises are for residential use by Tenant
   and the occupants agreed in writing only.

6. PETS. Pet policy: {{pet_policy}}{{pet_clause}}. Pets are subject to the
   agreed policy and Tenant remains responsible for their care and damage.

7. UTILITIES AND FEES. Tenant is responsible for utilities and other
   recurring charges for the Premises unless the parties agree otherwise in
   writing.

8. MAINTENANCE AND REPAIRS. Tenant will keep the Premises reasonably clean
   and notify Landlord promptly of needed repairs. Tenant will not make
   alterations without Landlord's written consent.

9. LANDLORD ACCESS. Landlord may enter the Premises to inspect, maintain or
   repair them after reasonable notice to Tenant, except in an emergency.

10. CONDITION. The Premises are rented as at {{available_date}}, in good
    repair, and Tenant will return them in the same condition, fair wear and
    tear excepted.

11. ASSIGNMENT AND SUBLETTING. Tenant may not assign this lease or sublet the
    Premises without Landlord's written consent.

12. DEFAULT. Failure to pay rent or to follow a material term of this lease is
    a default. The parties will use the notice and cure process required by
    applicable law before termination for default.

13. TERMINATION. Either party may terminate this lease as provided by law or
    by written agreement. Tenant will give written notice and return all keys
    on move-out.

14. ENTIRE AGREEMENT. This document is the entire agreement between the
    parties about the Premises and supersedes earlier discussions. Changes
    must be in writing and signed by both parties.

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


def _pet_deposit(prop: Property) -> float:
    return prop.pet_deposit_amount or PET_DEPOSIT_AMOUNT


def _pet_clause(prop: Property) -> str:
    if not _pets_allowed(prop):
        return ""
    return (f" Tenant shall pay a refundable pet deposit of "
            f"${money(_pet_deposit(prop))} before move-in.")


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
        "pet_deposit": (money(_pet_deposit(prop))
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
