package com.ryuupyroxi.kekar.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "photo_assets")
data class PhotoAssetEntity(
    @PrimaryKey val sha256: String,
    val propertyId: Long,
    val relativePath: String,
    val mimeType: String,
    val createdAt: String
)
