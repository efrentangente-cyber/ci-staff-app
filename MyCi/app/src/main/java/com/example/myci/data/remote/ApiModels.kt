package com.example.myci.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(val email: String, val password: String)

@JsonClass(generateAdapter = true)
data class LoginResponse(
    val token: String,
    val role: String,
    val name: String,
    val userId: Long
)

@JsonClass(generateAdapter = true)
data class LoanApplicationDto(
    val id: Long? = null,
    val memberName: String,
    val memberContact: String? = null,
    val memberAddress: String? = null,
    val loanAmount: Double? = null,
    val needsCi: Int = 1,
    val status: String? = null,
    val assignedCiStaffId: Long? = null,
    val submittedAt: String? = null,
    val updatedAt: String? = null,
    val ciNotes: String? = null,
    val ciChecklistJson: String? = null,
    val ciCompletedAt: String? = null,
    val loanType: String? = null,
    val lpsRemarks: String? = null,
    val loanStaffName: String? = null
)

@JsonClass(generateAdapter = true)
data class CreateLoanResponse(
    val id: Long,
    val updatedAt: String
)

@JsonClass(generateAdapter = true)
data class UploadResponse(
    val fileId: Long,
    val loanApplicationId: Long
)

@JsonClass(generateAdapter = true)
data class SyncDeltaResponse(
    val loans: List<LoanApplicationDto> = emptyList(),
    val serverNow: String
)

@JsonClass(generateAdapter = true)
data class MeResponse(
    val id: Long,
    val name: String,
    val role: String
)
