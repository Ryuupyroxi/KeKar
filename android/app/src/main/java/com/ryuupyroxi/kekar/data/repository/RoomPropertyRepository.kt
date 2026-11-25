package com.ryuupyroxi.kekar.data.repository

import com.ryuupyroxi.kekar.data.dao.PropertyDao
import com.ryuupyroxi.kekar.data.entities.PropertyEntity
import com.ryuupyroxi.kekar.domain.model.Property

class RoomPropertyRepository(private val dao: PropertyDao) : PropertyRepository {
    override suspend fun save(property: Property): Long = dao.insert(property.toEntity())

    override suspend fun list(): List<Property> = dao.all().map { it.toDomain() }

    override suspend fun get(id: Long): Property? = dao.find(id)?.toDomain()

    private fun Property.toEntity() = PropertyEntity(
        id = id,
        address = address,
        city = city,
        zipCode = zipCode,
        rentPrice = rentPrice,
        depositAmount = depositAmount,
        availableDate = availableDate,
        moveInDate = moveInDate,
        moveOutDate = moveOutDate,
        bedrooms = bedrooms,
        bathrooms = bathrooms,
        sqft = sqft,
        petPolicy = petPolicy,
        petDepositAmount = petDepositAmount,
        status = status,
        kind = kind,
        amenityWd = amenityWd,
        amenityAc = amenityAc,
        amenityYard = amenityYard,
        amenityDishwasher = amenityDishwasher,
        garageSpaces = garageSpaces,
        parkingType = parkingType
    )

    private fun PropertyEntity.toDomain() = Property(
        id = id,
        address = address,
        city = city,
        zipCode = zipCode,
        rentPrice = rentPrice,
        depositAmount = depositAmount,
        availableDate = availableDate,
        moveInDate = moveInDate,
        moveOutDate = moveOutDate,
        bedrooms = bedrooms,
        bathrooms = bathrooms,
        sqft = sqft,
        petPolicy = petPolicy ?: "No",
        petDepositAmount = petDepositAmount,
        status = status,
        kind = kind,
        amenityWd = amenityWd,
        amenityAc = amenityAc,
        amenityYard = amenityYard,
        amenityDishwasher = amenityDishwasher,
        garageSpaces = garageSpaces,
        parkingType = parkingType
    )
}
