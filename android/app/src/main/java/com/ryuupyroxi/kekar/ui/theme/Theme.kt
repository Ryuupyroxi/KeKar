package com.ryuupyroxi.kekar.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

enum class ThemeMode { SYSTEM, LIGHT, DARK, OLED }

@Composable
fun KeKarTheme(themeMode: ThemeMode, content: @Composable () -> Unit) {
    val mode = if (themeMode == ThemeMode.SYSTEM) {
        if (isSystemInDarkTheme()) ThemeMode.DARK else ThemeMode.LIGHT
    } else themeMode
    val scheme = when (mode) {
        ThemeMode.LIGHT -> lightColorScheme(
            primary = LightColors.primary,
            background = LightColors.background,
            onBackground = LightColors.onBackground,
            surface = LightColors.surface,
            onSurface = LightColors.onSurface)
        ThemeMode.DARK -> darkColorScheme(
            primary = DarkColors.primary,
            background = DarkColors.background,
            onBackground = DarkColors.onBackground,
            surface = DarkColors.surface,
            onSurface = DarkColors.onSurface)
        ThemeMode.OLED, ThemeMode.SYSTEM -> darkColorScheme(
            primary = OledColors.primary,
            background = OledColors.background,
            onBackground = OledColors.onBackground,
            surface = OledColors.surface,
            onSurface = OledColors.onSurface)
    }
    MaterialTheme(colorScheme = scheme, typography = KeKarTypography, content = content)
}
