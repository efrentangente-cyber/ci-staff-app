plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.example.myci"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.myci"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Room schema export — useful for tracking schema changes between releases.
        ksp {
            arg("room.schemaLocation", "$projectDir/schemas")
            arg("room.incremental", "true")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        // Required by every native activity (ActivityLoginBinding, ActivityHomeBinding, …).
        viewBinding = true
    }
}

dependencies {

    // --- Existing WebView shell deps ---
    implementation(libs.appcompat)
    implementation(libs.material)
    implementation(libs.activity)
    implementation(libs.constraintlayout)

    // --- Native rebuild: Kotlin stdlib + coroutines + lifecycle ---
    implementation(libs.core.ktx)
    implementation(libs.activity.ktx)
    implementation(libs.lifecycle.runtime.ktx)
    implementation(libs.lifecycle.viewmodel.ktx)
    implementation(libs.coroutines.core)
    implementation(libs.coroutines.android)

    // --- Native UI helpers (RecyclerView, swipe-refresh, cards) ---
    implementation(libs.recyclerview)
    implementation(libs.swiperefreshlayout)
    implementation(libs.cardview)
    implementation(libs.coordinatorlayout)

    // --- Local SQLite via Room (offline-first storage) ---
    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)

    // --- API sync layer: Retrofit + OkHttp + Moshi ---
    implementation(libs.retrofit)
    implementation(libs.retrofit.moshi)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.moshi)
    implementation(libs.moshi.kotlin)
    ksp(libs.moshi.codegen)

    // --- Background sync worker (drains pending queue when network returns) ---
    implementation(libs.work.runtime.ktx)

    // --- Token + role persistence ---
    implementation(libs.datastore.preferences)

    testImplementation(libs.junit)
    androidTestImplementation(libs.ext.junit)
    androidTestImplementation(libs.espresso.core)
}
