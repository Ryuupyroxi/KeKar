package com.ryuupyroxi.kekar.ui.property

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.domain.model.Property
import com.ryuupyroxi.kekar.ui.common.SpaciousCard
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PropertyDetailScreen(
    propertyId: Long?,
    onSaved: (Long) -> Unit,
    saveProperty: suspend (Property) -> Long
) {
    val scope = rememberCoroutineScope()
    var address by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("") }
    var zip by remember { mutableStateOf("") }
    var rent by remember { mutableStateOf("") }
    var petPolicy by remember { mutableStateOf("No") }
    var petExpanded by remember { mutableStateOf(false) }
    var driveway by remember { mutableStateOf(false) }
    var streetParking by remember { mutableStateOf(false) }
    var garage by remember { mutableStateOf(0) }

    Scaffold(topBar = { TopAppBar(title = { Text(if (propertyId == null) "New property" else "Edit property") }) }) { pad ->
        Column(
            Modifier.padding(pad).padding(16.dp).fillMaxWidth().verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            SpaciousCard("Details") {
                OutlinedTextField(value = address, onValueChange = { address = it }, label = { Text("Street address") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = city, onValueChange = { city = it }, label = { Text("City") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = zip, onValueChange = { zip = it }, label = { Text("ZIP") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
            }
            SpaciousCard("Rental terms") {
                OutlinedTextField(value = rent, onValueChange = { rent = it }, label = { Text("Monthly rent") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Security deposit") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Pet deposit") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Move-in date") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Move-out date") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
            }
            SpaciousCard("Short-stay terms") {
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Nightly price") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Cleaning fee") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Extra guest fee") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Minimum stay") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Max guests") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
            }
            SpaciousCard("Amenities") {
                CheckboxRow("Driveway", driveway) { driveway = it }
                CheckboxRow("Street parking", streetParking) { streetParking = it }
                CheckboxRow("1-car garage", garage == 1) { if (it) garage = 1 }
                CheckboxRow("2-car garage", garage == 2) { if (it) garage = 2 }
            }
            SpaciousCard("Pet policy") {
                ExposedDropdownMenuBox(expanded = petExpanded, onExpandedChange = { petExpanded = it }) {
                    OutlinedTextField(
                        value = petPolicy,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Pet policy") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = petExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth().heightIn(min = 48.dp)
                    )
                    ExposedDropdownMenu(expanded = petExpanded, onDismissRequest = { petExpanded = false }) {
                        listOf("Yes", "No").forEach { value ->
                            DropdownMenuItem(text = { Text(value) }, onClick = { petPolicy = value; petExpanded = false })
                        }
                    }
                }
            }
            SpaciousCard("Notes") {
                OutlinedTextField(value = "", onValueChange = {}, label = { Text("Notes") }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp))
            }
            Button(
                onClick = {
                    val property = Property(
                        id = propertyId ?: 0,
                        address = address,
                        city = city,
                        zipCode = zip,
                        rentPrice = rent.toDoubleOrNull(),
                        petPolicy = petPolicy,
                        garageSpaces = garage,
                        parkingType = when {
                            driveway -> "Driveway"
                            streetParking -> "Street"
                            garage > 0 -> "$garage-car garage"
                            else -> null
                        }
                    )
                    scope.launch { onSaved(saveProperty(property)) }
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
            ) { Text("Save property") }
        }
    }
}

@Composable
private fun CheckboxRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onChange)
        Text(label)
    }
}
