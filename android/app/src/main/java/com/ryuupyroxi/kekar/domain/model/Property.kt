package com.ryuupyroxi.kekar.domain.model

data class Property(
    val id: Long = 0,
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
    val petPolicy: String = "No",
    val petDepositAmount: Double? = null,
    val status: String = "Vacant",
    val kind: String = "rental",
    val amenityWd: Boolean = false,
    val amenityAc: Boolean = false,
    val amenityYard: Boolean = false,
    val amenityDishwasher: Boolean = false,
    val garageSpaces: Int = 0,
    val parkingType: String? = null
)
