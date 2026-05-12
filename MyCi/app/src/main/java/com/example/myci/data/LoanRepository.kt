package com.example.myci.data

import android.content.Context
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.example.myci.MyCiApp
import com.example.myci.data.local.DocumentEntity
import com.example.myci.data.local.LoanApplicationEntity
import com.example.myci.data.local.PendingOpEntity
import com.example.myci.data.local.PendingOpType
import com.example.myci.data.local.SyncStatus
import com.example.myci.sync.SyncWorker
import kotlinx.coroutines.flow.Flow
import org.json.JSONObject
import java.util.UUID

class LoanRepository(private val app: MyCiApp = MyCiApp.instance) {

    private val loanDao = app.db.loanApplicationDao()
    private val docDao = app.db.documentDao()
    private val pendingDao = app.db.pendingOpDao()

    fun observeLoans(): Flow<List<LoanApplicationEntity>> = loanDao.observeAll()

    fun observeCiAssigned(userId: Long): Flow<List<LoanApplicationEntity>> =
        loanDao.observeAssignedToMe(userId)

    /**
     * Server already filtered /api/ci/assigned by the current user; locally we just want any
     * row whose status is 'assigned_to_ci' regardless of which user_id stored it.
     */
    fun observeCiAssignedAnyone(): Flow<List<LoanApplicationEntity>> =
        kotlinx.coroutines.flow.flow {
            loanDao.observeAll().collect { list ->
                emit(
                    list.filter {
                        it.status == "assigned_to_ci" || it.status == "ci_completed"
                    }
                )
            }
        }

    fun observeConflicts(): Flow<List<LoanApplicationEntity>> = loanDao.observeConflicts()

    suspend fun pendingOps(): List<com.example.myci.data.local.PendingOpEntity> =
        pendingDao.all()

    /**
     * Create a loan locally, enqueue a CREATE_LOAN op + UPLOAD_DOCUMENT ops for each photo,
     * then kick the SyncWorker. Returns the new local id so callers can navigate immediately.
     */
    suspend fun createLoanOffline(
        memberName: String,
        memberContact: String?,
        memberAddress: String?,
        loanAmount: Double?,
        needsCi: Int,
        documentLocalPaths: List<String>
    ): Long {
        val loan = LoanApplicationEntity(
            memberName = memberName,
            memberContact = memberContact,
            memberAddress = memberAddress,
            loanAmount = loanAmount,
            needsCi = needsCi,
            status = "submitted",
            syncStatus = SyncStatus.PENDING_CREATE
        )
        val localId = loanDao.insert(loan)

        val payload = JSONObject().apply {
            put("memberName", memberName)
            put("memberContact", memberContact ?: JSONObject.NULL)
            put("memberAddress", memberAddress ?: JSONObject.NULL)
            put("loanAmount", loanAmount ?: JSONObject.NULL)
            put("needsCi", needsCi)
        }
        pendingDao.insert(
            PendingOpEntity(
                type = PendingOpType.CREATE_LOAN,
                targetTable = "loan_applications",
                targetLocalId = localId,
                payloadJson = payload.toString(),
                idempotencyKey = UUID.randomUUID().toString()
            )
        )

        documentLocalPaths.forEach { path ->
            val docId = docDao.insert(
                DocumentEntity(
                    loanLocalId = localId,
                    fileName = path.substringAfterLast('/'),
                    localFilePath = path
                )
            )
            val docPayload = JSONObject().apply {
                put("loanLocalId", localId)
                put("documentLocalId", docId)
                put("filePath", path)
            }
            pendingDao.insert(
                PendingOpEntity(
                    type = PendingOpType.UPLOAD_DOCUMENT,
                    targetTable = "documents",
                    targetLocalId = docId,
                    payloadJson = docPayload.toString(),
                    idempotencyKey = UUID.randomUUID().toString()
                )
            )
        }

        kickSync(app)
        return localId
    }

    /**
     * Save a CI interview locally, mark loan ci_completed, enqueue COMPLETE_CI op +
     * UPLOAD_CI_EVIDENCE ops for each photo. Works fully offline.
     */
    suspend fun completeCiOffline(
        loanLocalId: Long,
        ciNotes: String?,
        checklistJson: String?,
        evidencePhotoPaths: List<String>
    ) {
        val loan = loanDao.getByLocalId(loanLocalId) ?: return
        val now = System.currentTimeMillis()
        val updated = loan.copy(
            ciNotes = ciNotes,
            ciChecklistJson = checklistJson,
            ciCompletedAt = now,
            status = "ci_completed",
            updatedAt = now,
            // Force PENDING_UPDATE so the worker picks it up.
            syncStatus = if (loan.serverId == null) SyncStatus.PENDING_CREATE else SyncStatus.PENDING_UPDATE
        )
        loanDao.update(updated)

        val payload = JSONObject().apply {
            put("loanLocalId", loanLocalId)
            put("loanServerId", loan.serverId ?: JSONObject.NULL)
            put("ciNotes", ciNotes ?: JSONObject.NULL)
            put("checklistJson", checklistJson ?: JSONObject.NULL)
        }
        pendingDao.insert(
            PendingOpEntity(
                type = PendingOpType.COMPLETE_CI,
                targetTable = "loan_applications",
                targetLocalId = loanLocalId,
                payloadJson = payload.toString(),
                idempotencyKey = UUID.randomUUID().toString()
            )
        )

        evidencePhotoPaths.forEach { path ->
            val docId = docDao.insert(
                DocumentEntity(
                    loanLocalId = loanLocalId,
                    loanServerId = loan.serverId,
                    fileName = path.substringAfterLast('/'),
                    localFilePath = path
                )
            )
            val docPayload = JSONObject().apply {
                put("loanLocalId", loanLocalId)
                put("documentLocalId", docId)
                put("filePath", path)
            }
            pendingDao.insert(
                PendingOpEntity(
                    type = PendingOpType.UPLOAD_CI_EVIDENCE,
                    targetTable = "documents",
                    targetLocalId = docId,
                    payloadJson = docPayload.toString(),
                    idempotencyKey = UUID.randomUUID().toString()
                )
            )
        }

        kickSync(app)
    }

    companion object {
        fun kickSync(context: Context) {
            WorkManager.getInstance(context).enqueue(
                OneTimeWorkRequestBuilder<SyncWorker>().build()
            )
        }
    }
}
