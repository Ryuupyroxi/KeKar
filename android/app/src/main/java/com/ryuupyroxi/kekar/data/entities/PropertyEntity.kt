package com.ryuupyroxi.kekar.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "properties")
data class PropertyEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val address: String,
    val city: String? = null,
    val zipCode: String? = null,
    val rentPrice: Double? = null,
    val depositAmount: Double? = null,
    val availableDate: String? = null,
    val moveInDate: String? = null,
    val moveOutDate: String? = null,
    val bedrooms: Int? = null,
    val bathrooms: Double? = null,
    val sqft: Int? = null,
    val petPolicy: String? = null,
    val petDepositAmount: Double? = null,
    val status: String = "Vacant",
    val kind: String = "rental",
    val amenityWd: Boolean = false,
    val amenityAc: Boolean = false,
    val amenityYard: Boolean = false,
    val amenityDishwasher: Boolean = false,
    val amenityParking: Boolean = false,
    val garageSpaces: Int = 0,
    val parkingType: String? = null,
    val notes: String? = null,
    val nightlyPrice: Double? = null,
    val cleaningFee: Double? = null,
    val extraGuestFee: Double? = null,
    val minStayNights: Int? = null,
    val maxGuests: Int? = null,
    val checkInTime: String? = null,
    val checkOutTime: String? = null,
    val instantBook: Boolean = false,
    val cancellationPolicy: String? = null,
    val houseRules: String? = null,
    val updatedAt: String? = null,
    val deviceId: String? = null
)
