package com.ryuupyroxi.kekar.data.repository

import com.ryuupyroxi.kekar.domain.model.Property

interface PropertyRepository {
    suspend fun save(property: Property): Long
    suspend fun list(): List<Property>
    suspend fun get(id: Long): Property?
}
