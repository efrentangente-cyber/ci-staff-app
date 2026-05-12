package com.example.myci.data.remote

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Query

interface ApiService {

    @POST("login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("me")
    suspend fun me(): MeResponse

    @POST("loan_applications")
    suspend fun createLoan(
        @Header("Idempotency-Key") idempotencyKey: String,
        @Body body: LoanApplicationDto
    ): CreateLoanResponse

    @Multipart
    @POST("upload")
    suspend fun uploadDocument(
        @Header("Idempotency-Key") idempotencyKey: String,
        @Part("loan_application_id") loanApplicationId: RequestBody,
        @Part file: MultipartBody.Part
    ): UploadResponse

    @GET("sync")
    suspend fun pullDelta(@Query("since") sinceIsoOrEmpty: String): SyncDeltaResponse

    @GET("ci/assigned")
    suspend fun ciAssigned(): SyncDeltaResponse

    @Multipart
    @POST("ci/complete")
    suspend fun completeCi(
        @Header("Idempotency-Key") idempotencyKey: String,
        @Part("loan_application_id") loanApplicationId: RequestBody,
        @Part("ci_notes") ciNotes: RequestBody,
        @Part("checklist_data") checklistData: RequestBody
    ): CreateLoanResponse
}
