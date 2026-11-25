package com.ryuupyroxi.kekar.data

import androidx.room.Database
import androidx.room.RoomDatabase
import com.ryuupyroxi.kekar.data.entities.PhotoAssetEntity
import com.ryuupyroxi.kekar.data.entities.PropertyEntity
import com.ryuupyroxi.kekar.data.entities.SyncStateEntity

const val SCHEMA_VERSION = 1

@Database(
    entities = [PropertyEntity::class, SyncStateEntity::class, PhotoAssetEntity::class],
    version = SCHEMA_VERSION,
    exportSchema = true
)
abstract class KeKarDatabase : RoomDatabase()
