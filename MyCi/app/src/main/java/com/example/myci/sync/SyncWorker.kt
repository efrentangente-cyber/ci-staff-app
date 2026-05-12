package com.example.myci.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.myci.MyCiApp
import com.example.myci.data.local.MemberEntity
import com.example.myci.data.local.PendingOpEntity
import com.example.myci.data.local.PendingOpType
import com.example.myci.data.local.SyncStatus
import com.example.myci.data.remote.LoanApplicationDto
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File

/**
 * Drains pending_ops in arrival order, then pulls a server delta and updates Room.
 * Server-wins: any server row replaces local fields except for entries still PENDING_*.
 */
class SyncWorker(appCtx: Context, params: WorkerParameters) : CoroutineWorker(appCtx, params) {

    private val app: MyCiApp get() = applicationContext as MyCiApp
    private val db get() = app.db
    private val api get() = app.api

    override suspend fun doWork(): Result {
        val token = app.tokenStore.currentToken()
        if (token.isNullOrBlank()) return Result.success()

        return try {
            drainPending()
            pullDelta()
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    private suspend fun drainPending() {
        val pendingDao = db.pendingOpDao()
        val ops = pendingDao.all()
        for (op in ops) {
            try {
                when (op.type) {
                    PendingOpType.CREATE_LOAN -> handleCreateLoan(op)
                    PendingOpType.UPLOAD_DOCUMENT -> handleUploadDocument(op)
                    PendingOpType.UPLOAD_CI_EVIDENCE -> handleUploadDocument(op)
                    PendingOpType.COMPLETE_CI -> handleCompleteCi(op)
                }
                pendingDao.delete(op.id)
            } catch (e: Exception) {
                pendingDao.bumpFailure(op.id, e.message ?: e::class.java.simpleName)
                if (op.attempts >= 5) {
                    db.loanApplicationDao().getByLocalId(op.targetLocalId)?.let { loan ->
                        db.loanApplicationDao().update(loan.copy(syncStatus = SyncStatus.FAILED))
                    }
                    pendingDao.delete(op.id)
                }
            }
        }
    }

    private suspend fun handleCreateLoan(op: PendingOpEntity) {
        val loan = db.loanApplicationDao().getByLocalId(op.targetLocalId) ?: return
        if (loan.serverId != null) return
        val json = JSONObject(op.payloadJson)
        val dto = LoanApplicationDto(
            memberName = json.optString("memberName"),
            memberContact = json.optString("memberContact").takeIf { it.isNotBlank() && it != "null" },
            memberAddress = json.optString("memberAddress").takeIf { it.isNotBlank() && it != "null" },
            loanAmount = if (json.isNull("loanAmount")) null else json.optDouble("loanAmount"),
            needsCi = json.optInt("needsCi", 1)
        )
        val resp = api.createLoan(op.idempotencyKey, dto)
        db.loanApplicationDao().markSynced(
            localId = loan.localId,
            serverId = resp.id,
            status = SyncStatus.SYNCED,
            serverUpdatedAt = parseServerMillis(resp.updatedAt)
        )
        // Carry the new server id onto pending uploads tied to this loan.
        db.documentDao().forLoan(loan.localId).forEach { doc ->
            if (doc.loanServerId == null) {
                val updated = doc.copy(loanServerId = resp.id)
                db.documentDao().insert(updated)
            }
        }
    }

    private suspend fun handleUploadDocument(op: PendingOpEntity) {
        val payload = JSONObject(op.payloadJson)
        val loanLocalId = payload.optLong("loanLocalId")
        val docId = payload.optLong("documentLocalId")
        val loan = db.loanApplicationDao().getByLocalId(loanLocalId)
            ?: throw IllegalStateException("missing parent loan for upload")
        val serverId = loan.serverId
            ?: throw IllegalStateException("loan not yet synced; will retry")
        val file = File(payload.optString("filePath"))
        if (!file.exists()) throw IllegalStateException("file vanished: ${file.path}")

        val media = (guessMime(file.name)).toMediaTypeOrNull()
        val part = MultipartBody.Part.createFormData("file", file.name, file.asRequestBody(media))
        val loanIdBody: RequestBody = serverId.toString().toRequestBody("text/plain".toMediaTypeOrNull())

        val resp = api.uploadDocument(op.idempotencyKey, loanIdBody, part)
        db.documentDao().markUploaded(docId, resp.fileId, resp.loanApplicationId)
    }

    private suspend fun handleCompleteCi(op: PendingOpEntity) {
        val loan = db.loanApplicationDao().getByLocalId(op.targetLocalId)
            ?: throw IllegalStateException("missing loan for COMPLETE_CI")
        val serverId = loan.serverId
            ?: throw IllegalStateException("loan not yet synced; will retry COMPLETE_CI later")

        val payload = JSONObject(op.payloadJson)
        val notes = if (payload.isNull("ciNotes")) "" else payload.optString("ciNotes")
        val checklist = if (payload.isNull("checklistJson")) "" else payload.optString("checklistJson")

        val text = "text/plain".toMediaTypeOrNull()
        val resp = api.completeCi(
            idempotencyKey = op.idempotencyKey,
            loanApplicationId = serverId.toString().toRequestBody(text),
            ciNotes = notes.toRequestBody(text),
            checklistData = checklist.toRequestBody(text)
        )
        db.loanApplicationDao().update(
            loan.copy(
                syncStatus = SyncStatus.SYNCED,
                serverUpdatedAt = parseServerMillis(resp.updatedAt)
            )
        )
    }

    private suspend fun pullDelta() {
        val resp = api.pullDelta(sinceIsoOrEmpty = "")
        // Cache members from loans (light "members" cache derived from server data).
        val members = resp.loans.map {
            MemberEntity(
                serverId = it.id,
                name = it.memberName,
                contact = it.memberContact,
                address = it.memberAddress
            )
        }
        if (members.isNotEmpty()) db.memberDao().upsertAll(members)

        // Server-wins for non-pending rows.
        applyLoanDtos(resp.loans)

        // For ci_staff, also pull cases assigned to them so the offline list is current.
        try {
            val assigned = api.ciAssigned()
            applyLoanDtos(assigned.loans)
        } catch (_: Exception) {
            // /api/ci/assigned is optional for non-CI roles (returns empty / 403); ignore.
        }
    }

    private suspend fun applyLoanDtos(loans: List<com.example.myci.data.remote.LoanApplicationDto>) {
        for (dto in loans) {
            val sid = dto.id ?: continue
            val existing = db.loanApplicationDao().getByServerId(sid)
            val submittedMillis = dto.submittedAt?.takeIf { it.isNotBlank() }?.let { parseServerMillis(it) }
                ?: parseServerMillis(dto.updatedAt)
            val serverMillis = parseServerMillis(dto.updatedAt ?: dto.submittedAt)
            val ciCompletedMillis =
                dto.ciCompletedAt?.takeIf { it.isNotBlank() }?.let { parseServerMillis(it) }
            if (existing == null) {
                db.loanApplicationDao().insert(
                    com.example.myci.data.local.LoanApplicationEntity(
                        serverId = sid,
                        memberName = dto.memberName,
                        memberContact = dto.memberContact,
                        memberAddress = dto.memberAddress,
                        loanAmount = dto.loanAmount,
                        needsCi = dto.needsCi,
                        status = dto.status ?: "submitted",
                        assignedCiStaffId = dto.assignedCiStaffId,
                        ciNotes = dto.ciNotes,
                        ciChecklistJson = dto.ciChecklistJson,
                        ciCompletedAt = ciCompletedMillis,
                        submittedAt = submittedMillis,
                        updatedAt = serverMillis,
                        syncStatus = SyncStatus.SYNCED,
                        serverUpdatedAt = serverMillis
                    )
                )
            } else if (existing.syncStatus == SyncStatus.SYNCED) {
                db.loanApplicationDao().update(
                    existing.copy(
                        memberName = dto.memberName,
                        memberContact = dto.memberContact,
                        memberAddress = dto.memberAddress,
                        loanAmount = dto.loanAmount,
                        needsCi = dto.needsCi,
                        status = dto.status ?: existing.status,
                        assignedCiStaffId = dto.assignedCiStaffId ?: existing.assignedCiStaffId,
                        ciNotes = dto.ciNotes ?: existing.ciNotes,
                        ciChecklistJson = dto.ciChecklistJson ?: existing.ciChecklistJson,
                        ciCompletedAt = ciCompletedMillis ?: existing.ciCompletedAt,
                        submittedAt = dto.submittedAt?.takeIf { it.isNotBlank() }?.let { parseServerMillis(it) }
                            ?: existing.submittedAt,
                        serverUpdatedAt = serverMillis
                    )
                )
            } else if (existing.syncStatus == SyncStatus.PENDING_UPDATE) {
                if (serverMillis > (existing.serverUpdatedAt ?: 0L)) {
                    db.loanApplicationDao().markConflict(existing.localId)
                }
            }
        }
    }

    /**
     * Server may send SQLite TEXT timestamps, ISO strings, or (rarely) numeric epochs in JSON.
     */
    private fun parseServerMillis(raw: String?): Long {
        if (raw.isNullOrBlank()) return System.currentTimeMillis()
        val t = raw.trim()
        if (t.all { it.isDigit() }) {
            val n = t.toLongOrNull() ?: return System.currentTimeMillis()
            return when {
                n > 315_532_800_000L -> n // already ms since ~1980
                n > 31_557_600L -> n * 1000L // unix seconds → ms
                else -> n * 1000L
            }
        }
        return parseIsoMillis(t)
    }

    private fun parseIsoMillis(iso: String): Long {
        if (iso.isBlank()) return System.currentTimeMillis()
        return try {
            val utc = java.util.TimeZone.getTimeZone("UTC")
            val withoutTz = iso.trim().substringBefore('.').replace(' ', 'T')
            val sdf = java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.US)
            sdf.timeZone = utc
            sdf.parse(withoutTz)?.time ?: System.currentTimeMillis()
        } catch (e: Exception) {
            try {
                val sdf = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.US)
                sdf.timeZone = java.util.TimeZone.getTimeZone("UTC")
                sdf.parse(iso.trim().substringBefore('.'))?.time ?: System.currentTimeMillis()
            } catch (e2: Exception) {
                System.currentTimeMillis()
            }
        }
    }

    private fun guessMime(name: String): String = when {
        name.endsWith(".pdf", true) -> "application/pdf"
        name.endsWith(".png", true) -> "image/png"
        name.endsWith(".webp", true) -> "image/webp"
        else -> "image/jpeg"
    }
}
