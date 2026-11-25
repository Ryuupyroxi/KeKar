package com.ryuupyroxi.kekar.domain

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.data.repository.PropertyRepository
import com.ryuupyroxi.kekar.domain.model.Property
import com.ryuupyroxi.kekar.domain.usecase.SavePropertyUseCase
import kotlinx.coroutines.test.runTest
import org.junit.Test

class SavePropertyUseCaseTest {
    @Test
    fun saves_a_property_and_returns_its_id() = runTest {
        val repo = FakePropertyRepository()
        val useCase = SavePropertyUseCase(repo)
        val id = useCase(Property(address = "101 Oak Street", petPolicy = "Yes"))
        assertThat(id).isEqualTo(1)
        assertThat(repo.saved.single().petPolicy).isEqualTo("Yes")
    }
}

private class FakePropertyRepository : PropertyRepository {
    val saved = mutableListOf<Property>()
    private var nextId = 1L
    override suspend fun save(property: Property): Long {
        saved.add(property)
        return nextId++
    }
    override suspend fun list(): List<Property> = saved
    override suspend fun get(id: Long): Property? = saved.getOrNull(id.toInt() - 1)
}
