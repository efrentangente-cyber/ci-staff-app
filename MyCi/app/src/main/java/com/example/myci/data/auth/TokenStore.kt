package com.example.myci.data.auth

import android.util.Base64
import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import org.json.JSONObject

private val Context.dataStore by preferencesDataStore(name = "myci_auth")

/**
 * Token-based auth state. We deliberately avoid EncryptedSharedPreferences to keep
 * dependencies minimal; if you need device-bound encryption, swap to androidx.security.
 */
class TokenStore(private val context: Context) {

    private val keyToken = stringPreferencesKey("token")
    private val keyRole = stringPreferencesKey("role")
    private val keyUser = stringPreferencesKey("user_name")
    private val keyUserId = stringPreferencesKey("user_id")

    val token: Flow<String?> = context.dataStore.data.map { it[keyToken] }
    val role: Flow<String?> = context.dataStore.data.map { it[keyRole] }
    val userName: Flow<String?> = context.dataStore.data.map { it[keyUser] }

    /**
     * Persisted numeric user id, with JWT fallback so older installs still filter CI lists until next login.
     */
    val userId: Flow<Long?> = context.dataStore.data.map { prefs ->
        prefs[keyUserId]?.toLongOrNull()?.takeIf { it > 0 }
            ?: prefs[keyToken]?.let { parseSubFromMyCiToken(it) }
    }

    suspend fun currentToken(): String? = token.first()

    suspend fun save(token: String, role: String, userName: String, userId: Long) {
        context.dataStore.edit { prefs: androidx.datastore.preferences.core.MutablePreferences ->
            prefs[keyToken] = token
            prefs[keyRole] = role
            prefs[keyUser] = userName
            prefs[keyUserId] = userId.toString()
        }
    }

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }

    companion object {
        private fun parseSubFromMyCiToken(token: String): Long? {
            val body = token.substringBefore('.').trim()
            if (body.isEmpty()) return null
            return try {
                val pad = "=".repeat((4 - body.length % 4) % 4)
                val jsonBytes = Base64.decode(body + pad, Base64.URL_SAFE or Base64.NO_WRAP)
                val json = JSONObject(String(jsonBytes, Charsets.UTF_8))
                json.optLong("sub", -1L).takeIf { it > 0 }
            } catch (_: Exception) {
                null
            }
        }
    }
}
