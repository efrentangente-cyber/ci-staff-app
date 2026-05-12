package com.example.myci.web

import android.content.Context
import android.content.Intent
import com.example.myci.MainActivity

/**
 * Deep-link the WebView shell to specific server routes and optionally bridge the native Bearer
 * token into a Flask cookie session (see [WebSessionSync] and server `/api/session_bridge`).
 */
object WebAppIntents {
    const val EXTRA_WEB_PATH = "com.example.myci.WEB_PATH"
    const val EXTRA_BRIDGE_SESSION = "com.example.myci.BRIDGE_SESSION"

    /** Same default dashboards as Flask `index` / role checks. */
    @JvmStatic
    fun pathForDashboardRole(role: String?): String {
        return when (role.orEmpty().lowercase()) {
            "admin" -> "/admin/dashboard"
            "ci_staff" -> "/ci/dashboard"
            else -> "/loan/dashboard"
        }
    }

    @JvmStatic
    fun createMainIntent(
        context: Context,
        webPath: String?,
        bridgeNativeSession: Boolean
    ): Intent {
        return Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            if (!webPath.isNullOrBlank()) {
                putExtra(EXTRA_WEB_PATH, webPath)
            }
            putExtra(EXTRA_BRIDGE_SESSION, bridgeNativeSession)
        }
    }
}
