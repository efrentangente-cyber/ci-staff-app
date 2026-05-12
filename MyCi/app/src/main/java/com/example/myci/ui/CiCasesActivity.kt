package com.example.myci.ui

import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.isVisible
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myci.MyCiApp
import com.example.myci.R
import com.example.myci.data.LoanRepository
import com.example.myci.data.local.LoanApplicationEntity
import com.example.myci.data.local.SyncStatus
import com.example.myci.databinding.ActivityCiCasesBinding
import com.example.myci.databinding.ItemCiCaseRowBinding
import com.example.myci.sync.runMobileSyncOnce
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * CI/BI dashboard aligned with `templates/ci_dashboard.html`: stats, Pending vs Completed sections,
 * filter field, and row actions similar to the web table (Start + pending-upload hint).
 */
class CiCasesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityCiCasesBinding
    private var latestAll: List<LoanApplicationEntity> = emptyList()
    private var searchQuery: String = ""

    private val adapterPending = CiCaseRowAdapter(
        showStartCta = true,
        onOpen = { openInterview(it) }
    )
    private val adapterCompleted = CiCaseRowAdapter(
        showStartCta = false,
        onOpen = { openInterview(it) }
    )

    private fun openInterview(loan: LoanApplicationEntity) {
        startActivity(
            Intent(this, CiInterviewActivity::class.java)
                .putExtra(CiInterviewActivity.EXTRA_LOAN_LOCAL_ID, loan.localId)
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCiCasesBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.recyclerPending.layoutManager = LinearLayoutManager(this)
        binding.recyclerPending.adapter = adapterPending
        binding.recyclerCompleted.layoutManager = LinearLayoutManager(this)
        binding.recyclerCompleted.adapter = adapterCompleted

        applyStat(
            binding.statCiTotal.tvStatLabel, binding.statCiTotal.statIconBg,
            binding.statCiTotal.ivStatIcon,
            label = getString(R.string.stat_total_assigned),
            iconBgDrawable = R.drawable.bg_stat_icon_blue, glyph = "📋"
        )
        applyStat(
            binding.statCiPending.tvStatLabel, binding.statCiPending.statIconBg,
            binding.statCiPending.ivStatIcon,
            label = getString(R.string.stat_pending_interview),
            iconBgDrawable = R.drawable.bg_stat_icon_yellow, glyph = "⏱"
        )
        applyStat(
            binding.statCiCompleted.tvStatLabel, binding.statCiCompleted.statIconBg,
            binding.statCiCompleted.ivStatIcon,
            label = getString(R.string.stat_completed),
            iconBgDrawable = R.drawable.bg_stat_icon_green, glyph = "✓"
        )
        applyStat(
            binding.statCiRate.tvStatLabel, binding.statCiRate.statIconBg,
            binding.statCiRate.ivStatIcon,
            label = getString(R.string.stat_completion_rate),
            iconBgDrawable = R.drawable.bg_stat_icon_yellow, glyph = "%"
        )

        binding.etSearch.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                searchQuery = s?.toString().orEmpty()
                applyFiltersAndBadges()
            }
        })

        binding.btnSyncNow.setOnClickListener {
            binding.btnSyncNow.isEnabled = false
            lifecycleScope.launch {
                val result = withContext(Dispatchers.IO) {
                    runMobileSyncOnce(MyCiApp.instance)
                }
                binding.btnSyncNow.isEnabled = true
                if (result.isSuccess) {
                    Toast.makeText(this@CiCasesActivity, R.string.ci_sync_saved_native, Toast.LENGTH_LONG).show()
                } else {
                    val msg = result.exceptionOrNull()?.message ?: "unknown error"
                    Toast.makeText(
                        this@CiCasesActivity,
                        getString(R.string.ci_sync_failed_prefix, msg),
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }

        binding.btnCiOpenWeb.setOnClickListener {
            startActivity(WebAppIntents.createMainIntent(this, "/ci/dashboard", true))
        }
        binding.btnCiLogout.setOnClickListener {
            lifecycleScope.launch {
                MyCiApp.instance.tokenStore.clear()
                startActivity(Intent(this@CiCasesActivity, LoginActivity::class.java))
                finish()
            }
        }

        lifecycleScope.launch {
            LoanRepository().observeCiDashboard().collectLatest { list ->
                latestAll = list
                applyFiltersAndBadges()
                refreshStats(list)
            }
        }
    }

    private fun applyFiltersAndBadges() {
        val q = searchQuery.trim().lowercase(Locale.getDefault())
        fun matches(loan: LoanApplicationEntity): Boolean {
            if (q.isEmpty()) return true
            val hay = listOf(
                loan.memberName,
                loan.memberAddress,
                loan.memberContact,
                loan.serverId?.toString(),
                loan.status,
                loan.loanStaffName,
                loan.loanType
            ).joinToString(" ").lowercase(Locale.getDefault())
            return hay.contains(q)
        }
        val pending = latestAll.filter { it.status == "assigned_to_ci" }.filter(::matches)
        val completed = latestAll.filter { it.status == "ci_completed" }.filter(::matches)
        adapterPending.submit(pending)
        adapterCompleted.submit(completed)
        binding.tvPendingBadge.text = getString(R.string.ci_badge_pending_fmt, pending.size)
        binding.tvCompletedBadge.text = getString(R.string.ci_badge_completed_fmt, completed.size)
    }

    private fun applyStat(
        tvLabel: android.widget.TextView,
        iconBgView: android.view.View,
        glyphView: android.widget.TextView,
        label: String,
        iconBgDrawable: Int,
        glyph: String
    ) {
        tvLabel.text = label
        glyphView.text = glyph
        iconBgView.background = ContextCompat.getDrawable(this, iconBgDrawable)
    }

    private fun refreshStats(list: List<LoanApplicationEntity>) {
        val total = list.size
        val pending = list.count { it.status == "assigned_to_ci" }
        val completed = list.count { it.status == "ci_completed" }
        val rate = if (total > 0) (completed.toDouble() / total * 100.0) else 0.0
        binding.statCiTotal.tvStatNumber.text = total.toString()
        binding.statCiPending.tvStatNumber.text = pending.toString()
        binding.statCiCompleted.tvStatNumber.text = completed.toString()
        binding.statCiRate.tvStatNumber.text = "${rate.toInt()}%"
    }

    private class CiCaseRowAdapter(
        private val showStartCta: Boolean,
        private val onOpen: (LoanApplicationEntity) -> Unit
    ) : RecyclerView.Adapter<CiCaseRowAdapter.VH>() {

        private val items = mutableListOf<LoanApplicationEntity>()
        private val df = SimpleDateFormat("dd-MM-yy", Locale.getDefault())

        fun submit(list: List<LoanApplicationEntity>) {
            items.clear()
            items.addAll(list)
            notifyDataSetChanged()
        }

        override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
            val b = ItemCiCaseRowBinding.inflate(
                android.view.LayoutInflater.from(parent.context), parent, false
            )
            return VH(b, showStartCta, onOpen)
        }

        override fun onBindViewHolder(holder: VH, position: Int) {
            holder.bind(items[position], df)
        }

        override fun getItemCount(): Int = items.size

        class VH(
            private val b: ItemCiCaseRowBinding,
            private val showStartCta: Boolean,
            private val onOpen: (LoanApplicationEntity) -> Unit
        ) : RecyclerView.ViewHolder(b.root) {

            fun bind(loan: LoanApplicationEntity, df: SimpleDateFormat) {
                val ctx = itemView.context
                b.tvAppId.text = loan.serverId?.let { "#$it" } ?: "—"
                b.tvName.text = loan.memberName
                b.tvAddress.text = loan.memberAddress?.takeIf { it.isNotBlank() } ?: "—"
                b.tvSubmitted.text = ctx.getString(
                    R.string.ci_row_submitted_fmt,
                    df.format(Date(loan.submittedAt))
                )
                b.tvAmount.text = loan.loanAmount?.let { a -> "₱${"%,.2f".format(a)}" } ?: "—"

                val (text, bg, fg) = when (loan.status) {
                    "ci_completed" -> Triple(ctx.getString(R.string.ci_status_completed_label), R.drawable.bg_status_success, R.color.status_success_text)
                    "assigned_to_ci" -> Triple(ctx.getString(R.string.ci_status_pending_label), R.drawable.bg_status_warning, R.color.status_warning_text)
                    else -> Triple(loan.status.replace('_', ' '), R.drawable.bg_status_info, R.color.status_info_text)
                }
                b.tvStatus.text = text
                b.tvStatus.setBackgroundResource(bg)
                b.tvStatus.setTextColor(ContextCompat.getColor(ctx, fg))

                val uploadPending = loan.status == "ci_completed" &&
                    loan.syncStatus != SyncStatus.SYNCED
                b.tvUploadPending.isVisible = uploadPending

                b.btnStartInterview.isVisible = showStartCta && loan.status == "assigned_to_ci"
                b.btnStartInterview.setOnClickListener { onOpen(loan) }
                b.root.setOnClickListener { onOpen(loan) }
            }
        }
    }
}
