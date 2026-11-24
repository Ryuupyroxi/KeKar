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
    from src.ui.main_window import HEADER_LOGO_HEIGHT

    label = kekar_app.main_window.logo_label
    assert label.height() <= HEADER_LOGO_HEIGHT
    assert abs(label.height() - label.pixmap().height()) <= 1


def test_header_logo_is_enlarged_and_centred(kekar_app):
    """The wordmark keeps its readable size while its strip stays tight.

    A small wordmark tucked into the left corner left the full-width header
    reading as dead space; inflating the strip to the source file's 96 px did
    the same thing in a different way.
    """
    from src.ui.main_window import HEADER_LOGO_HEIGHT

    window = kekar_app.main_window
    label = window.logo_label
    pix = label.pixmap()
    assert pix.isNull() is False
    assert pix.height() >= 36, "the wordmark must keep its visible size"
    assert pix.width() >= 100
    assert pix.height() == HEADER_LOGO_HEIGHT
    assert pix.width() > pix.height(), "the logo is a wide lockup"

    window.show()
    kekar_app.processEvents()
    try:
        content = window.centralWidget()
        # Compare on-screen positions so the outer layout's margins count.
        logo_centre = label.mapToGlobal(label.rect().center()).x()
        content_centre = content.mapToGlobal(content.rect().center()).x()
        offset = abs(logo_centre - content_centre)
        assert offset <= 2, f"header logo is {offset}px off centre"
    finally:
        window.hide()


def test_header_logo_trims_transparent_padding(kekar_app):
    """The header fits the visible mark, not the PNG's empty canvas."""
    from PIL import Image

    from src.ui.main_window import HEADER_LOGO_HEIGHT

    with Image.open(logo_path()) as image:
        bbox = image.getchannel("A").getbbox()
    assert bbox is not None, "the logo must have visible pixels"
    left, top, right, bottom = bbox
    expected_ratio = (right - left) / (bottom - top)

    label = kekar_app.main_window.logo_label
    pix = label.pixmap()
    assert abs(pix.width() / pix.height() - expected_ratio) < 0.05, (
        "the header must use the wordmark's own aspect ratio")
    assert label.height() <= 48, "the strip must hug the visible logo"


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
