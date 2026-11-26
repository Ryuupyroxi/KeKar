package com.ryuupyroxi.kekar.domain.usecase

import com.ryuupyroxi.kekar.domain.model.Booking

fun leaseFields(): List<String> = listOf("Property", "Tenant", "Landlord", "Term", "Template", "Pet deposit")

fun leaseClauses(): List<String> = listOf(
    "Rent and due date",
    "Security deposit",
    "Pet deposit clause",
    "Term and notice",
    "Maintenance and repairs"
)

fun builtInLeaseTemplate(): String = listOf(
    "RESIDENTIAL LEASE AGREEMENT",
    "Property: {{address}}",
    "Landlord: {{landlord}}",
    "Tenant: {{tenant}}",
    "Term: {{term}}",
    "Rent: {{rent}} due on the first day of each month.",
    "Security deposit: {{deposit}}.",
    "Pet deposit clause: {{pet_deposit}}.",
    "Maintenance and repairs: tenant shall keep the premises reasonably clean.",
    "Notice: parties agree to give written notice as required by law."
).joinToString("\n")

fun staysOverlap(first: Booking, second: Booking): Boolean =
    first.propertyId == second.propertyId &&
        first.checkIn < second.checkOut && second.checkIn < first.checkOut
