package com.ryuupyroxi.kekar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.ryuupyroxi.kekar.ui.navigation.KeKarNavHost
import com.ryuupyroxi.kekar.ui.theme.KeKarTheme
import com.ryuupyroxi.kekar.ui.theme.ThemeMode
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            KeKarTheme(ThemeMode.SYSTEM) { KeKarNavHost() }
        }
    }
}
