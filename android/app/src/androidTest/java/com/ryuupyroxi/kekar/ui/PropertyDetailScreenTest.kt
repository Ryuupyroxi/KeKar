package com.ryuupyroxi.kekar.ui

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import com.ryuupyroxi.kekar.MainActivity
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test

class PropertyDetailScreenTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    @Test
    fun save_button_is_enabled_after_address_is_entered() {
        compose.onNodeWithText("+").performClick()
        compose.onNodeWithText("Street address").assertExists()
        compose.onNodeWithText("Save property").assertExists()
    }

}
