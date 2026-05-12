package com.example.myci.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Mirrors the website's loan_applications row but adds offline bookkeeping:
 * - localId: stable id used while we don't yet have a server id
 * - serverId: filled after first successful sync (nullable)
 * - syncStatus: SYNCED / PENDING_CREATE / PENDING_UPDATE / FAILED / CONFLICT
 * - updatedAt: last local modification (millis)
 * - serverUpdatedAt: last server-known version timestamp; used for server-wins resolution
 */
@Entity(
    tableName = "loan_applications",
    indices = [Index(value = ["serverId"], unique = true)]
)
data class LoanApplicationEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val serverId: Long? = null,
    val memberName: String,
    val memberContact: String?,
    val memberAddress: String?,
    val loanAmount: Double?,
    val needsCi: Int = 1,
    val status: String = "submitted",
    val assignedCiStaffId: Long? = null,
    val submittedAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val serverUpdatedAt: Long? = null,
    val syncStatus: String = SyncStatus.PENDING_CREATE,
    val isConflict: Boolean = false,
    // CI completion fields (mirror website columns: ci_notes, ci_checklist_data, ci_completed_at)
    val ciNotes: String? = null,
    val ciChecklistJson: String? = null,
    val ciCompletedAt: Long? = null
)

@Entity(
    tableName = "documents",
    indices = [Index("loanLocalId"), Index("loanServerId")]
)
data class DocumentEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val loanLocalId: Long,
    val loanServerId: Long? = null,
    val fileName: String,
    val localFilePath: String,
    val serverFileId: Long? = null,
    val syncStatus: String = SyncStatus.PENDING_CREATE
)

/**
 * Cached member info so common lookups work offline.
 */
@Entity(tableName = "members", indices = [Index(value = ["serverId"], unique = true)])
data class MemberEntity(
    @PrimaryKey(autoGenerate = true) val localId: Long = 0,
    val serverId: Long? = null,
    val name: String,
    val contact: String?,
    val address: String?,
    val updatedAt: Long = System.currentTimeMillis()
)

/**
 * Generic outbound queue. Each row represents one mutation to replay against the API.
 * idempotencyKey is sent as a header so retries don't create duplicates server-side.
 */
@Entity(tableName = "pending_ops")
data class PendingOpEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val type: String,
    val targetTable: String,
    val targetLocalId: Long,
    val payloadJson: String,
    val idempotencyKey: String,
    val attempts: Int = 0,
    val lastError: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)

object SyncStatus {
    const val SYNCED = "SYNCED"
    const val PENDING_CREATE = "PENDING_CREATE"
    const val PENDING_UPDATE = "PENDING_UPDATE"
    const val FAILED = "FAILED"
    const val CONFLICT = "CONFLICT"
}

object PendingOpType {
    const val CREATE_LOAN = "CREATE_LOAN"
    const val UPDATE_LOAN = "UPDATE_LOAN"
    const val UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    const val COMPLETE_CI = "COMPLETE_CI"
    const val UPLOAD_CI_EVIDENCE = "UPLOAD_CI_EVIDENCE"
}
