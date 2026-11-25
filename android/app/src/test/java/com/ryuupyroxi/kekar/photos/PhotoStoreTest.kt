package com.ryuupyroxi.kekar.photos

import com.google.common.truth.Truth.assertThat
import java.nio.file.Files
import org.junit.Test

class PhotoStoreTest {
    @Test
    fun saved_photo_is_written_under_the_app_photo_directory() {
        val dir = Files.createTempDirectory("kekar-photos")
        val store = PhotoStore(dir.toFile())
        val bytes = "fake-jpeg-bytes".toByteArray()

        val sha = store.saveBytes(bytes)

        assertThat(sha).matches("[0-9a-f]{64}")
        assertThat(store.fileFor(sha).readBytes()).isEqualTo(bytes)
        assertThat(store.fileFor(sha).parentFile).isEqualTo(dir.toFile())
    }
}
