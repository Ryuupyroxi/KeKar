package com.ryuupyroxi.kekar.domain.model

data class Applicant(
    val id: Long = 0,
    val propertyId: Long,
    val name: String,
    val contact: String? = null,
    val stage: String = "New",
    val notes: String? = null
)
