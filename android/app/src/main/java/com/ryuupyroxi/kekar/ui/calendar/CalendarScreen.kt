package com.ryuupyroxi.kekar.ui.calendar

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.calendar.CalendarEvent

@Composable
fun CalendarScreen(events: List<CalendarEvent>) {
    LazyColumn(Modifier.padding(16.dp).fillMaxWidth()) {
        items(events) { event ->
            Card(Modifier.padding(vertical = 4.dp)) {
                Text(event.label, Modifier.padding(16.dp))
            }
        }
    }
}
