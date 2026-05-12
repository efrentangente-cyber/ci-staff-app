package com.example.myci

import android.app.Application
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.example.myci.data.auth.TokenStore
import com.example.myci.data.local.AppDatabase
import com.example.myci.data.remote.ApiService
import com.example.myci.data.remote.Network
import com.example.myci.sync.SyncWorker
import java.util.concurrent.TimeUnit

class MyCiApp : Application() {

    /**
     * Same host as [R.string.webapp_base_url] but **always** the site origin (no `/api` suffix).
     * WebView and cookie bridges use this; misconfiguration with a trailing `/api` is normalized away.
     */
    val siteOrigin: String by lazy { normalizeSiteOrigin(getString(R.string.webapp_base_url)) }

    /** Retrofit base = `{siteOrigin}/api` — matches Flask [mobile_api] blueprint prefix. */
    private val retrofitApiRoot: String by lazy { "${siteOrigin}/api" }

    val db: AppDatabase by lazy { AppDatabase.get(this) }
    val tokenStore: TokenStore by lazy { TokenStore(this) }
    val api: ApiService by lazy { Network.api(retrofitApiRoot, tokenStore) }

    private fun normalizeSiteOrigin(raw: String): String {
        var o = raw.trim().trimEnd('/')
        // Avoid https://host/api → double /api/api/… when combined with Retrofit paths.
        while (o.endsWith("/api")) {
            o = o.removeSuffix("/api")
        }
        return o.trimEnd('/')
    }

    override fun onCreate() {
        super.onCreate()
        instance = this

        // Periodic sync ~15 min when network is available; opportunistic enqueue happens on writes too.
        val req = PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "myci-periodic-sync",
            ExistingPeriodicWorkPolicy.KEEP,
            req
        )
    }

    companion object {
        @Volatile lateinit var instance: MyCiApp
            private set
    }
}
