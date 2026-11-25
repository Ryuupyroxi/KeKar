package com.ryuupyroxi.kekar.ui.property

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.domain.model.Property

@Composable
fun PropertyListScreen(properties: List<Property>, onAdd: () -> Unit) {
    Scaffold(floatingActionButton = { FloatingActionButton(onClick = onAdd) { Text("+") } }) { pad ->
        LazyColumn(Modifier.padding(pad).padding(16.dp).fillMaxSize()) {
            items(properties) { property ->
                Text(property.address)
            }
        }
    }
}
