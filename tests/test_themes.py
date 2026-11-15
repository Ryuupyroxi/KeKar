"""Themes: palettes, contrast, resolution, and switching."""
import pytest

from src.config.settings import Settings
from src.ui.palette import (CHOICES, DARK, LIGHT, OLED, THEMES, contrast,
                            is_valid, required_pairs, resolve, text_on)
from src.ui.theme import build_stylesheet


def test_themes_are_registered_and_valid():
    assert set(THEMES) == {"light", "dark", "oled"}
    assert CHOICES == ("system", "light", "dark", "oled")
    for key in CHOICES:
        assert is_valid(key)
    assert not is_valid("sepia")


def test_system_resolves_to_a_real_palette():
    assert resolve("system") in (LIGHT, DARK)


def test_explicit_choices_resolve():
    assert resolve("light") is LIGHT
    assert resolve("dark") is DARK
    assert resolve("oled") is OLED


def test_unknown_theme_falls_back_to_light():
    """A corrupted settings file must not stop the app from starting."""
    assert resolve("sepia") is LIGHT
    assert resolve("") is LIGHT


def test_oled_window_is_pure_black():
    assert OLED.window == "#000000"
    assert OLED.input_bg == "#000000"


@pytest.mark.parametrize("theme", [LIGHT, DARK, OLED])
def test_every_palette_passes_contrast_requirements(theme):
    for label, foreground, background, minimum in required_pairs(theme):
        ratio = contrast(foreground, background)
        assert ratio >= minimum, (
            f"{theme.name}: {label} is {ratio:.2f}, needs {minimum}")


@pytest.mark.parametrize("theme", [LIGHT, DARK, OLED])
def test_status_labels_are_readable(theme):
    for role in ("online", "offline", "vacant", "rented"):
        colour = getattr(theme, role)
        assert contrast(text_on(colour), colour) >= 4.5


def test_stylesheet_carries_the_palette_colours():
    sheet = build_stylesheet(DARK)
    assert DARK.window in sheet
    assert DARK.accent in sheet
    assert DARK.on_accent in sheet
    assert "#f5f4f1" not in sheet, "light palette leaked into the dark sheet"


def test_settings_defaults_to_system():
    assert Settings().theme == "system"


def test_theme_switching_updates_every_custom_widget(kekar_app):
    window = kekar_app.main_window
    dark = kekar_app.apply_theme("dark")
    assert kekar_app.current_theme() is dark
    assert kekar_app.settings.theme == "dark"

    light = kekar_app.apply_theme("light")
    assert kekar_app.current_theme() is light
    assert kekar_app.settings.theme == "light"


def test_view_menu_ticks_the_stored_theme(kekar_app):
    window = kekar_app.main_window
    kekar_app.apply_theme("oled")
    assert window._theme_actions["oled"].isChecked() is True
    assert window._theme_actions["light"].isChecked() is False

    kekar_app.apply_theme("system")
    assert window._theme_actions["system"].isChecked() is True


def test_property_rows_repaint_in_the_new_palette(kekar_app):
    """The rows paint themselves, so they must read the new palette."""
    from src.data.models import Property
    from src.ui import property_drawer

    kekar_app.property_repo.create(Property(address="1 Theme Way"))
    kekar_app.main_window.reload_all()

    kekar_app.apply_theme("dark")
    assert property_drawer._current_theme is DARK

    kekar_app.apply_theme("light")
    assert property_drawer._current_theme is LIGHT
