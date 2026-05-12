package com.example.myci.ui

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.core.view.isVisible
import androidx.lifecycle.lifecycleScope
import com.example.myci.MyCiApp
import com.example.myci.R
import com.example.myci.data.LoanRepository
import com.example.myci.data.local.LoanApplicationEntity
import com.example.myci.data.local.SyncStatus
import com.example.myci.databinding.ActivityCiInterviewBinding
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Native flow aligned with web `ci_review_application.html` + checklist/evidence steps.
 * Submit queues offline operations; [LoanRepository.completeCiOffline] marks pending until sync.
 */
class CiInterviewActivity : AppCompatActivity() {

    private lateinit var binding: ActivityCiInterviewBinding
    private var loanLocalId: Long = -1L
    private val photos = mutableListOf<String>()
    private var pendingCameraFile: File? = null
    private var readOnly: Boolean = false

    private val detailDf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())

    private val gallery = registerForActivityResult(
        ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        if (readOnly) return@registerForActivityResult
        uris?.forEach { uri -> copyContentToCache(uri)?.let { photos.add(it) } }
        binding.tvPhotos.text = getString(R.string.ci_photos_count_fmt, photos.size)
    }

    private val camera = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (readOnly) return@registerForActivityResult
        if (result.resultCode == Activity.RESULT_OK) {
            pendingCameraFile?.let { photos.add(it.absolutePath) }
        }
        binding.tvPhotos.text = getString(R.string.ci_photos_count_fmt, photos.size)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCiInterviewBinding.inflate(layoutInflater)
        setContentView(binding.root)

        loanLocalId = intent.getLongExtra(EXTRA_LOAN_LOCAL_ID, -1L)
        if (loanLocalId < 0) {
            finish()
            return
        }

        binding.btnCiBack.setOnClickListener { finish() }

        lifecycleScope.launch {
            val loan = withContext(Dispatchers.IO) {
                MyCiApp.instance.db.loanApplicationDao().getByLocalId(loanLocalId)
            }
            bindLoan(loan)
        }

        binding.btnGallery.setOnClickListener {
            if (!readOnly) gallery.launch("image/*")
        }
        binding.btnCamera.setOnClickListener {
            if (!readOnly) takePhoto()
        }
        binding.btnOpenCaseInWeb.setOnClickListener {
            lifecycleScope.launch {
                val loan = withContext(Dispatchers.IO) {
                    MyCiApp.instance.db.loanApplicationDao().getByLocalId(loanLocalId)
                }
                val sid = loan?.serverId
                val path = if (sid != null) "/ci/review/$sid" else "/ci/dashboard"
                startActivity(WebAppIntents.createMainIntent(this@CiInterviewActivity, path, true))
            }
        }
        binding.btnComplete.setOnClickListener {
            if (!readOnly) complete()
        }
    }

    private fun bindLoan(loan: LoanApplicationEntity?) {
        if (loan == null) {
            finish()
            return
        }
        readOnly = loan.status == "ci_completed" && loan.syncStatus == SyncStatus.SYNCED

        binding.tvReadOnlyBanner.isVisible = readOnly
        binding.etNotes.isEnabled = !readOnly
        binding.cbResidenceConfirmed.isEnabled = !readOnly
        binding.cbIncomeVerified.isEnabled = !readOnly
        binding.cbCharacterReferenceOk.isEnabled = !readOnly
        binding.cbRecommendApprove.isEnabled = !readOnly
        binding.btnGallery.isEnabled = !readOnly
        binding.btnCamera.isEnabled = !readOnly
        binding.btnComplete.isEnabled = !readOnly

        binding.tvDetailSubtitle.text = buildString {
            append(loan.memberName)
            append(" · ")
            append(loan.loanAmount?.let { a -> "₱${"%,.2f".format(a)}" } ?: getString(R.string.ci_na))
        }
        binding.tvDetailAppId.text = loan.serverId?.let { "#$it" } ?: getString(R.string.ci_na)
        binding.tvDetailStatus.text = humanizeStatus(loan.status)
        binding.tvDetailMember.text = loan.memberName
        binding.tvDetailContact.text = loan.memberContact?.takeIf { it.isNotBlank() } ?: getString(R.string.ci_na)
        binding.tvDetailAddress.text = loan.memberAddress?.takeIf { it.isNotBlank() } ?: getString(R.string.ci_na)
        binding.tvDetailAmount.text = loan.loanAmount?.let { a -> "₱${"%,.2f".format(a)}" } ?: getString(R.string.ci_na)
        binding.tvDetailLoanType.text = loan.loanType?.takeIf { it.isNotBlank() } ?: getString(R.string.ci_na)
        binding.tvDetailSubmittedBy.text = loan.loanStaffName?.takeIf { it.isNotBlank() } ?: getString(R.string.ci_na)
        binding.tvDetailSubmittedAt.text = detailDf.format(Date(loan.submittedAt))

        val lps = loan.lpsRemarks?.trim().orEmpty()
        binding.rowLpsRemarks.isVisible = lps.isNotEmpty()
        binding.tvDetailLpsRemarks.text = if (lps.isNotEmpty()) lps else ""

        binding.etNotes.setText(loan.ciNotes.orEmpty())
        loan.ciChecklistJson?.let { js ->
            try {
                val o = JSONObject(js)
                binding.cbResidenceConfirmed.isChecked = o.optBoolean("residenceConfirmed", false)
                binding.cbIncomeVerified.isChecked = o.optBoolean("incomeVerified", false)
                binding.cbCharacterReferenceOk.isChecked = o.optBoolean("characterReferenceOk", false)
                binding.cbRecommendApprove.isChecked = o.optBoolean("recommendApprove", false)
            } catch (_: Exception) {
            }
        }
        binding.tvPhotos.text = getString(R.string.ci_photos_count_fmt, photos.size)
    }

    private fun humanizeStatus(status: String?): String {
        if (status.isNullOrBlank()) return getString(R.string.ci_na)
        return status.replace('_', ' ').split(' ').joinToString(" ") { word ->
            word.replaceFirstChar { ch ->
                if (ch.isLowerCase()) ch.titlecase(Locale.getDefault()) else ch.toString()
            }
        }
    }

    private fun complete() {
        val notes = binding.etNotes.text?.toString()?.trim().orEmpty()
        val checklist = JSONObject().apply {
            put("residenceConfirmed", binding.cbResidenceConfirmed.isChecked)
            put("incomeVerified", binding.cbIncomeVerified.isChecked)
            put("characterReferenceOk", binding.cbCharacterReferenceOk.isChecked)
            put("recommendApprove", binding.cbRecommendApprove.isChecked)
        }.toString()

        binding.progress.visibility = View.VISIBLE
        binding.btnComplete.isEnabled = false
        lifecycleScope.launch {
            withContext(Dispatchers.IO) {
                LoanRepository().completeCiOffline(
                    loanLocalId = loanLocalId,
                    ciNotes = notes,
                    checklistJson = checklist,
                    evidencePhotoPaths = photos.toList()
                )
            }
            Toast.makeText(this@CiInterviewActivity, R.string.ci_complete_toast, Toast.LENGTH_LONG).show()
            finish()
        }
    }

    private fun takePhoto() {
        val ts = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val dir = File(filesDir, "evidence").also { it.mkdirs() }
        val out = File(dir, "CI_${ts}.jpg")
        pendingCameraFile = out
        val uri = FileProvider.getUriForFile(this, "com.example.myci.fileprovider", out)
        val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
            putExtra(MediaStore.EXTRA_OUTPUT, uri)
            addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        }
        camera.launch(intent)
    }

    private fun copyContentToCache(uri: Uri): String? {
        return try {
            val ts = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
            val dir = File(filesDir, "evidence").also { it.mkdirs() }
            val out = File(dir, "CIGAL_${ts}.jpg")
            contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(out).use { input.copyTo(it) }
            }
            out.absolutePath
        } catch (_: Exception) {
            null
        }
    }

    companion object {
        const val EXTRA_LOAN_LOCAL_ID = "extra_loan_local_id"
    }
}
