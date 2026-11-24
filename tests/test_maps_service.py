"""Google Places (New) request/parse tests — no real network is used."""
import io
import json
import urllib.error

import pytest

from src.services import maps_service


class _Response:
    """The small part of an HTTP response the service reads."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _http_error(body, code=429, reason="Too Many Requests"):
    return urllib.error.HTTPError(
        "https://places.googleapis.com/v1/places:autocomplete", code, reason,
        {}, io.BytesIO(json.dumps(body).encode("utf-8")))


@pytest.fixture
def http(monkeypatch):
    """Route urlopen through a handler and record every request."""
    state = {"calls": [], "handler": None}

    def fake(request, timeout=None):
        state["calls"].append((request, timeout))
        return state["handler"](request, timeout)

    monkeypatch.setattr(maps_service.urllib.request, "urlopen", fake)
    return state


def test_autocomplete_posts_and_parses_predictions(http):
    http["handler"] = lambda request, timeout: _Response({
        "suggestions": [
            {"placePrediction": {
                "text": {"text": "10 Main St, Pawhuska, OK 74056"},
                "placeId": "ChIJ-pawhuska"}},
            {"placePrediction": {
                "text": {"text": "20 Oak Ave, Tulsa, OK"},
                "placeId": "ChIJ-tulsa"}},
            {"placePrediction": {
                "text": {"text": ""}, "placeId": "no-description"}},
        ]})

    results = maps_service.autocomplete("maps-key", "10 main")

    assert [(s.description, s.place_id) for s in results] == [
        ("10 Main St, Pawhuska, OK 74056", "ChIJ-pawhuska"),
        ("20 Oak Ave, Tulsa, OK", "ChIJ-tulsa"),
    ]
    request, timeout = http["calls"][0]
    assert request.get_method() == "POST"
    assert json.loads(request.data) == {"input": "10 main",
                                        "languageCode": "en"}
    assert request.get_header("X-goog-api-key") == "maps-key"
    assert request.get_header("Content-type") == "application/json"


def test_autocomplete_without_key_makes_no_request(http):
    def forbidden(request, timeout=None):
        raise AssertionError("a missing key must never reach the network")

    http["handler"] = forbidden

    assert maps_service.autocomplete("", "123 Main St") == []
    assert maps_service.autocomplete("maps-key", "   ") == []
    assert http["calls"] == []


def test_details_parses_address_components(http):
    http["handler"] = lambda request, timeout: _Response({
        "formattedAddress": "10 Main St, Pawhuska, OK 74056, USA",
        "displayName": {"text": "10 Main St"},
        "addressComponents": [
            {"longText": "10", "shortText": "10",
             "types": ["street_number"]},
            {"longText": "Main Street", "shortText": "Main St",
             "types": ["route"]},
            {"longText": "Pawhuska", "shortText": "Pawhuska",
             "types": ["locality", "political"]},
            {"longText": "Oklahoma", "shortText": "OK",
             "types": ["administrative_area_level_1"]},
            {"longText": "74056", "shortText": "74056",
             "types": ["postal_code"]},
        ]})

    details = maps_service.place_details("maps-key", "ChIJ-pawhuska")

    assert details.city == "Pawhuska"
    assert details.postal_code == "74056"
    assert details.state == "Oklahoma"
    assert details.street_address == "10 Main Street"
    assert details.formatted_address.endswith("USA")
    request, timeout = http["calls"][0]
    assert request.get_method() == "GET"
    assert "ChIJ-pawhuska" in request.full_url
    assert "addressComponents,formattedAddress,displayName" in request.full_url
    assert request.get_header("X-goog-api-key") == "maps-key"


def test_http_error_quotes_the_providers_message(http):
    def quota_exceeded(request, timeout=None):
        raise _http_error({"error": {
            "code": 429,
            "message": "You have exceeded your daily request quota.",
            "status": "RESOURCE_EXHAUSTED",
        }})

    http["handler"] = quota_exceeded

    with pytest.raises(maps_service.MapsError) as caught:
        maps_service.autocomplete("maps-key", "123 Main St")

    assert "HTTP 429" in str(caught.value)
    assert "You have exceeded your daily request quota." in str(caught.value)


def test_network_failure_has_a_readable_message(http):
    def offline(request, timeout=None):
        raise urllib.error.URLError("name resolution failed")

    http["handler"] = offline

    with pytest.raises(maps_service.MapsError, match="name resolution failed"):
        maps_service.place_details("maps-key", "place-1")
