package com.ryuupyroxi.kekar.calendar

import com.ryuupyroxi.kekar.domain.model.Booking
import com.ryuupyroxi.kekar.domain.model.Property

data class CalendarEvent(
    val date: String,
    val label: String,
    val color: Long,
    val propertyId: Long
)

private const val MOVE_IN_COLOR = 0xFF2E7D32L
private const val MOVE_OUT_COLOR = 0xFFB71C1CL
private const val SHORT_STAY_COLOR = 0xFF6A1B9AL

fun buildCalendarEvents(
    properties: List<Property>,
    bookings: List<Booking>,
    selectedId: Long?
): List<CalendarEvent> {
    val rows = properties.map { property ->
        val dates = listOfNotNull(property.moveInDate, property.moveOutDate)
        val label = buildString {
            append(property.address)
            if (property.moveInDate != null) append(" | Move-in ${property.moveInDate}")
            if (property.moveOutDate != null) append(" | Move-out ${property.moveOutDate}")
        }
        CalendarEvent(
            date = dates.minOrNull().orEmpty(),
            label = label,
            color = if (property.moveInDate != null) MOVE_IN_COLOR else MOVE_OUT_COLOR,
            propertyId = property.id
        )
    }
    val (selected, others) = rows.partition { selectedId != null && it.propertyId == selectedId }
    val stays = bookings.map { booking ->
        val property = properties.firstOrNull { it.id == booking.propertyId }
        CalendarEvent(
            date = booking.checkIn,
            label = "Short stay | ${booking.guestName} | ${property?.address ?: "Unknown"}",
            color = SHORT_STAY_COLOR,
            propertyId = booking.propertyId
        )
    }
    return selected + others + stays
}
