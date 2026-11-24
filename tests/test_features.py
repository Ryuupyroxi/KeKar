"""Build variant switch: full stays complete, Lite hides direct connections."""
import src.features as features


def test_full_variant_is_the_default(monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    assert features.variant() == "full"
    assert features.is_lite() is False
    assert features.chat_enabled() is True
    assert features.marketplace_enabled() is True
    assert features.portal_sync_enabled() is True


def test_unknown_variant_falls_back_to_full(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "experimental")
    assert features.variant() == "full"


def test_lite_disables_only_the_three_direct_connections(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    assert features.variant() == "lite"
    assert features.is_lite() is True
    assert features.chat_enabled() is True
    assert features.marketplace_enabled() is False
    assert features.portal_sync_enabled() is False


def test_lite_hides_only_the_named_site_channels(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    channels = ["generic", "zillow", "apartments_com", "airbnb", "vrbo",
                "booking_com"]
    assert features.visible_channels(channels) == [
        "generic", "zillow", "booking_com"]


def test_full_keeps_every_channel(monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    channels = ["generic", "zillow", "apartments_com", "airbnb", "vrbo",
                "booking_com"]
    assert features.visible_channels(channels) == channels


def test_lite_disables_google_maps_suggestions(monkeypatch):
    monkeypatch.setenv("KEKAR_VARIANT", "lite")
    assert features.maps_enabled() is False


def test_full_keeps_google_maps_suggestions(monkeypatch):
    monkeypatch.delenv("KEKAR_VARIANT", raising=False)
    assert features.maps_enabled() is True
