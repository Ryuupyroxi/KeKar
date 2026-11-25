package com.ryuupyroxi.kekar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import com.ryuupyroxi.kekar.ui.theme.KeKarTheme
import com.ryuupyroxi.kekar.ui.theme.ThemeMode
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            KeKarTheme(ThemeMode.SYSTEM) {
                Text("KeKar", style = MaterialTheme.typography.headlineMedium)
            }
        }
    }
}
