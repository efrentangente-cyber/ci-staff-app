package com.example.myci.web

import android.content.Context
import android.webkit.CookieManager
import com.example.myci.MyCiApp
import kotlinx.coroutines.runBlocking
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.concurrent.TimeUnit

/**
 * HTTP GET `/api/session_bridge?next=` with Bearer token — copies Set-Cookie into [CookieManager]
 * without following redirects so session headers are preserved.
 */
object WebSessionSync {

    @JvmStatic
    fun bridgeIfPossible(context: Context, baseUrl: String, nextPath: String): Boolean {
        val app = context.applicationContext as? MyCiApp ?: return false
        val token = runBlocking { app.tokenStore.currentToken() } ?: return false
        if (token.isBlank()) return false

        val path = normalizePath(nextPath) ?: "/loan/dashboard"

        val client = OkHttpClient.Builder()
            .callTimeout(30, TimeUnit.SECONDS)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .followRedirects(false)
            .followSslRedirects(false)
            .build()

        val trimmedBase = baseUrl.trimEnd('/')
        val qp = URLEncoder.encode(path, StandardCharsets.UTF_8.name())
        val url = "$trimmedBase/api/session_bridge?next=$qp"

        val req = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $token")
            .get()
            .build()

        return try {
            client.newCall(req).execute().use { resp ->
                val origin = "$trimmedBase/"
                applySetCookies(origin, resp)
                val code = resp.code
                // 302 / 303 from Flask redirect after login_user — cookies are what we need.
                code in 200..399
            }
        } catch (_: Exception) {
            false
        }
    }

    private fun normalizePath(raw: String): String? {
        var p = raw.trim()
        if (p.isEmpty()) return "/"
        if (!p.startsWith("/")) p = "/" + p
        if (p.startsWith("//")) return null
        return p
    }

    private fun applySetCookies(origin: String, response: Response) {
        val cm = CookieManager.getInstance()
        for (i in 0 until response.headers.size) {
            val name = response.headers.name(i)
            if (!name.equals("Set-Cookie", ignoreCase = true)) continue
            cm.setCookie(origin, response.headers.value(i))
        }
        cm.flush()
    }
}
