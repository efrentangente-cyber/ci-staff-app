package com.example.myci.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.myci.data.LoanRepository
import com.example.myci.databinding.ActivitySyncStatusBinding
import com.example.myci.databinding.ItemSyncRowBinding
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/**
 * Operator visibility into the offline queue + any flagged conflicts. Read-only for now;
 * "Retry" just kicks the worker which will pick up everything in pending_ops.
 */
class SyncStatusActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySyncStatusBinding
    private val adapter = SyncRowsAdapter()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySyncStatusBinding.inflate(layoutInflater)
        setContentView(binding.root)
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = adapter
        binding.btnRetry.setOnClickListener {
            LoanRepository.kickSync(this)
            refresh()
        }

        lifecycleScope.launch {
            LoanRepository().observeConflicts().collectLatest { conflicts ->
                refresh(conflicts.map {
                    Row("Conflict",
                        "${it.memberName} (#${it.serverId ?: it.localId})",
                        "Local edit + server change. Server wins; local marked CONFLICT."
                    )
                })
            }
        }
        refresh()
    }

    private fun refresh(extra: List<Row> = emptyList()) {
        lifecycleScope.launch {
            val ops = LoanRepository().pendingOps()
            val pendingRows = ops.map {
                Row(it.type, it.targetTable + "#" + it.targetLocalId,
                    "attempts=${it.attempts}" + (it.lastError?.let { e -> " · last: $e" } ?: ""))
            }
            val all = extra + pendingRows
            adapter.submit(all)
            binding.tvSummary.text = "Pending: ${ops.size}, Conflicts: ${extra.size}"
        }
    }

    data class Row(val title: String, val subtitle: String, val detail: String)

    private class SyncRowsAdapter : RecyclerView.Adapter<SyncRowsAdapter.VH>() {
        private val items = mutableListOf<Row>()
        fun submit(list: List<Row>) { items.clear(); items.addAll(list); notifyDataSetChanged() }

        override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int): VH {
            val b = ItemSyncRowBinding.inflate(
                android.view.LayoutInflater.from(parent.context), parent, false
            )
            return VH(b)
        }

        override fun getItemCount(): Int = items.size
        override fun onBindViewHolder(holder: VH, position: Int) {
            val r = items[position]
            holder.b.tvTitle.text = r.title
            holder.b.tvSubtitle.text = r.subtitle
            holder.b.tvDetail.text = r.detail
        }
        class VH(val b: ItemSyncRowBinding) : RecyclerView.ViewHolder(b.root)
    }
}
