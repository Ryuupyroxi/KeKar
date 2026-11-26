package com.ryuupyroxi.kekar.ui.stays

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ryuupyroxi.kekar.domain.model.Booking

@Composable
fun StaysScreen(bookings: List<Booking>) {
    LazyColumn(Modifier.padding(16.dp).fillMaxWidth()) {
        items(bookings) { booking ->
            Card(Modifier.padding(vertical = 4.dp)) {
                Text("${booking.guestName} | ${booking.checkIn} → ${booking.checkOut}", Modifier.padding(16.dp))
            }
        }
    }
}
