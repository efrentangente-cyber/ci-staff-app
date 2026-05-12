package com.example.myci.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myci.MyCiApp
import com.example.myci.R
import com.example.myci.data.LoanRepository
import com.example.myci.data.local.LoanApplicationEntity
import com.example.myci.databinding.ActivityCiCasesBinding
import com.example.myci.databinding.ItemLoanRowBinding
import com.example.myci.web.WebAppIntents
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Lists CI cases assigned to the logged-in CI staff. Tap a row to open the interview form.
 * Mirrors the website's `ci_dashboard.html` layout (top bar + 4 stat cards + table card).
 */
class CiCasesActivity : AppCompatActivity() {

    private lateinit var binding: ActivityCiCasesBinding
    private val adapter = CiCasesAdapter { loan ->
        startActivity(
            Intent(this, CiInterviewActivity::class.java)
                .putExtra(CiInterviewActivity.EXTRA_LOAN_LOCAL_ID, loan.localId)
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCiCasesBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter

        applyStat(binding.statCiTotal.tvStatLabel, binding.statCiTotal.statIconBg,
            binding.statCiTotal.ivStatIcon,
            label = getString(R.string.stat_total_assigned),
            iconBgDrawable = R.drawable.bg_stat_icon_blue, glyph = "📋")
        applyStat(binding.statCiPending.tvStatLabel, binding.statCiPending.statIconBg,
            binding.statCiPending.ivStatIcon,
            label = getString(R.string.stat_pending_interview),
            iconBgDrawable = R.drawable.bg_stat_icon_yellow, glyph = "⏱")
        applyStat(binding.statCiCompleted.tvStatLabel, binding.statCiCompleted.statIconBg,
            binding.statCiCompleted.ivStatIcon,
            label = getString(R.string.stat_completed),
            iconBgDrawable = R.drawable.bg_stat_icon_green, glyph = "✓")
        applyStat(binding.statCiRate.tvStatLabel, binding.statCiRate.statIconBg,
            binding.statCiRate.ivStatIcon,
            label = getString(R.string.stat_completion_rate),
            iconBgDrawable = R.drawable.bg_stat_icon_yellow, glyph = "%")

        binding.btnSyncNow.setOnClickListener { LoanRepository.kickSync(this) }

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

        // Observe assigned cases (server already filters /api/ci/assigned by user).
        lifecycleScope.launch {
            LoanRepository().observeCiAssignedAnyone().collectLatest { list ->
                adapter.submit(list)
                refreshStats(list)
            }
        }
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

    private class CiCasesAdapter(
        val onClick: (LoanApplicationEntity) -> Unit
    ) : RecyclerView.Adapter<CiCasesAdapter.VH>() {
        private val items = mutableListOf<LoanApplicationEntity>()
        private val df = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())

        fun submit(list: List<LoanApplicationEntity>) {
            items.clear(); items.addAll(list); notifyDataSetChanged()
        }

        override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
            val b = ItemLoanRowBinding.inflate(
                android.view.LayoutInflater.from(parent.context), parent, false
            )
            return VH(b, onClick)
        }

        override fun onBindViewHolder(holder: VH, position: Int) {
            val it = items[position]
            holder.b.tvName.text = it.memberName
            holder.b.tvAmount.text = it.loanAmount?.let { a -> "₱${"%,.2f".format(a)}" } ?: "—"
            val ctx = holder.itemView.context
            val (text, bg, fg) = when (it.status) {
                "ci_completed" -> Triple("CI Completed", R.drawable.bg_status_success, R.color.status_success_text)
                "assigned_to_ci" -> Triple("Pending interview", R.drawable.bg_status_warning, R.color.status_warning_text)
                else -> Triple(it.status, R.drawable.bg_status_info, R.color.status_info_text)
            }
            holder.b.tvStatus.text = text
            holder.b.tvStatus.setBackgroundResource(bg)
            holder.b.tvStatus.setTextColor(ContextCompat.getColor(ctx, fg))
            holder.b.tvDate.text = df.format(Date(it.submittedAt))
            holder.bind(it)
        }

        override fun getItemCount(): Int = items.size

        class VH(val b: ItemLoanRowBinding, private val onClick: (LoanApplicationEntity) -> Unit)
            : RecyclerView.ViewHolder(b.root) {
            private var current: LoanApplicationEntity? = null
            init { b.root.setOnClickListener { current?.let(onClick) } }
            fun bind(it: LoanApplicationEntity) { current = it }
        }
    }
}
