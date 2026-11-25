package com.ryuupyroxi.kekar.data

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.data.entities.PropertyEntity
import org.junit.Test

class SchemaTest {
    @Test
    fun schema_version_is_one() {
        assertThat(SCHEMA_VERSION).isEqualTo(1)
    }

    @Test
    fun property_entity_keeps_desktop_legacy_fields() {
        val fieldNames = PropertyEntity::class.java.declaredFields.map { it.name }
        assertThat(fieldNames).contains("amenityParking")
        assertThat(fieldNames).contains("petDepositAmount")
        assertThat(fieldNames).contains("garageSpaces")
        assertThat(fieldNames).contains("parkingType")
    }
}
