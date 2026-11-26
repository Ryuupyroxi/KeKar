package com.ryuupyroxi.kekar.records

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.domain.model.Booking
import com.ryuupyroxi.kekar.domain.usecase.leaseClauses
import com.ryuupyroxi.kekar.domain.usecase.leaseFields
import com.ryuupyroxi.kekar.domain.usecase.staysOverlap
import org.junit.Test

class RecordScreenSpecTest {
    @Test
    fun lease_fields_include_template_and_pet_deposit_clause() {
        assertThat(leaseFields()).contains("Template")
        assertThat(leaseClauses()).contains("Pet deposit clause")
    }

    @Test
    fun overlapping_stays_are_detected() {
        val first = Booking(propertyId = 1, guestName = "A", checkIn = "2027-06-01", checkOut = "2027-06-05")
        val second = Booking(propertyId = 1, guestName = "B", checkIn = "2027-06-04", checkOut = "2027-06-08")
        assertThat(staysOverlap(first, second)).isTrue()
    }
}
