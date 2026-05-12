package com.example.myci.data.auth

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "myci_auth")

/**
 * Token-based auth state. We deliberately avoid EncryptedSharedPreferences to keep
 * dependencies minimal; if you need device-bound encryption, swap to androidx.security.
 */
class TokenStore(private val context: Context) {

    private val keyToken = stringPreferencesKey("token")
    private val keyRole = stringPreferencesKey("role")
    private val keyUser = stringPreferencesKey("user_name")

    val token: Flow<String?> = context.dataStore.data.map { it[keyToken] }
    val role: Flow<String?> = context.dataStore.data.map { it[keyRole] }
    val userName: Flow<String?> = context.dataStore.data.map { it[keyUser] }

    suspend fun currentToken(): String? = token.first()

    suspend fun save(token: String, role: String, userName: String) {
        context.dataStore.edit { prefs: androidx.datastore.preferences.core.MutablePreferences ->
            prefs[keyToken] = token
            prefs[keyRole] = role
            prefs[keyUser] = userName
        }
    }

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }
}
