package com.example.myci.data.remote

import com.example.myci.data.auth.TokenStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

object Network {

    @Volatile private var apiCache: ApiService? = null
    @Volatile private var baseUrlCache: String? = null

    fun api(baseUrl: String, tokenStore: TokenStore): ApiService {
        val cached = apiCache
        if (cached != null && baseUrlCache == baseUrl) return cached
        synchronized(this) {
            val again = apiCache
            if (again != null && baseUrlCache == baseUrl) return again

            val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

            val log = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            }

            val authInterceptor = Interceptor { chain ->
                val token = runBlocking { tokenStore.currentToken() }
                val req = chain.request().newBuilder().apply {
                    header("Accept", "application/json")
                    if (!token.isNullOrBlank()) header("Authorization", "Bearer $token")
                }.build()
                chain.proceed(req)
            }

            val client = OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(60, TimeUnit.SECONDS)
                .retryOnConnectionFailure(true)
                .addInterceptor(authInterceptor)
                .addInterceptor(log)
                .build()

            val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
            val retrofit = Retrofit.Builder()
                .baseUrl(normalized)
                .client(client)
                .addConverterFactory(MoshiConverterFactory.create(moshi))
                .build()

            val svc = retrofit.create(ApiService::class.java)
            apiCache = svc
            baseUrlCache = baseUrl
            return svc
        }
    }
}

class HttpException(val statusCode: Int, message: String) : RuntimeException(message)

fun <T> Response.requireOk(): Response {
    if (!isSuccessful) throw HttpException(code, "HTTP $code")
    return this
}
