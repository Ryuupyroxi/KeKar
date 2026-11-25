package com.ryuupyroxi.kekar.photos

import android.content.Context
import android.graphics.Bitmap
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest

class PhotoStore(private val dir: File) {
    companion object {
        fun from(context: Context): PhotoStore =
            PhotoStore(context.filesDir.resolve("photos").apply { mkdirs() })
    }

    suspend fun save(bitmap: Bitmap): String {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 82, stream)
        return saveBytes(stream.toByteArray())
    }

    fun saveBytes(bytes: ByteArray): String {
        val sha = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
        fileFor(sha).writeBytes(bytes)
        return sha
    }

    fun fileFor(sha: String): File = File(dir, "$sha.jpg")
}
