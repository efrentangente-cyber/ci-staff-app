package com.example.myci.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface LoanApplicationDao {

    @Query("SELECT * FROM loan_applications ORDER BY submittedAt DESC")
    fun observeAll(): Flow<List<LoanApplicationEntity>>

    @Query("SELECT * FROM loan_applications WHERE localId = :localId LIMIT 1")
    suspend fun getByLocalId(localId: Long): LoanApplicationEntity?

    @Query("SELECT * FROM loan_applications WHERE serverId = :serverId LIMIT 1")
    suspend fun getByServerId(serverId: Long): LoanApplicationEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(loan: LoanApplicationEntity): Long

    @Update
    suspend fun update(loan: LoanApplicationEntity)

    @Query("UPDATE loan_applications SET serverId = :serverId, syncStatus = :status, serverUpdatedAt = :serverUpdatedAt WHERE localId = :localId")
    suspend fun markSynced(localId: Long, serverId: Long, status: String, serverUpdatedAt: Long)

    @Query("UPDATE loan_applications SET syncStatus = :status, isConflict = :isConflict WHERE localId = :localId")
    suspend fun markConflict(localId: Long, status: String = SyncStatus.CONFLICT, isConflict: Boolean = true)

    @Query("SELECT * FROM loan_applications WHERE assignedCiStaffId = :userId AND status = 'assigned_to_ci' ORDER BY submittedAt DESC")
    fun observeAssignedToMe(userId: Long): Flow<List<LoanApplicationEntity>>

    @Query("SELECT * FROM loan_applications WHERE isConflict = 1")
    fun observeConflicts(): Flow<List<LoanApplicationEntity>>
}

@Dao
interface DocumentDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(doc: DocumentEntity): Long

    @Query("SELECT * FROM documents WHERE loanLocalId = :loanLocalId")
    suspend fun forLoan(loanLocalId: Long): List<DocumentEntity>

    @Query("UPDATE documents SET serverFileId = :serverFileId, syncStatus = :status, loanServerId = :loanServerId WHERE localId = :localId")
    suspend fun markUploaded(localId: Long, serverFileId: Long, loanServerId: Long, status: String = SyncStatus.SYNCED)
}

@Dao
interface MemberDao {

    @Query("SELECT * FROM members ORDER BY name ASC")
    fun observeAll(): Flow<List<MemberEntity>>

    @Query("SELECT * FROM members WHERE name LIKE '%' || :q || '%' OR address LIKE '%' || :q || '%' LIMIT 25")
    suspend fun search(q: String): List<MemberEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(members: List<MemberEntity>)
}

@Dao
interface PendingOpDao {

    @Insert
    suspend fun insert(op: PendingOpEntity): Long

    @Query("SELECT * FROM pending_ops ORDER BY id ASC")
    suspend fun all(): List<PendingOpEntity>

    @Query("DELETE FROM pending_ops WHERE id = :id")
    suspend fun delete(id: Long)

    @Query("UPDATE pending_ops SET attempts = attempts + 1, lastError = :err WHERE id = :id")
    suspend fun bumpFailure(id: Long, err: String)
}
