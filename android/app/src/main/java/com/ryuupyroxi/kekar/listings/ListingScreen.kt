package com.ryuupyroxi.kekar.listings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.domain.model.Property

@androidx.compose.material3.ExperimentalMaterial3Api
@Composable
fun ListingScreen(property: Property) {
    var site by remember { mutableStateOf("zillow") }
    var expanded by remember { mutableStateOf(false) }
    val pkg = compileSitePackage(property, site)
    Column(Modifier.padding(16.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
            OutlinedTextField(
                value = SITE_LABELS.getValue(site),
                onValueChange = {},
                readOnly = true,
                label = { Text("Site") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                modifier = Modifier.menuAnchor().fillMaxWidth()
            )
            ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                SITE_KEYS.forEach { key ->
                    DropdownMenuItem(text = { Text(SITE_LABELS.getValue(key)) }, onClick = { site = key; expanded = false })
                }
            }
        }
        Text("Title: ${pkg.title}")
        Text(pkg.body)
        pkg.warnings.forEach { Text(it) }
    }
}
