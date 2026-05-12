package com.example.myci.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.myci.MyCiApp

/**
 * Periodic / background sync: drains pending_ops then pulls server rows into Room.
 */
class SyncWorker(appCtx: Context, params: WorkerParameters) : CoroutineWorker(appCtx, params) {

    private val app: MyCiApp get() = applicationContext as MyCiApp

    override suspend fun doWork(): androidx.work.ListenableWorker.Result {
        val token = app.tokenStore.currentToken()
        if (token.isNullOrBlank()) return androidx.work.ListenableWorker.Result.success()

        return try {
            MobileSyncEngine(app).runFullSync()
            androidx.work.ListenableWorker.Result.success()
        } catch (_: Exception) {
            androidx.work.ListenableWorker.Result.retry()
        }
    }
}
