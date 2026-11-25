package com.ryuupyroxi.kekar.ui.theme

import androidx.compose.ui.graphics.Color
import com.google.common.truth.Truth.assertThat
import org.junit.Test

class ThemeTokensTest {
    @Test
    fun oled_has_pure_black_background_and_light_text() {
        assertThat(OledColors.background).isEqualTo(Color(0xFF000000))
        assertThat(OledColors.onBackground).isEqualTo(Color(0xFFE8E6E1))
    }

    @Test
    fun accent_is_amber_in_all_themes() {
        assertThat(LightColors.primary).isEqualTo(Color(0xFFC8892A))
        assertThat(DarkColors.primary).isEqualTo(Color(0xFFC8892A))
        assertThat(OledColors.primary).isEqualTo(Color(0xFFC8892A))
    }
}
