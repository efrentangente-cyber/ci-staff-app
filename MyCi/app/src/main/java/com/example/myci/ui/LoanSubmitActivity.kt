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
import com.example.myci.data.LoanRepository
import com.example.myci.databinding.ActivityLoanSubmitBinding
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class LoanSubmitActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoanSubmitBinding
    private val pickedPaths = mutableListOf<String>()
    private var pendingCameraFile: File? = null

    private val gallery = registerForActivityResult(
        ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        uris?.forEach { uri -> copyContentToCache(uri)?.let { pickedPaths.add(it) } }
        binding.tvAttachCount.text = "Attachments: ${pickedPaths.size}"
    }

    private val camera = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            pendingCameraFile?.let { pickedPaths.add(it.absolutePath) }
        }
        binding.tvAttachCount.text = "Attachments: ${pickedPaths.size}"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoanSubmitBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnPickGallery.setOnClickListener { gallery.launch("image/*") }
        binding.btnTakePhoto.setOnClickListener { takePhoto() }
        binding.btnSubmit.setOnClickListener { submit() }
        binding.btnLoanOpenWeb.setOnClickListener {
            startActivity(WebAppIntents.createMainIntent(this, "/loan/submit", true))
        }
    }

    private fun takePhoto() {
        val ts = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val dir = File(filesDir, "evidence").also { it.mkdirs() }
        val out = File(dir, "JPEG_${ts}.jpg")
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
            val out = File(dir, "GAL_${ts}.jpg")
            contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(out).use { input.copyTo(it) }
            }
            out.absolutePath
        } catch (e: Exception) {
            null
        }
    }

    private fun submit() {
        val name = binding.etName.text?.toString()?.trim().orEmpty()
        val contact = binding.etContact.text?.toString()?.trim().orEmpty().takeIf { it.isNotEmpty() }
        val address = binding.etAddress.text?.toString()?.trim().orEmpty().takeIf { it.isNotEmpty() }
        val amount = binding.etAmount.text?.toString()?.trim()?.toDoubleOrNull()
        val needsCi = if (binding.cbNeedsCi.isChecked) 1 else 0
        if (name.isEmpty() || address == null || amount == null) {
            Toast.makeText(this, "Name, address and amount are required", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progress.visibility = View.VISIBLE
        binding.btnSubmit.isEnabled = false
        lifecycleScope.launch {
            withContext(Dispatchers.IO) {
                LoanRepository().createLoanOffline(
                    memberName = name,
                    memberContact = contact,
                    memberAddress = address,
                    loanAmount = amount,
                    needsCi = needsCi,
                    documentLocalPaths = pickedPaths.toList()
                )
            }
            Toast.makeText(
                this@LoanSubmitActivity,
                R.string.loan_submit_pending_toast,
                Toast.LENGTH_LONG
            ).show()
            finish()
        }
    }
}
