package com.ryuupyroxi.kekar.listings

import com.ryuupyroxi.kekar.domain.model.Property

val SITE_KEYS = listOf(
    "zillow", "apartments_com", "facebook_marketplace", "airbnb", "vrbo", "booking_com"
)

val SITE_LABELS = mapOf(
    "zillow" to "Zillow",
    "apartments_com" to "Apartments.com",
    "facebook_marketplace" to "Facebook Marketplace",
    "airbnb" to "Airbnb",
    "vrbo" to "Vrbo",
    "booking_com" to "Booking.com"
)

fun compileSitePackage(property: Property, site: String): SitePackage {
    val city = property.city ?: "the area"
    val rent = property.rentPrice?.let { "$" + it.toInt() } ?: "contact for rent"
    val address = property.address
    val beds = property.bedrooms?.toString() ?: "studio"
    val baseFields = listOf(
        "Address" to address,
        "City" to city,
        "Rent" to rent,
        "Bedrooms" to beds
    )
    return when (site) {
        "apartments_com" -> SitePackage(site, SITE_LABELS.getValue(site),
            "$beds bedroom apartment in $city",
            "$beds bedroom rental at $address in $city. Rent: $rent. Contact the owner for a showing.",
            baseFields + ("Equal housing" to "Yes"), emptyList())
        "facebook_marketplace" -> SitePackage(site, SITE_LABELS.getValue(site),
            "$beds BR rental in $city — $rent",
            "$beds bedroom rental at $address, $city. $rent/month. Message for details and showing times.",
            baseFields,
            listOf("Watch for scams: never wire money or pay before viewing the property in person."))
        "airbnb" -> SitePackage(site, SITE_LABELS.getValue(site),
            "Stay in $city — $address",
            "Short-term stay in $city. Nightly rate applies, cleaning fee may apply. House rules and minimum stay are set by the host.",
            baseFields + ("Instant book" to if (property.kind == "short_stay") "Yes" else "No"),
            emptyList())
        "vrbo" -> SitePackage(site, SITE_LABELS.getValue(site),
            "Vacation rental in $city — $address",
            "Whole-property short stay in $city. Nightly rate, cleaning fee and guest limit shown on the booking request.",
            baseFields, emptyList())
        "booking_com" -> SitePackage(site, SITE_LABELS.getValue(site),
            "$city short stay — $address",
            "Short stay in $city. Cancellation policy and check-in times are confirmed before booking.",
            baseFields, emptyList())
        else -> SitePackage(site, SITE_LABELS.getValue(site),
            "$beds bd in $city | $address",
            "$beds bedroom rental at $address in $city. $rent/month. Equal Housing Opportunity.",
            baseFields + ("Equal housing" to "Yes"), emptyList())
    }
}
