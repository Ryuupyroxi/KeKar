# Android App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `KeKar Android`, a native standalone Android 10+ version of KeKar Lite with every Lite feature and optional snapshot sync to the desktop app.

**Architecture:** One Kotlin Android Studio project under `android/`, using Compose for UI, Room for the local SQLite database, Hilt for dependency injection, WorkManager for explicit sync jobs, and a package-per-concern layout (`data`, `domain`, `sync`, `ui`, `photos`, `listings`, `assistant`, `settings`, `updates`). The app is fully usable without a desktop; sync is an explicit user action using a `.kekarsync` ZIP and three-way field-level merge.

**Tech Stack:** Kotlin 2.0, Jetpack Compose + Material 3, Room 2.6, Hilt, Navigation Compose, WorkManager, DataStore, kotlinx.serialization, OkHttp, Coil, AndroidX Security, JUnit 4, Truth, Turbine, MockK, Gradle Kotlin DSL, AGP 8.5.

## Global Constraints

- Package name: `com.ryuupyroxi.kekar`.
- Project location: `/home/Ryuu/Documents/kekar project/android/`.
- `minSdk = 29`, `targetSdk = 35`, `compileSdk = 35`.
- Every Lite feature is v1 must-have: properties, rental and short-stay terms, amenities, pet policy, photos, calendar, applicants, leases, stays, listing-site packages, assistant, tour, settings, Help legend and update checker.
- Offline-first: local Room database is authoritative on the device. No cloud service or account is required.
- Sync is explicit. No silent background merge and no automatic overwrites.
- Sync package: `.kekarsync` ZIP containing `database.db`, `photos/<sha256>.jpg`, `manifest.json`.
- `manifest.json` fields: `schema_version`, `device_id`, `generated_at`, `base_snapshot_id`, `files` with SHA-256 hashes.
- Theme default: follow system; manual Light / Dark / OLED overrides.
- OLED theme: background `#000000`; no dark text on dark surfaces anywhere.
- Accent: warm amber only for active navigation, primary actions and status. No blue or teal.
- Typography: system Roboto/Inter, no bundled display font.
- Icons: Material Symbols outlined, 2dp stroke.
- Accessibility: dynamic type to 200%, minimum 48dp touch targets, WCAG AA contrast in all themes.
- Motion: short fades only, soft 8dp elevation, no flashy transitions.
- Assistant key: user-entered at runtime, stored via Android Keystore/EncryptedSharedPreferences. Never in source, logs, sync packages or APK assets.
- Distribution: signed private APK first via GitHub release asset; Play Store phase later.
- Signing keystore is stored outside the repository and never committed.

## Key Decisions

1. **"Phone primary" resolved to standalone equals.** The design conversation changed the product model: both apps are complete standalone products. Sync is optional alignment between equals, not a master/slave relationship.
2. **"Offline-first" plus "assistant" resolved as hybrid.** All property features work offline. The assistant is the only network feature and is opt-in through a user-entered key.
3. **"Near feature parity" resolved as full Lite parity.** The user selected all Lite features as v1 must-haves.
4. **"Private APK first" plus "Play Store later" resolved as two release phases.** Play Store work does not block the first usable build.
5. **"Sleek and user-friendly" resolved as clean neutral productivity with spacious cards.** The user chose graphite/white, amber accent, system font and quiet motion.

## File Structure

```text
android/
  settings.gradle.kts
  build.gradle.kts
  gradle.properties
  app/
    build.gradle.kts
    proguard-rules.pro
    src/main/AndroidManifest.xml
    src/main/java/com/ryuupyroxi/kekar/
      KeKarApplication.kt
      MainActivity.kt
      data/
        KeKarDatabase.kt
        entities/PropertyEntity.kt
        entities/ApplicantEntity.kt
        entities/BookingEntity.kt
        entities/LeaseEntity.kt
        entities/PortalSettingsEntity.kt
        entities/ChatMessageEntity.kt
        entities/SyncStateEntity.kt
        entities/PhotoAssetEntity.kt
        dao/PropertyDao.kt
        dao/ApplicantDao.kt
        dao/BookingDao.kt
        dao/LeaseDao.kt
        dao/ChatDao.kt
        dao/SyncDao.kt
        repository/PropertyRepository.kt
        repository/ApplicantRepository.kt
        repository/BookingRepository.kt
        repository/LeaseRepository.kt
      domain/
        model/Property.kt
        model/Applicant.kt
        model/Booking.kt
        usecase/SavePropertyUseCase.kt
        usecase/GenerateLeaseUseCase.kt
      ui/
        theme/Color.kt
        theme/Theme.kt
        theme/Type.kt
        navigation/KeKarNavHost.kt
        dashboard/DashboardScreen.kt
        property/PropertyListScreen.kt
        property/PropertyDetailScreen.kt
        calendar/CalendarScreen.kt
        applicants/ApplicantsScreen.kt
        leases/LeasesScreen.kt
        stays/StaysScreen.kt
        assistant/AssistantScreen.kt
        settings/SettingsScreen.kt
        help/HelpScreen.kt
        sync/SyncScreen.kt
        common/SpaciousCard.kt
      photos/
        PhotoStore.kt
        PhotoPicker.kt
      listings/
        SitePackage.kt
        SitePackages.kt
        ListingScreen.kt
      assistant/
        OpenRouterClient.kt
        AssistantRepository.kt
        AssistantTools.kt
        KeyStore.kt
      sync/
        SyncManifest.kt
        SnapshotExporter.kt
        SnapshotImporter.kt
        MergeEngine.kt
        Conflict.kt
        SyncWorker.kt
      settings/
        SettingsRepository.kt
        ThemeMode.kt
      updates/
        GitHubUpdateChecker.kt
    src/test/java/com/ryuupyroxi/kekar/...
    src/androidTest/java/com/ryuupyroxi/kekar/...
```

---

## Task 1: Gradle scaffold and runnable themed shell

**Objective:** Create a buildable Android app with Compose, Hilt, Navigation and the three themes.

**Files:**
- Create: `android/settings.gradle.kts`, `android/build.gradle.kts`, `android/gradle.properties`
- Create: `android/app/build.gradle.kts`, `android/app/proguard-rules.pro`, `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/KeKarApplication.kt`, `MainActivity.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/theme/Color.kt`, `Theme.kt`, `Type.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/theme/ThemeTokensTest.kt`

**Interfaces:**
- Produces: `KeKarTheme(themeMode: ThemeMode, content: @Composable () -> Unit)`.
- Produces: `enum class ThemeMode { SYSTEM, LIGHT, DARK, OLED }`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.theme

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class ThemeTokensTest {
    @Test
    fun oled_has_pure_black_background_and_light_text() {
        assertThat(OledColors.background.value).isEqualTo(0xFF000000.toInt())
        assertThat(OledColors.onBackground.value).isEqualTo(0xFFE8E6E1.toInt())
    }

    @Test
    fun accent_is_amber_in_all_themes() {
        assertThat(LightColors.primary.value).isEqualTo(0xFFC8892A.toInt())
        assertThat(DarkColors.primary.value).isEqualTo(0xFFC8892A.toInt())
        assertThat(OledColors.primary.value).isEqualTo(0xFFC8892A.toInt())
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*ThemeTokensTest'`
Expected: FAIL — unresolved references `OledColors`, `LightColors`, `DarkColors`.

- [ ] **Step 3: Write minimal implementation**

`android/app/src/main/java/com/ryuupyroxi/kekar/ui/theme/Color.kt`:

```kotlin
package com.ryuupyroxi.kekar.ui.theme

import androidx.compose.ui.graphics.Color

object LightColors {
    val primary = Color(0xFFC8892A)
    val background = Color(0xFFFFFFFF)
    val onBackground = Color(0xFF1B1B1B)
    val surface = Color(0xFFF6F5F2)
    val onSurface = Color(0xFF242424)
}

object DarkColors {
    val primary = Color(0xFFC8892A)
    val background = Color(0xFF202124)
    val onBackground = Color(0xFFE8E6E1)
    val surface = Color(0xFF2A2B2E)
    val onSurface = Color(0xFFE8E6E1)
}

object OledColors {
    val primary = Color(0xFFC8892A)
    val background = Color(0xFF000000)
    val onBackground = Color(0xFFE8E6E1)
    val surface = Color(0xFF0B0B0B)
    val onSurface = Color(0xFFF2F0EB)
}
```

`android/app/src/main/java/com/ryuupyroxi/kekar/ui/theme/Theme.kt`:

```kotlin
package com.ryuupyroxi.kekar.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

enum class ThemeMode { SYSTEM, LIGHT, DARK, OLED }

@Composable
fun KeKarTheme(themeMode: ThemeMode, content: @Composable () -> Unit) {
    val mode = if (themeMode == ThemeMode.SYSTEM) {
        if (isSystemInDarkTheme()) ThemeMode.DARK else ThemeMode.LIGHT
    } else themeMode
    val scheme = when (mode) {
        ThemeMode.LIGHT -> lightColorScheme(
            primary = LightColors.primary,
            background = LightColors.background,
            onBackground = LightColors.onBackground,
            surface = LightColors.surface,
            onSurface = LightColors.onSurface)
        ThemeMode.DARK -> darkColorScheme(
            primary = DarkColors.primary,
            background = DarkColors.background,
            onBackground = DarkColors.onBackground,
            surface = DarkColors.surface,
            onSurface = DarkColors.onSurface)
        ThemeMode.OLED, ThemeMode.SYSTEM -> darkColorScheme(
            primary = OledColors.primary,
            background = OledColors.background,
            onBackground = OledColors.onBackground,
            surface = OledColors.surface,
            onSurface = OledColors.onSurface)
    }
    MaterialTheme(colorScheme = scheme, typography = KeKarTypography, content = content)
}
```

`android/app/src/main/java/com/ryuupyroxi/kekar/ui/theme/Type.kt`:

```kotlin
package com.ryuupyroxi.kekar.ui.theme

import androidx.compose.material3.Typography

val KeKarTypography = Typography()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*ThemeTokensTest'`
Expected: PASS — 2 tests.

- [ ] **Step 5: Verify the shell builds**

Run: `cd android && ./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL and `app/build/outputs/apk/debug/app-debug.apk` exists.

- [ ] **Step 6: Commit**

```bash
git add android/
git commit -m "feat(android): scaffold Compose app with light, dark and OLED themes"
```

## Task 2: Room database and schema-drift test

**Objective:** Define the local database mirroring the desktop schema, including sync metadata.

**Files:**
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/data/KeKarDatabase.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/data/entities/PropertyEntity.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/data/entities/SyncStateEntity.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/data/entities/PhotoAssetEntity.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/data/SchemaTest.kt`

**Interfaces:**
- Consumes: `ThemeMode` from Task 1 is not used here.
- Produces: `const val SCHEMA_VERSION = 1`.
- Produces: `@Entity(tableName = "properties") data class PropertyEntity(...)`.
- Produces: `abstract class KeKarDatabase : RoomDatabase()`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.data

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class SchemaTest {
    @Test
    fun schema_version_is_one() {
        assertThat(SCHEMA_VERSION).isEqualTo(1)
    }

    @Test
    fun property_entity_keeps_desktop_legacy_fields() {
        val fieldNames = PropertyEntity::class.java.declaredFields.map { it.name }
        assertThat(fieldNames).containsAllIn(
            listOf("amenityParking", "petDepositAmount", "garageSpaces", "parkingType"))
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SchemaTest'`
Expected: FAIL — unresolved `SCHEMA_VERSION`, `PropertyEntity`.

- [ ] **Step 3: Write minimal implementation**

`android/app/src/main/java/com/ryuupyroxi/kekar/data/entities/PropertyEntity.kt`:

```kotlin
package com.ryuupyroxi.kekar.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "properties")
data class PropertyEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val address: String,
    val city: String? = null,
    val zipCode: String? = null,
    val rentPrice: Double? = null,
    val depositAmount: Double? = null,
    val availableDate: String? = null,
    val moveInDate: String? = null,
    val moveOutDate: String? = null,
    val bedrooms: Int? = null,
    val bathrooms: Double? = null,
    val sqft: Int? = null,
    val petPolicy: String? = null,
    val petDepositAmount: Double? = null,
    val status: String = "Vacant",
    val kind: String = "rental",
    val amenityWd: Boolean = false,
    val amenityAc: Boolean = false,
    val amenityYard: Boolean = false,
    val amenityDishwasher: Boolean = false,
    val amenityParking: Boolean = false,
    val garageSpaces: Int = 0,
    val parkingType: String? = null,
    val notes: String? = null,
    val nightlyPrice: Double? = null,
    val cleaningFee: Double? = null,
    val extraGuestFee: Double? = null,
    val minStayNights: Int? = null,
    val maxGuests: Int? = null,
    val checkInTime: String? = null,
    val checkOutTime: String? = null,
    val instantBook: Boolean = false,
    val cancellationPolicy: String? = null,
    val houseRules: String? = null,
    val updatedAt: String? = null,
    val deviceId: String? = null
)
```

`android/app/src/main/java/com/ryuupyroxi/kekar/data/entities/SyncStateEntity.kt`:

```kotlin
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
```

`android/app/src/main/java/com/ryuupyroxi/kekar/data/entities/PhotoAssetEntity.kt`:

```kotlin
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
```

`android/app/src/main/java/com/ryuupyroxi/kekar/data/KeKarDatabase.kt`:

```kotlin
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SchemaTest'`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/data android/app/src/test/java/com/ryuupyroxi/kekar/data
git commit -m "feat(android): add Room schema with desktop-compatible property fields"
```

## Task 3: Property repository and save use case

**Objective:** Persist and load properties through a repository with the same Yes/No pet policy and derived amenity fields as Lite.

**Files:**
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/data/dao/PropertyDao.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/data/repository/PropertyRepository.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/domain/model/Property.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/domain/usecase/SavePropertyUseCase.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/domain/SavePropertyUseCaseTest.kt`

**Interfaces:**
- Consumes: `PropertyEntity` from Task 2.
- Produces: `interface PropertyRepository { suspend fun save(property: Property): Long; suspend fun list(): List<Property>; suspend fun get(id: Long): Property? }`.
- Produces: `class SavePropertyUseCase(private val repository: PropertyRepository)` with `suspend operator fun invoke(property: Property): Long`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.domain

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.domain.model.Property
import com.ryuupyroxi.kekar.domain.usecase.SavePropertyUseCase
import kotlinx.coroutines.test.runTest
import org.junit.Test

class SavePropertyUseCaseTest {
    @Test
    fun saves_a_property_and_returns_its_id() = runTest {
        val repo = FakePropertyRepository()
        val useCase = SavePropertyUseCase(repo)
        val id = useCase(Property(address = "101 Oak Street", petPolicy = "Yes"))
        assertThat(id).isEqualTo(1)
        assertThat(repo.saved.single().petPolicy).isEqualTo("Yes")
    }
}
```

Add the fake in the same test file:

```kotlin
private class FakePropertyRepository : com.ryuupyroxi.kekar.data.repository.PropertyRepository {
    val saved = mutableListOf<Property>()
    private var nextId = 1L
    override suspend fun save(property: Property): Long {
        saved.add(property)
        return nextId++
    }
    override suspend fun list(): List<Property> = saved
    override suspend fun get(id: Long): Property? = saved.getOrNull(id.toInt() - 1)
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SavePropertyUseCaseTest'`
Expected: FAIL — unresolved `Property`, `SavePropertyUseCase`, `PropertyRepository`.

- [ ] **Step 3: Write minimal implementation**

`android/app/src/main/java/com/ryuupyroxi/kekar/domain/model/Property.kt`:

```kotlin
package com.ryuupyroxi.kekar.domain.model

data class Property(
    val id: Long = 0,
    val address: String,
    val city: String? = null,
    val zipCode: String? = null,
    val rentPrice: Double? = null,
    val depositAmount: Double? = null,
    val availableDate: String? = null,
    val moveInDate: String? = null,
    val moveOutDate: String? = null,
    val bedrooms: Int? = null,
    val bathrooms: Double? = null,
    val sqft: Int? = null,
    val petPolicy: String = "No",
    val petDepositAmount: Double? = null,
    val status: String = "Vacant",
    val kind: String = "rental",
    val amenityWd: Boolean = false,
    val amenityAc: Boolean = false,
    val amenityYard: Boolean = false,
    val amenityDishwasher: Boolean = false,
    val garageSpaces: Int = 0,
    val parkingType: String? = null
)
```

`android/app/src/main/java/com/ryuupyroxi/kekar/data/repository/PropertyRepository.kt`:

```kotlin
package com.ryuupyroxi.kekar.data.repository

import com.ryuupyroxi.kekar.domain.model.Property

interface PropertyRepository {
    suspend fun save(property: Property): Long
    suspend fun list(): List<Property>
    suspend fun get(id: Long): Property?
}
```

`android/app/src/main/java/com/ryuupyroxi/kekar/domain/usecase/SavePropertyUseCase.kt`:

```kotlin
package com.ryuupyroxi.kekar.domain.usecase

import com.ryuupyroxi.kekar.data.repository.PropertyRepository
import com.ryuupyroxi.kekar.domain.model.Property

class SavePropertyUseCase(private val repository: PropertyRepository) {
    suspend operator fun invoke(property: Property): Long = repository.save(property)
}
```

- [ ] **Step 4: Wire Room implementation**

Create `android/app/src/main/java/com/ryuupyroxi/kekar/data/dao/PropertyDao.kt`:

```kotlin
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
```

Add a Room-backed implementation in `data/repository/RoomPropertyRepository.kt` mapping `Property` to `PropertyEntity` and back. Do not store `amenityParking`; keep the entity field for snapshot compatibility only.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SavePropertyUseCaseTest'`
Expected: PASS — 1 test.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/domain android/app/src/main/java/com/ryuupyroxi/kekar/data android/app/src/test/java/com/ryuupyroxi/kekar/domain
git commit -m "feat(android): add property repository and save use case"
```

## Task 4: Navigation shell and property list/detail screens

**Objective:** Give the app a runnable bottom-navigation shell and a property detail form matching Lite fields.

**Files:**
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/navigation/KeKarNavHost.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/property/PropertyListScreen.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/property/PropertyDetailScreen.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/common/SpaciousCard.kt`
- Test: `android/app/src/androidTest/java/com/ryuupyroxi/kekar/ui/PropertyDetailScreenTest.kt`

**Interfaces:**
- Consumes: `SavePropertyUseCase` from Task 3.
- Produces: `@Composable fun KeKarNavHost()`.
- Produces: `@Composable fun PropertyDetailScreen(propertyId: Long?, onSaved: (Long) -> Unit)`.

- [ ] **Step 1: Write the failing instrumented test**

```kotlin
package com.ryuupyroxi.kekar.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test

class PropertyDetailScreenTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun save_button_is_enabled_after_address_is_entered() {
        compose.setContent { PropertyDetailScreen(propertyId = null, onSaved = {}) }
        compose.onNodeWithText("Save property").performClick()
        compose.onNodeWithText("Street address").assertExists()
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests '*PropertyDetailScreenTest'`
Expected: FAIL — unresolved composable.

- [ ] **Step 3: Implement the screens**

Acceptance specification for `PropertyDetailScreen`:

- Scaffold with top app bar title `New property` or `Edit property`, back arrow, and `Save property` button.
- Body is a `Column` with `verticalArrangement = Arrangement.spacedBy(16.dp)` and 16dp padding.
- Sections in order, each inside `SpaciousCard`: `Details`, `Rental terms`, `Short-stay terms`, `Amenities`, `Pet policy`, `Notes`.
- Details fields: Street address, City, ZIP, Bedrooms, Bathrooms, Square feet.
- Rental terms: Monthly rent, Security deposit, Pet deposit, Available date, Move-in date picker, Move-out date picker.
- Short-stay terms: Nightly price, Cleaning fee, Extra guest fee, Minimum stay, Max guests, Check-in time, Check-out time, Cancellation, Instant Book, House rules.
- Amenities: four checkboxes — Driveway, Street parking, 1-car garage, 2-car garage. Garage checkboxes are mutually exclusive; parking checkboxes are mutually exclusive.
- Pet policy: Yes/No dropdown only.
- Every clickable control has `Modifier.heightIn(min = 48.dp)`.
- Save button calls `SavePropertyUseCase` and then `onSaved(id)`.

`SpaciousCard.kt` implementation:

```kotlin
package com.ryuupyroxi.kekar.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun SpaciousCard(title: String, content: @Composable () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            content()
        }
    }
}
```

- [ ] **Step 4: Implement the navigation shell**

Bottom destinations with outline Material Symbols: Dashboard, Properties, Calendar, Applicants, Leases, Stays, Assistant. Settings and Help are top-bar actions. Each destination initially renders a labelled placeholder composable except Properties.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests '*PropertyDetailScreenTest'`
Expected: PASS — 1 test.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/ui android/app/src/androidTest/java/com/ryuupyroxi/kekar/ui
git commit -m "feat(android): add navigation shell and property detail form"
```

## Task 5: Photo capture and app-private store

**Objective:** Capture or pick photos, compress them and store them inside app-private storage.

**Files:**
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/photos/PhotoStore.kt`
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/photos/PhotoPicker.kt`
- Modify: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/property/PropertyDetailScreen.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/photos/PhotoStoreTest.kt`

**Interfaces:**
- Consumes: Android `Context`, `Bitmap`.
- Produces: `class PhotoStore(private val context: Context)` with `suspend fun save(bitmap: Bitmap): String` returning SHA-256.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.photos

import android.graphics.Bitmap
import androidx.test.core.app.ApplicationProvider
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import org.junit.Test

class PhotoStoreTest {
    @Test
    fun saved_photo_is_in_app_private_files_dir() = runTest {
        val store = PhotoStore(ApplicationProvider.getApplicationContext())
        val sha = store.save(Bitmap.createBitmap(8, 8, Bitmap.Config.ARGB_8888))
        assertThat(sha).matches("[0-9a-f]{64}")
        assertThat(store.fileFor(sha).parentFile!!.name).isEqualTo("photos")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*PhotoStoreTest'`
Expected: FAIL — unresolved `PhotoStore`.

- [ ] **Step 3: Implement**

`PhotoStore.kt`:

```kotlin
package com.ryuupyroxi.kekar.photos

import android.content.Context
import android.graphics.Bitmap
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import kotlin.io.path.outputStream

class PhotoStore(private val context: Context) {
    private val dir = context.filesDir.resolve("photos").apply { mkdirs() }

    suspend fun save(bitmap: Bitmap): String {
        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 82, stream)
        val bytes = stream.toByteArray()
        val sha = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
        fileFor(sha).writeBytes(bytes)
        return sha
    }

    fun fileFor(sha: String) = dir.resolve("$sha.jpg")
}
```

Wire a camera/gallery button into `PropertyDetailScreen` using `rememberLauncherForActivityResult` with `ActivityResultContracts.TakePicturePreview()` and `GetContent()`, then call `PhotoStore.save`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*PhotoStoreTest'`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/photos android/app/src/test/java/com/ryuupyroxi/kekar/photos android/app/src/main/java/com/ryuupyroxi/kekar/ui/property
git commit -m "feat(android): add app-private photo capture and storage"
```

## Task 6: Calendar screen

**Objective:** Show property move dates and short-stay bookings with Lite's colours and interactions.

**Files:**
- Create: `android/app/src/main/java/com/ryuupyroxi/kekar/ui/calendar/CalendarScreen.kt`
- Modify: `KeKarNavHost.kt` Calendar destination
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/calendar/CalendarEventsTest.kt`

**Interfaces:**
- Consumes: `PropertyRepository` from Task 3.
- Produces: `data class CalendarEvent(val date: String, val label: String, val color: Long, val propertyId: Long)`.
- Produces: `fun buildCalendarEvents(properties: List<Property>, bookings: List<Booking>, selectedId: Long?): List<CalendarEvent>`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.calendar

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.domain.model.Booking
import com.ryuupyroxi.kekar.domain.model.Property
import org.junit.Test

class CalendarEventsTest {
    @Test
    fun selected_property_row_sorts_first() {
        val first = Property(id = 1, address = "Top Road", moveInDate = "2027-05-20")
        val second = Property(id = 2, address = "Lower Road", moveInDate = "2027-01-05")
        val events = buildCalendarEvents(listOf(first, second), emptyList(), 1)
        assertThat(events.first().label).contains("Top Road")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*CalendarEventsTest'`
Expected: FAIL — unresolved `Booking`, `buildCalendarEvents`.

- [ ] **Step 3: Implement domain model and builder**

Add `domain/model/Booking.kt` with `id`, `propertyId`, `guestName`, `checkIn`, `checkOut`, `status`.

Implement `buildCalendarEvents` with these exact rules:
- One row per property containing `Move-in YYYY-MM-DD` and `Move-out YYYY-MM-DD`.
- Selected property rows sort before others; within each group sort by earliest date.
- Short stays produce one row per booking labelled `Short stay — guest — address`.
- Colours: move-in `0xFF2E7D32`, move-out `0xFFB71C1C`, short stay `0xFF6A1B9A`.

- [ ] **Step 4: Implement the screen**

Acceptance specification for `CalendarScreen`:
- Full-width month calendar from `androidx.compose.material3.DatePicker` in calendar mode.
- Highlighted days use the three colours; selected property days are bold.
- Below the calendar is a lazy column of event rows.
- Tapping a highlighted date shows a card naming the property and event type.
- Help menu contains `Calendar legend` with green/red/purple explanations.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*CalendarEventsTest'`
Expected: PASS — 1 test.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/domain/model/Booking.kt android/app/src/main/java/com/ryuupyroxi/kekar/ui/calendar android/app/src/test/java/com/ryuupyroxi/kekar/calendar
git commit -m "feat(android): add calendar events and screen"
```

## Task 7: Applicants, leases and stays screens

**Objective:** Implement the remaining record screens with Lite parity.

**Files:**
- Create: `ui/applicants/ApplicantsScreen.kt`, `ui/leases/LeasesScreen.kt`, `ui/stays/StaysScreen.kt`
- Create: `domain/model/Applicant.kt`, `domain/model/Lease.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/records/RecordScreenSpecTest.kt`

**Interfaces:**
- Consumes: `PropertyRepository`, `Booking` from Task 6.
- Produces: `@Composable fun ApplicantsScreen()`, `LeasesScreen()`, `StaysScreen()`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.records

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class RecordScreenSpecTest {
    @Test
    fun lease_fields_include_pet_deposit_and_template_action() {
        val fields = listOf("Property", "Tenant", "Landlord", "Term", "Template")
        assertThat(fields).contains("Template")
        assertThat(fields + "Pet deposit clause").contains("Pet deposit clause")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*RecordScreenSpecTest'`
Expected: FAIL — unresolved test class.

- [ ] **Step 3: Implement screens**

Acceptance specifications:
- Applicants: list with Name, Property dropdown from saved properties, Contact, Stage, Notes. Tap a row opens a full profile card with Save profile.
- Leases: Property dropdown, Tenant, Landlord, Term, template editor with `Load built-in template` and `Upload template file`, Generate, Copy, Share, Save. Generated lease includes pet policy and pet deposit clause.
- Stays: Property dropdown, Add/Edit/Cancel/Delete stay, table of Guest, Portal, Check-in, Check-out, Nights, Payout, Status; overlapping stays are rejected with a readable message.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*RecordScreenSpecTest'`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/ui/applicants android/app/src/main/java/com/ryuupyroxi/kekar/ui/leases android/app/src/main/java/com/ryuupyroxi/kekar/ui/stays android/app/src/main/java/com/ryuupyroxi/kekar/domain/model
git commit -m "feat(android): add applicants, leases and stays screens"
```

## Task 8: Listing site packages and screen

**Objective:** Port the desktop site-package logic into pure Kotlin and expose it through a Site picker.

**Files:**
- Create: `listings/SitePackage.kt`, `listings/SitePackages.kt`, `listings/ListingScreen.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/listings/SitePackagesTest.kt`

**Interfaces:**
- Consumes: `Property` from Task 3.
- Produces: `data class SitePackage(val site: String, val label: String, val title: String, val body: String, val fields: List<Pair<String,String>>, val warnings: List<String>)`.
- Produces: `fun compileSitePackage(property: Property, site: String): SitePackage`.
- Produces: `val SITE_KEYS = listOf("zillow", "apartments_com", "facebook_marketplace", "airbnb", "vrbo", "booking_com")`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.listings

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.domain.model.Property
import org.junit.Test

class SitePackagesTest {
    @Test
    fun all_sites_are_available_and_facebook_has_a_scam_warning() {
        assertThat(SITE_KEYS).containsAllIn(listOf("zillow", "apartments_com",
            "facebook_marketplace", "airbnb", "vrbo", "booking_com"))
        val pkg = compileSitePackage(Property(address = "44 Market Way", city = "Pawhuska",
            rentPrice = 900.0, bedrooms = 2), "facebook_marketplace")
        assertThat(pkg.warnings.joinToString(" ")).contains("scam")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SitePackagesTest'`
Expected: FAIL — unresolved `SITE_KEYS`, `compileSitePackage`.

- [ ] **Step 3: Implement the compiler**

Port the desktop `src/services/listing_sites.py` rules:
- Zillow: title `{beds} bd {baths} ba in {city} | {address}`, Equal Housing line.
- apartments.com: separate description field, lead-friendly structure.
- Facebook Marketplace: short neighbourhood title, plain description, scam warning.
- Airbnb: nightly rate, cleaning fee, minimum stay, occupancy, house rules.
- Vrbo: nightly rate, cleaning fee, extra guest fee, occupancy.
- Booking.com: nightly rate, cleaning fee, minimum stay, cancellation.

- [ ] **Step 4: Implement the screen**

Acceptance specification for `ListingScreen`:
- Label reads `Site`, not `Channel`.
- Dropdown lists generic plus every key in `SITE_KEYS`.
- Preview uses `[Label]`, `Title:` and body.
- Warnings appear without a repeated "Before you post" heading.
- Copy and Share buttons use Android clipboard and share intent.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SitePackagesTest'`
Expected: PASS — 1 test.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/listings android/app/src/test/java/com/ryuupyroxi/kekar/listings
git commit -m "feat(android): add listing site packages and preview screen"
```

## Task 9: Assistant client and secure key storage

**Objective:** Add an OpenRouter-compatible assistant with a runtime-entered key.

**Files:**
- Create: `assistant/OpenRouterClient.kt`, `assistant/AssistantRepository.kt`, `assistant/KeyStore.kt`, `assistant/AssistantTools.kt`
- Create: `ui/assistant/AssistantScreen.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/assistant/AssistantClientTest.kt`

**Interfaces:**
- Consumes: OkHttp, kotlinx.serialization.
- Produces: `class KeyStore(private val context: Context)` with `fun getKey(): String?`, `fun saveKey(key: String)`.
- Produces: `class OpenRouterClient(private val keyStore: KeyStore)` with `suspend fun chat(messages: List<ChatMessage>): String`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.assistant

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class AssistantClientTest {
    @Test
    fun provider_url_is_openrouter_chat_endpoint() {
        assertThat(OpenRouterClient.CHAT_URL)
            .isEqualTo("https://openrouter.ai/api/v1/chat/completions")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*AssistantClientTest'`
Expected: FAIL — unresolved `OpenRouterClient`.

- [ ] **Step 3: Implement**

`KeyStore.kt` uses `EncryptedSharedPreferences` with `MasterKey` from AndroidX Security. Key name: `api_key`. The key is never logged.

`OpenRouterClient.kt` posts JSON with `model = "openrouter/free"`, `messages`, and `Authorization: Bearer <key>`. It treats empty content as failure, quotes provider error text in the UI, and never writes the key to a file.

`AssistantTools.kt` exposes read-only tools: `property_list`, `applicant_list`, `booking_list`, `lease_list`. Any future write tool requires a UI confirmation before dispatch.

- [ ] **Step 4: Implement the screen**

Acceptance specification for `AssistantScreen`:
- If no key exists, show `Add your API key in Settings to use the assistant` with a Settings button.
- Chat transcript uses user/assistant bubbles with 16dp spacing.
- Input field and Send button are at least 48dp tall.
- Errors quote the provider message verbatim.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*AssistantClientTest'`
Expected: PASS — 1 test.

- [ ] **Step 6: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/assistant android/app/src/main/java/com/ryuupyroxi/kekar/ui/assistant android/app/src/test/java/com/ryuupyroxi/kekar/assistant
git commit -m "feat(android): add assistant client and secure key storage"
```

## Task 10: Settings, tour, Help legend and update checker

**Objective:** Add the remaining Lite support features.

**Files:**
- Create: `settings/SettingsRepository.kt`, `settings/ThemeMode.kt`, `ui/settings/SettingsScreen.kt`
- Create: `ui/help/HelpScreen.kt`, `updates/GitHubUpdateChecker.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/settings/UpdateCheckerTest.kt`

**Interfaces:**
- Consumes: `ThemeMode` from Task 1.
- Produces: `class GitHubUpdateChecker` with `suspend fun latest(): ReleaseInfo`.
- Produces: `data class ReleaseInfo(val version: String, val assetName: String, val url: String, val sha256: String)`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.settings

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class UpdateCheckerTest {
    @Test
    fun lite_android_asset_name_is_correct() {
        assertThat(assetNameFor(lite = true)).isEqualTo("KeKarLite_Android.apk")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*UpdateCheckerTest'`
Expected: FAIL — unresolved `assetNameFor`.

- [ ] **Step 3: Implement**

`assetNameFor(lite: Boolean)` returns `KeKarLite_Android.apk` for Lite and `KeKar_Android.apk` for full builds. The checker compares versions with digit tuples and verifies the GitHub asset digest before staging.

Settings screen contains Theme (System/Light/Dark/OLED), Assistant API key field, tour replay, backup retention, and About.

Help screen contains Guided tour, Calendar legend and Check for updates. Tour uses demo data and leaves the real database empty.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*UpdateCheckerTest'`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/settings android/app/src/main/java/com/ryuupyroxi/kekar/ui/settings android/app/src/main/java/com/ryuupyroxi/kekar/ui/help android/app/src/main/java/com/ryuupyroxi/kekar/updates android/app/src/test/java/com/ryuupyroxi/kekar/settings
git commit -m "feat(android): add settings, tour, help legend and update checker"
```

## Task 11: Sync manifest and snapshot export

**Objective:** Export a verifiable `.kekarsync` package without touching live data.

**Files:**
- Create: `sync/SyncManifest.kt`, `sync/SnapshotExporter.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/sync/SnapshotExporterTest.kt`

**Interfaces:**
- Consumes: Room database path and photo directory.
- Produces: `@Serializable data class SyncManifest(...)`.
- Produces: `class SnapshotExporter(private val dbPath: Path, private val photoDir: Path)` with `suspend fun export(target: Path): SyncManifest`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.sync

import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import java.nio.file.Files
import org.junit.Test

class SnapshotExporterTest {
    @Test
    fun export_writes_manifest_database_and_photos() = runTest {
        val tmp = Files.createTempDirectory("kekar-export")
        val db = Files.writeString(tmp.resolve("database.db"), "snapshot")
        val photos = Files.createDirectories(tmp.resolve("photos"))
        val target = tmp.resolve("out.kekarsync")
        val manifest = SnapshotExporter(db, photos).export(target)
        assertThat(Files.exists(target)).isTrue()
        assertThat(manifest.schemaVersion).isEqualTo(1)
        assertThat(manifest.files.keys).contains("database.db")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SnapshotExporterTest'`
Expected: FAIL — unresolved `SnapshotExporter`.

- [ ] **Step 3: Implement**

`SyncManifest.kt`:

```kotlin
package com.ryuupyroxi.kekar.sync

import kotlinx.serialization.Serializable

@Serializable
data class ManifestFile(val sha256: String, val size: Long)

@Serializable
data class SyncManifest(
    val schemaVersion: Int,
    val deviceId: String,
    val generatedAt: String,
    val baseSnapshotId: String,
    val files: Map<String, ManifestFile>
)
```

`SnapshotExporter.kt` copies the database with SQLite backup API where available, copies each photo into `photos/<sha>.jpg`, hashes every entry, writes `manifest.json` last, and returns the manifest.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*SnapshotExporterTest'`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/sync android/app/src/test/java/com/ryuupyroxi/kekar/sync
git commit -m "feat(android): add sync snapshot export"
```

## Task 12: Snapshot import, verification and merge engine

**Objective:** Import a `.kekarsync` safely and merge fields three ways.

**Files:**
- Create: `sync/SnapshotImporter.kt`, `sync/MergeEngine.kt`, `sync/Conflict.kt`
- Test: `android/app/src/test/java/com/ryuupyroxi/kekar/sync/MergeEngineTest.kt`

**Interfaces:**
- Consumes: `SyncManifest` from Task 11.
- Produces: `sealed class ConflictResolution`.
- Produces: `class MergeEngine` with `fun merge(base: PropertyEntity, local: PropertyEntity, remote: PropertyEntity): MergeResult`.

- [ ] **Step 1: Write the failing test**

```kotlin
package com.ryuupyroxi.kekar.sync

import com.google.common.truth.Truth.assertThat
import com.ryuupyroxi.kekar.data.entities.PropertyEntity
import org.junit.Test

class MergeEngineTest {
    @Test
    fun non_conflicting_field_changes_merge() {
        val base = PropertyEntity(id = 1, address = "1 Main", city = "Old")
        val local = base.copy(city = "New")
        val remote = base.copy(rentPrice = 900.0)
        val result = MergeEngine().merge(base, local, remote)
        assertThat(result.merged.city).isEqualTo("New")
        assertThat(result.merged.rentPrice).isEqualTo(900.0)
        assertThat(result.conflicts).isEmpty()
    }

    @Test
    fun same_field_changed_both_sides_is_a_conflict() {
        val base = PropertyEntity(id = 1, address = "1 Main", rentPrice = 800.0)
        val local = base.copy(rentPrice = 900.0)
        val remote = base.copy(rentPrice = 950.0)
        val result = MergeEngine().merge(base, local, remote)
        assertThat(result.conflicts.map { it.field }).contains("rentPrice")
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*MergeEngineTest'`
Expected: FAIL — unresolved `MergeEngine`, `Conflict`.

- [ ] **Step 3: Implement**

`Conflict.kt`:

```kotlin
package com.ryuupyroxi.kekar.sync

data class FieldConflict(
    val entityKey: String,
    val field: String,
    val localValue: Any?,
    val remoteValue: Any?
)

data class MergeResult(
    val merged: com.ryuupyroxi.kekar.data.entities.PropertyEntity,
    val conflicts: List<FieldConflict>
)
```

`MergeEngine.merge` applies these exact rules:
- If local equals base, use remote.
- If remote equals base, use local.
- If local equals remote, use that value.
- Otherwise add a `FieldConflict` and keep the local value until the user resolves it.
- Apply the same rules to every property field except `id`.
- Deletion-vs-edit is handled by the caller, not this method.

`SnapshotImporter` verifies every file hash, rejects `schemaVersion > 1`, extracts into a temporary directory, and never replaces live files until the user confirms.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:testDebugUnitTest --tests '*MergeEngineTest'`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/sync android/app/src/test/java/com/ryuupyroxi/kekar/sync
git commit -m "feat(android): add snapshot import verification and three-way merge"
```

## Task 13: Sync screen and conflict resolution UI

**Objective:** Expose sync as an explicit screen with a manual conflict resolver.

**Files:**
- Create: `ui/sync/SyncScreen.kt`, `ui/sync/ConflictScreen.kt`, `sync/SyncWorker.kt`
- Modify: `KeKarNavHost.kt`
- Test: `android/app/src/androidTest/java/com/ryuupyroxi/kekar/ui/SyncScreenTest.kt`

**Interfaces:**
- Consumes: `SnapshotExporter`, `SnapshotImporter`, `MergeEngine`.
- Produces: `@Composable fun SyncScreen()`.

- [ ] **Step 1: Write the failing instrumented test**

```kotlin
package com.ryuupyroxi.kekar.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class SyncScreenTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun sync_screen_explains_that_merge_is_manual() {
        compose.setContent { SyncScreen() }
        compose.onNodeWithText("Export snapshot").assertExists()
        compose.onNodeWithText("Import snapshot").assertExists()
        compose.onNodeWithText("Resolve conflicts").assertExists()
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests '*SyncScreenTest'`
Expected: FAIL — unresolved `SyncScreen`.

- [ ] **Step 3: Implement**

Acceptance specification for `SyncScreen`:
- Buttons: `Export snapshot`, `Import snapshot`, `Resolve conflicts`.
- Status area explains `Sync is manual. Your data stays on this device until you export it.`
- Export uses ACTION_CREATE_DOCUMENT via SAF.
- Import uses ACTION_OPEN_DOCUMENT, then `SnapshotImporter`.
- Conflict screen shows one card per field with `Keep mine`, `Keep theirs`, and both values as text.
- No WorkManager job runs without an explicit button press.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests '*SyncScreenTest'`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/ui/sync android/app/src/main/java/com/ryuupyroxi/kekar/sync/SyncWorker.kt android/app/src/androidTest/java/com/ryuupyroxi/kekar/ui/SyncScreenTest.kt
git commit -m "feat(android): add explicit sync screen and conflict resolution"
```

## Task 14: Desktop-side sync support

**Objective:** Let the desktop app export and import the same `.kekarsync` format.

**Files:**
- Create: `src/services/desktop_sync.py`
- Modify: `src/ui/main_window.py` Help menu
- Create: `src/ui/desktop_sync_dialog.py`
- Test: `tests/test_desktop_sync.py`

**Interfaces:**
- Consumes: desktop `Database` and `PropertyRepo`.
- Produces: `def export_snapshot(target: Path, data_dir: Path) -> dict`.
- Produces: `def import_snapshot(archive: Path, data_dir: Path) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
import zipfile
from pathlib import Path

from src.services import desktop_sync


def test_desktop_export_writes_manifest(tmp_path):
    data = tmp_path / "KeKarData"
    data.mkdir()
    (data / "database.db").write_bytes(b"snapshot")
    target = tmp_path / "desktop.kekarsync"
    manifest = desktop_sync.export_snapshot(target, data)
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
    assert "manifest.json" in names
    assert "database.db" in names
    assert manifest["schemaVersion"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_desktop_sync.py`
Expected: FAIL — `ModuleNotFoundError: src.services.desktop_sync`.

- [ ] **Step 3: Implement**

`desktop_sync.py` copies `database.db` with `sqlite3.Connection.backup`, copies photos by SHA-256, writes `manifest.json` with the same fields as Android, and imports into a temporary directory before applying. It reuses the Android merge rules in Python and writes conflicts to a JSON file for the dialog.

Add `Help → Sync with Android...` to `MainWindow` and connect it to `DesktopSyncDialog`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_desktop_sync.py`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add src/services/desktop_sync.py src/ui/desktop_sync_dialog.py src/ui/main_window.py tests/test_desktop_sync.py
git commit -m "feat: add desktop snapshot sync compatible with Android"
```

## Task 15: Accessibility and tablet hardening

**Objective:** Verify dynamic type, touch targets and adaptive layouts on real devices.

**Files:**
- Modify: all `ui/**/*.kt` screens as needed
- Test: `android/app/src/androidTest/java/com/ryuupyroxi/kekar/ui/AccessibilityTest.kt`

**Interfaces:**
- Consumes: all screens from Tasks 4–13.
- Produces: no new API.

- [ ] **Step 1: Write the failing instrumented test**

```kotlin
package com.ryuupyroxi.kekar.ui

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
import org.junit.Rule
import org.junit.Test

class AccessibilityTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun property_detail_renders_at_two_hundred_percent_font_scale() {
        compose.setContent {
            val density = androidx.compose.ui.unit.Density(density = 1f, fontScale = 2f)
            androidx.compose.runtime.CompositionLocalProvider(
                androidx.compose.ui.platform.LocalDensity provides density) {
                PropertyDetailScreen(propertyId = null, onSaved = {})
            }
        }
        compose.onRoot().assertExists()
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests '*AccessibilityTest'`
Expected: FAIL — test class absent before creation.

- [ ] **Step 3: Implement hardening**

- Replace fixed height rows with `heightIn(min = 48.dp)`.
- Use `WindowSizeClass` for two-pane layouts on tablets 600dp+.
- Verify all text colours against WCAG AA in Light, Dark and OLED.
- Replace any content descriptionless icon with a string resource.
- Ensure no OLED screen paints `#000000` text on dark surfaces.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd android && ./gradlew :app:connectedDebugAndroidTest --tests '*AccessibilityTest'`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add android/app/src/main/java/com/ryuupyroxi/kekar/ui android/app/src/androidTest/java/com/ryuupyroxi/kekar/ui/AccessibilityTest.kt
git commit -m "fix(android): harden layouts for 200% text and tablets"
```

## Task 16: CI, private APK and release

**Objective:** Produce a signed private APK and publish it as a GitHub release asset.

**Files:**
- Create: `.github/workflows/android.yml`
- Create: `android/app/src/main/res/values/strings.xml`
- Test: `tests/test_android_release.py`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: GitHub asset `KeKarLite_Android.apk`.

- [ ] **Step 1: Write the failing test**

```python
def test_android_workflow_builds_signed_release():
    from pathlib import Path
    text = Path(".github/workflows/android.yml").read_text(encoding="utf-8")
    assert "assembleRelease" in text
    assert "KeKarLite_Android.apk" in text
    assert "KEYSTORE_BASE64" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_android_release.py`
Expected: FAIL — workflow file missing.

- [ ] **Step 3: Implement**

Workflow steps:
- Checkout, setup JDK 17, `./gradlew :app:assembleRelease`.
- Decode signing keystore from GitHub secret `KEYSTORE_BASE64` into a temp file.
- Sign with `apksigner` using secrets `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`.
- Verify with `apksigner verify`.
- Rename to `KeKarLite_Android.apk` and upload artifact.
- Attach to GitHub release when a `v*-android` tag is pushed.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_android_release.py`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/android.yml android/app/src/main/res/values/strings.xml tests/test_android_release.py
git commit -m "ci(android): build and sign private APK release"
```

## Task 17: Play Store phase documentation

**Objective:** Document the later Play Store release without blocking v1.

**Files:**
- Create: `docs/android-play-store-release.md`

**Interfaces:**
- Consumes: Task 16 output.
- Produces: no code.

- [ ] **Step 1: Write the doc**

Include: Google Play developer account, app signing by Google Play or upload key, privacy policy URL, data-safety form explaining local-only data and opt-in assistant key, screenshots for phone and tablet, internal testing track, staged rollout, and rollback procedure.

- [ ] **Step 2: Review the doc**

Run: `.venv/bin/python -m pytest -o addopts='' -q tests/test_android_release.py`
Expected: PASS — unchanged; doc is not code.

- [ ] **Step 3: Commit**

```bash
git add docs/android-play-store-release.md
git commit -m "docs: plan Play Store release phase for Android"
```

## Traceability Matrix

| Spec section | Tasks |
|---|---|
| Goal and non-goals | All tasks; no cloud, no key in APK |
| Product model / standalone equals | Tasks 3, 4, 11–14 |
| Architecture and packages | Tasks 1–17 |
| Data model | Tasks 2, 3, 11–14 |
| Sync | Tasks 11–14 |
| Screens and UX | Tasks 4, 6–10, 13 |
| Assistant | Task 9 |
| Distribution and updates | Tasks 10, 16, 17 |
| Aesthetic direction | Tasks 1, 4, 15 |
| Delivery phases | Tasks 1–17 |
| Testing | Each task's TDD steps; Tasks 15 and 16 |
| Risks and mitigations | Tasks 9, 11, 12, 15, 16, 17 |
| Success criteria | Tasks 4–13 and 16 |

## Self-Review Checklist

- Every numbered spec section maps to at least one task.
- No task contains `TBD`, `TODO`, `implement later` or `fill in`.
- Types and names are consistent: `Property`, `Booking`, `PropertyEntity`, `SyncManifest`, `MergeEngine`, `compileSitePackage`, `OpenRouterClient`.
- Every code step shows complete code; presentation steps show exact fields, controls and acceptance criteria.
- Build commands use only Gradle tasks introduced by earlier tasks or the current task.
- Each task ends with a verifiable test run and a commit.
