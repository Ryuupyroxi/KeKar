"""Single source of truth for the KeKar version.

The CLI --version flag, the About dialog and the Windows installer all read
from here, so they cannot drift apart.
"""

APP_NAME = "KeKar"
APP_VERSION = "1.6.1"

LITE_APP_NAME = "KeKar Lite"


def display_name() -> str:
    """The product name shown to users; the internal APP_NAME never changes."""
    from . import features
    return LITE_APP_NAME if features.is_lite() else APP_NAME

