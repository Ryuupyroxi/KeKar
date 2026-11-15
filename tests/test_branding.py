"""Branding: the supplied icon and logo are wired into the app."""
import struct
from pathlib import Path

import pytest

from src.paths import icon_path, logo_path, resource_path


def test_icon_file_exists():
    path = icon_path()
    assert path.exists(), f"missing {path}"
    assert path.stat().st_size > 1000


def test_logo_file_exists():
    path = logo_path()
    assert path.exists(), f"missing {path}"
    assert path.stat().st_size > 1000


def test_ico_carries_several_sizes():
    """Windows picks a frame by size; a single-frame .ico scales badly."""
    data = icon_path().read_bytes()
    # ICONDIR: reserved(2) type(2) count(2)
    count = struct.unpack_from("<H", data, 4)[0]
    assert count >= 5, f"expected several frames, found {count}"
    sizes = set()
    for i in range(count):
        width, height = data[6 + i * 16], data[7 + i * 16]
        sizes.add(width or 256)
        sizes.add(height or 256)
    for needed in (16, 32, 48, 128, 256):
        assert needed in sizes, f"no {needed}px frame in the .ico"


def test_hicolor_pngs_exist():
    """Linux launchers look under icons/hicolor/<size>/apps/."""
    for size in (16, 32, 48, 64, 128, 256):
        path = resource_path("icons", f"kekar-{size}.png")
        assert path.exists(), f"missing {path}"


def test_logo_keeps_its_aspect_ratio():
    """Squashing the logo would be visible; the .ico is square, the logo is not."""
    from PIL import Image
    logo = Image.open(logo_path())
    assert logo.width > logo.height
    assert logo.mode == "RGBA"


def test_resource_path_finds_bundled_layout():
    assert resource_path("icons", "kekar-mark.png").exists()


def test_window_icon_is_set(kekar_app):
    assert kekar_app.main_window.windowIcon().isNull() is False


def test_window_header_shows_the_logo(kekar_app):
    label = kekar_app.main_window.logo_label
    assert label is not None
    assert label.pixmap() is not None
    assert label.pixmap().isNull() is False


def test_logo_label_is_not_a_wasteful_band(kekar_app):
    """The strip should be exactly the logo's height, not a tall empty band."""
    label = kekar_app.main_window.logo_label
    assert label.height() <= 64


def test_about_dialog_shows_the_logo(kekar_app):
    from src.ui.main_window import AboutDialog

    dialog = AboutDialog(kekar_app, kekar_app.main_window)
    logos = dialog.findChildren(type(dialog.logo_label))
    assert logos, "About dialog should show the logo"
    assert any(not logo.pixmap().isNull() for logo in logos)


def test_about_dialog_wraps_its_text(kekar_app):
    from PyQt6.QtWidgets import QLabel

    from src.ui.main_window import AboutDialog

    dialog = AboutDialog(kekar_app, kekar_app.main_window)
    labels = dialog.findChildren(QLabel)
    assert any(label.wordWrap() for label in labels), (
        "the About body must wrap, or it runs off the dialog edge")


def test_about_dialog_body_is_not_clipped(kekar_app):
    """The dialog must be tall enough for the word-wrapped body."""
    from PyQt6.QtWidgets import QLabel

    from src.ui.main_window import AboutDialog

    dialog = AboutDialog(kekar_app, kekar_app.main_window)
    dialog.show()
    kekar_app.processEvents()
    body = next(label for label in dialog.findChildren(QLabel)
                if label.wordWrap())
    assert body.height() >= body.sizeHint().height(), (
        "the About body is clipped at the dialog's bottom edge")
    dialog.close()
