package com.ryuupyroxi.kekar.listings

data class SitePackage(
    val site: String,
    val label: String,
    val title: String,
    val body: String,
    val fields: List<Pair<String, String>>,
    val warnings: List<String>
)
