package com.ryuupyroxi.kekar.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sync_state")
data class SyncStateEntity(
    @PrimaryKey val entityKey: String,
    val lastBaseSnapshotId: String,
    val updatedAt: String,
    val deviceId: String
)
