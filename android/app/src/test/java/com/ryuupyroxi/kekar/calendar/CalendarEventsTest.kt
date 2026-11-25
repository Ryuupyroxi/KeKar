package com.ryuupyroxi.kekar.calendar

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.domain.model.Booking
import com.ryuupyroxi.kekar.domain.model.Property
import org.junit.Test

class CalendarEventsTest {
    @Test
    fun selected_property_row_sorts_first() {
        val first = Property(id = 1, address = "Top Road", moveInDate = "2027-05-20")
        val second = Property(id = 2, address = "Lower Road", moveInDate = "2027-01-05")

        val events = buildCalendarEvents(listOf(first, second), emptyList(), 1)

        assertThat(events.first().label).contains("Top Road")
    }
}
