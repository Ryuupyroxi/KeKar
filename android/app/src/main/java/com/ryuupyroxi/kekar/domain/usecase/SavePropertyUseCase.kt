package com.ryuupyroxi.kekar.domain.usecase

import com.ryuupyroxi.kekar.data.repository.PropertyRepository
import com.ryuupyroxi.kekar.domain.model.Property

class SavePropertyUseCase(private val repository: PropertyRepository) {
    suspend operator fun invoke(property: Property): Long = repository.save(property)
}
