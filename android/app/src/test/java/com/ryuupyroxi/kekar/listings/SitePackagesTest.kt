package com.ryuupyroxi.kekar.listings

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.domain.model.Property
import org.junit.Test

class SitePackagesTest {
    @Test
    fun all_sites_are_available_and_facebook_has_a_scam_warning() {
        SITE_KEYS.forEach { assertThat(SITE_KEYS).contains(it) }

        val pkg = compileSitePackage(
            Property(address = "44 Market Way", city = "Pawhuska", rentPrice = 900.0, bedrooms = 2),
            "facebook_marketplace")

        assertThat(pkg.warnings.joinToString(" ")).contains("scam")
    }
}
