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
import androidx.lifecycle.lifecycleScope
import com.example.myci.MyCiApp
import com.example.myci.data.LoanRepository
import com.example.myci.databinding.ActivityCiInterviewBinding
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Native CI interview form. Mirrors the website fields: notes + a flexible JSON checklist
 * (here represented as labeled radios for now; the JSON shape is open for future fields).
 * Saves locally and queues sync; works fully offline.
 */
class CiInterviewActivity : AppCompatActivity() {

    private lateinit var binding: ActivityCiInterviewBinding
    private var loanLocalId: Long = -1L
    private val photos = mutableListOf<String>()
    private var pendingCameraFile: File? = null

    private val gallery = registerForActivityResult(
        ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        uris?.forEach { uri -> copyContentToCache(uri)?.let { photos.add(it) } }
        binding.tvPhotos.text = "Photos: ${photos.size}"
    }

    private val camera = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            pendingCameraFile?.let { photos.add(it.absolutePath) }
        }
        binding.tvPhotos.text = "Photos: ${photos.size}"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCiInterviewBinding.inflate(layoutInflater)
        setContentView(binding.root)

        loanLocalId = intent.getLongExtra(EXTRA_LOAN_LOCAL_ID, -1L)
        if (loanLocalId < 0) { finish(); return }

        lifecycleScope.launch {
            val loan = MyCiApp.instance.db.loanApplicationDao().getByLocalId(loanLocalId)
            binding.tvTitle.text = loan?.let { "${it.memberName} · ₱${it.loanAmount ?: "—"}" } ?: "(loan)"
            binding.etNotes.setText(loan?.ciNotes.orEmpty())
            // Try to pre-fill the small checklist if a JSON was already stored.
            loan?.ciChecklistJson?.let { js ->
                try {
                    val o = JSONObject(js)
                    binding.cbResidenceConfirmed.isChecked = o.optBoolean("residenceConfirmed", false)
                    binding.cbIncomeVerified.isChecked = o.optBoolean("incomeVerified", false)
                    binding.cbCharacterReferenceOk.isChecked = o.optBoolean("characterReferenceOk", false)
                    binding.cbRecommendApprove.isChecked = o.optBoolean("recommendApprove", false)
                } catch (_: Exception) { }
            }
        }

        binding.btnGallery.setOnClickListener { gallery.launch("image/*") }
        binding.btnCamera.setOnClickListener { takePhoto() }
        binding.btnOpenCaseInWeb.setOnClickListener {
            lifecycleScope.launch {
                val loan = MyCiApp.instance.db.loanApplicationDao().getByLocalId(loanLocalId)
                val sid = loan?.serverId
                val path = if (sid != null) "/ci/application/$sid" else "/ci/dashboard"
                startActivity(WebAppIntents.createMainIntent(this@CiInterviewActivity, path, true))
            }
        }
        binding.btnComplete.setOnClickListener { complete() }
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
            LoanRepository().completeCiOffline(
                loanLocalId = loanLocalId,
                ciNotes = notes,
                checklistJson = checklist,
                evidencePhotoPaths = photos.toList()
            )
            Toast.makeText(
                this@CiInterviewActivity,
                "Interview saved offline. Will send to admin when online.",
                Toast.LENGTH_LONG
            ).show()
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
        } catch (e: Exception) { null }
    }

    companion object {
        const val EXTRA_LOAN_LOCAL_ID = "extra_loan_local_id"
    }
}
