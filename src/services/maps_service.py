"""Google Maps address suggestions for the property form (Places API, New).

Only the two calls KeKar actually needs are implemented, with stdlib ``urllib``
so the frozen USB build gains no dependency:

* ``autocomplete`` — POST ``places:autocomplete`` for a list of predictions.
* ``place_details`` — GET ``places/{id}`` for the address components used to
  fill City and ZIP when the user picks a suggestion.

An empty key is a normal "feature off" state, never an error: it returns no
suggestions and makes no request. HTTP failures raise :class:`MapsError`
carrying the provider's own message, so "quota exhausted" is not reported as
"no internet".
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
DETAILS_FIELDS = "addressComponents,formattedAddress,displayName"


class MapsError(RuntimeError):
    """A Google Maps request failed; the message is shown to the user."""


@dataclass(frozen=True)
class Suggestion:
    description: str
    place_id: str


@dataclass(frozen=True)
class PlaceDetails:
    formatted_address: str = ""
    display_name: str = ""
    street_number: str = ""
    route: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""

    @property
    def street_address(self) -> str:
        """The number and street, without city/state/ZIP."""
        return " ".join(part for part in (self.street_number, self.route)
                        if part).strip()


def _http_error(exc: urllib.error.HTTPError) -> str:
    """Quote the provider's ``error.message`` when it supplies one."""
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    message = ""
    if body:
        try:
            payload = json.loads(body)
        except ValueError:
            message = body.strip()[:300]
        else:
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    message = error.get("message", "") or ""
                message = message or payload.get("message", "") or ""
    if not message:
        message = str(exc.reason or exc)
    return f"HTTP {exc.code} — {message}"


def _request(url: str, api_key: str, payload: dict | None = None,
             timeout: int = 10) -> dict:
    headers = {"X-Goog-Api-Key": api_key}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise MapsError(_http_error(exc)) from exc
    except urllib.error.URLError as exc:
        raise MapsError(f"Google Maps could not be reached: {exc.reason}") \
            from exc
    try:
        parsed = json.loads(body)
    except ValueError as exc:
        raise MapsError("Google Maps returned an unreadable response.") \
            from exc
    if not isinstance(parsed, dict):
        raise MapsError("Google Maps returned an unexpected response.")
    return parsed


def autocomplete(api_key: str, text: str, timeout: int = 10) -> list[Suggestion]:
    """Return place predictions for typed text; no key means no request."""
    text = text.strip()
    if not api_key or not text:
        return []
    data = _request(AUTOCOMPLETE_URL, api_key,
                    payload={"input": text, "languageCode": "en"},
                    timeout=timeout)
    suggestions: list[Suggestion] = []
    for item in data.get("suggestions", []):
        if not isinstance(item, dict):
            continue
        prediction = item.get("placePrediction") or {}
        if not isinstance(prediction, dict):
            continue
        text_obj = prediction.get("text") or {}
        description = text_obj.get("text", "") if isinstance(text_obj, dict) \
            else ""
        place_id = prediction.get("placeId", "")
        if description and place_id:
            suggestions.append(Suggestion(description, place_id))
    return suggestions


def place_details(api_key: str, place_id: str,
                  timeout: int = 10) -> PlaceDetails:
    """Fetch the address components for one prediction."""
    if not api_key or not place_id:
        raise MapsError("A Google Maps key and a place are required.")
    quoted = urllib.parse.quote(place_id, safe="")
    url = (DETAILS_URL.format(place_id=quoted)
           + "?fields=" + urllib.parse.quote(DETAILS_FIELDS, safe=","))
    data = _request(url, api_key, timeout=timeout)
    components: dict[str, str] = {}
    raw_components = data.get("addressComponents", [])
    if isinstance(raw_components, list):
        for component in raw_components:
            if not isinstance(component, dict):
                continue
            value = component.get("longText") or component.get("shortText") \
                or ""
            for kind in component.get("types", []) or []:
                if kind not in components:
                    components[kind] = value
    name = data.get("displayName") or {}
    return PlaceDetails(
        formatted_address=data.get("formattedAddress", "") or "",
        display_name=name.get("text", "") if isinstance(name, dict) else "",
        street_number=components.get("street_number", ""),
        route=components.get("route", ""),
        city=components.get("locality", ""),
        state=components.get("administrative_area_level_1", ""),
        postal_code=components.get("postal_code", ""),
    )
