package com.example.myci.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myci.MyCiApp
import com.example.myci.R
import com.example.myci.data.LoanRepository
import com.example.myci.data.local.LoanApplicationEntity
import com.example.myci.databinding.ActivityHomeBinding
import com.example.myci.databinding.ItemLoanRowBinding
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Loan Staff Dashboard. Mirrors the website's `loan_dashboard.html`:
 * top bar with greeting, stat-card grid summarising the local loan table,
 * "Applications" content card with the recycler, and a bottom sync/web/logout strip.
 */
class HomeActivity : androidx.appcompat.app.AppCompatActivity() {

    private lateinit var binding: ActivityHomeBinding
    private val adapter = LoansAdapter()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityHomeBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        // Static labels + icon colors for each of the 4 stat cards (web parity).
        applyStat(binding.statTotal.tvStatLabel, binding.statTotal.statIconBg,
            binding.statTotal.ivStatIcon,
            label = getString(R.string.stat_total_applications),
            iconBgDrawable = R.drawable.bg_stat_icon_blue, glyph = "📄")
        applyStat(binding.statPending.tvStatLabel, binding.statPending.statIconBg,
            binding.statPending.ivStatIcon,
            label = getString(R.string.stat_pending),
            iconBgDrawable = R.drawable.bg_stat_icon_yellow, glyph = "⏱")
        applyStat(binding.statApproved.tvStatLabel, binding.statApproved.statIconBg,
            binding.statApproved.ivStatIcon,
            label = getString(R.string.stat_approved),
            iconBgDrawable = R.drawable.bg_stat_icon_green, glyph = "✓")
        applyStat(binding.statRating.tvStatLabel, binding.statRating.statIconBg,
            binding.statRating.ivStatIcon,
            label = getString(R.string.stat_success_rating),
            iconBgDrawable = R.drawable.bg_stat_icon_yellow, glyph = "★")

        binding.fabNewLoan.setOnClickListener {
            startActivity(Intent(this, LoanSubmitActivity::class.java))
        }
        binding.btnOpenWeb.setOnClickListener {
            lifecycleScope.launch {
                val role = MyCiApp.instance.tokenStore.role.first()
                startActivity(
                    WebAppIntents.createMainIntent(
                        this@HomeActivity,
                        WebAppIntents.pathForDashboardRole(role),
                        true
                    )
                )
            }
        }
        binding.btnSyncNow.setOnClickListener {
            LoanRepository.kickSync(this)
        }
        binding.btnCiCases.setOnClickListener {
            startActivity(Intent(this, CiCasesActivity::class.java))
        }
        binding.btnSyncStatus.setOnClickListener {
            startActivity(Intent(this, SyncStatusActivity::class.java))
        }
        binding.btnLogout.setOnClickListener {
            lifecycleScope.launch {
                MyCiApp.instance.tokenStore.clear()
                startActivity(Intent(this@HomeActivity, LoginActivity::class.java))
                finish()
            }
        }

        lifecycleScope.launch {
            LoanRepository().observeLoans().collectLatest { list ->
                adapter.submit(list)
                refreshStats(list)
            }
        }
        lifecycleScope.launch {
            MyCiApp.instance.tokenStore.userName.collectLatest { name ->
                binding.tvHello.text = getString(R.string.home_greeting_fmt, name ?: "")
            }
        }
        lifecycleScope.launch {
            MyCiApp.instance.tokenStore.role.collectLatest { role ->
                binding.fabNewLoan.visibility =
                    if (role == "ci_staff") View.GONE else View.VISIBLE
            }
        }
    }

    private fun applyStat(
        tvLabel: android.widget.TextView,
        iconBgView: android.view.View,
        glyphView: android.widget.TextView,
        label: String,
        iconBgDrawable: Int = R.drawable.bg_stat_icon_blue,
        glyph: String = "•"
    ) {
        tvLabel.text = label
        glyphView.text = glyph
        iconBgView.background = ContextCompat.getDrawable(this, iconBgDrawable)
    }

    private fun refreshStats(list: List<LoanApplicationEntity>) {
        val total = list.size
        val pending = list.count { it.status in setOf("submitted", "assigned_to_ci") }
        val approved = list.count { it.status == "approved" }
        val rating = if (total > 0) (approved.toDouble() / total * 10.0) else 0.0

        binding.statTotal.tvStatNumber.text = total.toString()
        binding.statPending.tvStatNumber.text = pending.toString()
        binding.statApproved.tvStatNumber.text = approved.toString()
        binding.statRating.tvStatNumber.text = "%.1f".format(rating)
    }

    private class LoansAdapter : RecyclerView.Adapter<LoansAdapter.VH>() {
        private val items = mutableListOf<LoanApplicationEntity>()
        private val df = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())

        fun submit(list: List<LoanApplicationEntity>) {
            items.clear(); items.addAll(list); notifyDataSetChanged()
        }

        override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
            val b = ItemLoanRowBinding.inflate(
                android.view.LayoutInflater.from(parent.context), parent, false
            )
            return VH(b)
        }

        override fun getItemCount(): Int = items.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val it = items[position]
            holder.b.tvName.text = it.memberName
            holder.b.tvAmount.text = it.loanAmount?.let { a -> "₱${"%,.2f".format(a)}" } ?: "—"
            // Status badge color matches the web's Bootstrap badge palette.
            val ctx = holder.itemView.context
            val badge = badgeFor(it.status)
            holder.b.tvStatus.text = badge.text
            holder.b.tvStatus.setBackgroundResource(badge.bg)
            holder.b.tvStatus.setTextColor(ContextCompat.getColor(ctx, badge.fg))
            holder.b.tvDate.text = df.format(Date(it.submittedAt))
        }

        class VH(val b: ItemLoanRowBinding) : RecyclerView.ViewHolder(b.root)

        private data class Badge(val text: String, val bg: Int, val fg: Int)

        private fun badgeFor(status: String): Badge = when (status) {
            "approved" -> Badge("Approved", R.drawable.bg_status_success, R.color.status_success_text)
            "rejected" -> Badge("Rejected", R.drawable.bg_status_warning, R.color.status_danger_text)
            "ci_completed" -> Badge("CI Completed", R.drawable.bg_status_info, R.color.status_info_text)
            "assigned_to_ci" -> Badge("Assigned to CI", R.drawable.bg_status_warning, R.color.status_warning_text)
            "submitted" -> Badge("Submitted", R.drawable.bg_status_info, R.color.status_info_text)
            else -> Badge(status, R.drawable.bg_status_warning, R.color.status_warning_text)
        }
    }
}
