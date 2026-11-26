package com.ryuupyroxi.kekar.domain.model

data class Lease(
    val id: Long = 0,
    val propertyId: Long,
    val tenant: String,
    val landlord: String,
    val term: String,
    val body: String
)
