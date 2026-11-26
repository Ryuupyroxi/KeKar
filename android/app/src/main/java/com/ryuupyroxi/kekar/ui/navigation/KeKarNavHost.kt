package com.ryuupyroxi.kekar.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Settings
import com.ryuupyroxi.kekar.ui.applicants.ApplicantsScreen
import com.ryuupyroxi.kekar.ui.calendar.CalendarScreen
import com.ryuupyroxi.kekar.ui.property.PropertyDetailScreen
import com.ryuupyroxi.kekar.ui.leases.LeasesScreen
import com.ryuupyroxi.kekar.ui.property.PropertyListScreen
import com.ryuupyroxi.kekar.ui.stays.StaysScreen

private data class Destination(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

@Composable
fun KeKarNavHost() {
    val destinations = listOf(
        Destination("Dashboard", Icons.Filled.Home),
        Destination("Properties", Icons.Filled.Home),
        Destination("Calendar", Icons.Filled.CalendarMonth),
        Destination("Applicants", Icons.Filled.People),
        Destination("Leases", Icons.Filled.DateRange),
        Destination("Stays", Icons.Filled.ChevronRight),
        Destination("Assistant", Icons.Filled.Chat)
    )
    var selected by remember { mutableStateOf("Properties") }
    var editing by remember { mutableStateOf(false) }
    Scaffold(bottomBar = {
        NavigationBar {
            destinations.forEach { dest ->
                NavigationBarItem(
                    selected = selected == dest.label,
                    onClick = { selected = dest.label; editing = false },
                    icon = { Icon(dest.icon, contentDescription = dest.label) },
                    label = { Text(dest.label) }
                )
            }
        }
    }) { pad ->
        androidx.compose.foundation.layout.Box(Modifier.padding(pad)) {
            when {
                selected == "Properties" && editing -> PropertyDetailScreen(
                    propertyId = null,
                    onSaved = { editing = false },
                    saveProperty = { 1L }
                )
                selected == "Properties" -> PropertyListScreen(emptyList()) { editing = true }
                selected == "Calendar" -> CalendarScreen(emptyList())
                selected == "Applicants" -> ApplicantsScreen(emptyList())
                selected == "Leases" -> LeasesScreen()
                selected == "Stays" -> StaysScreen(emptyList())
                else -> Text(destinations.first { it.label == selected }.label + " coming next")
            }
        }
    }
}
