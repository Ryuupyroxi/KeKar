package com.ryuupyroxi.kekar.domain.model

data class Booking(
    val id: Long = 0,
    val propertyId: Long,
    val guestName: String,
    val checkIn: String,
    val checkOut: String,
    val status: String = "Confirmed"
)
