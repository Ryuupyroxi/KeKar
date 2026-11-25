package com.ryuupyroxi.kekar.data.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.ryuupyroxi.kekar.data.entities.PropertyEntity

@Dao
interface PropertyDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entity: PropertyEntity): Long

    @Query("SELECT * FROM properties ORDER BY address")
    suspend fun all(): List<PropertyEntity>

    @Query("SELECT * FROM properties WHERE id = :id")
    suspend fun find(id: Long): PropertyEntity?
}
