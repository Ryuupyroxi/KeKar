"""Build variant and feature switches for KeKar / KeKar Lite.

One source tree ships two products. A frozen build carries a generated
``src/_variant.py`` stamp (written by ``tools/set_variant.py``); a source
checkout and the test suite use ``KEKAR_VARIANT``. Anything else resolves to
``full``, so a plain checkout keeps every KeKar feature.

The switch controls composition only. Data, schema and settings are identical
in both variants.
"""
from __future__ import annotations

import os

FULL = "full"
LITE = "lite"
VALID_VARIANTS = (FULL, LITE)

# Channel keys hidden from the Lite picker. The copy/paste mechanism itself is
# never disabled: compile_channel() still accepts every key in both builds.
# Listing packages are offline copy/paste text, so every site stays visible
# in Lite. Direct connections (portal sync, Marketplace autofill, Maps) remain
# disabled; those are separate feature flags below.
LITE_HIDDEN_CHANNELS = frozenset()


def _stamped_variant() -> str | None:
    """The value baked into a frozen build, if one was generated."""
    try:
        from ._variant import VARIANT  # generated; gitignored
    except ImportError:
        return None
    return VARIANT if VARIANT in VALID_VARIANTS else None


def variant() -> str:
    """The active build variant: ``full`` (default) or ``lite``."""
    env = os.environ.get("KEKAR_VARIANT", "").strip().lower()
    if env in VALID_VARIANTS:
        return env
    return _stamped_variant() or FULL


def is_lite() -> bool:
    return variant() == LITE


def chat_enabled() -> bool:
    """The AI assistant is available in both builds when a key is configured.

    Lite still hides the direct portal, Marketplace and Maps connections; the
    assistant is an opt-in by virtue of needing a key, not a build difference.
    """
    return True


def marketplace_enabled() -> bool:
    """Facebook Marketplace autofill opens a browser over CDP."""
    return not is_lite()


def portal_sync_enabled() -> bool:
    """'Sync now' fetches a portal's iCal URL over the network."""
    return not is_lite()


def maps_enabled() -> bool:
    """Google Places address lookup is another outbound connection (K11)."""
    return not is_lite()


def visible_channels(all_channels: list[str]) -> list[str]:
    """Channel keys the current build offers in the listing picker."""
    if not is_lite():
        return list(all_channels)
    return [key for key in all_channels if key not in LITE_HIDDEN_CHANNELS]
