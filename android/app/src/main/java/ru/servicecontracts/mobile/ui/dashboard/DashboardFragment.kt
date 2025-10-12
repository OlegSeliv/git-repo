package ru.servicecontracts.mobile.ui.dashboard

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.LinearLayoutManager
import com.github.mikephil.charting.charts.PieChart
import com.github.mikephil.charting.data.PieData
import com.github.mikephil.charting.data.PieDataSet
import com.github.mikephil.charting.data.PieEntry
import ru.servicecontracts.mobile.R
import ru.servicecontracts.mobile.databinding.FragmentDashboardBinding
import ru.servicecontracts.mobile.ui.adapters.QuickActionsAdapter
import ru.servicecontracts.mobile.ui.adapters.RecentOrdersAdapter

class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: DashboardViewModel
    private lateinit var quickActionsAdapter: QuickActionsAdapter
    private lateinit var recentOrdersAdapter: RecentOrdersAdapter

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        viewModel = ViewModelProvider(this)[DashboardViewModel::class.java]
        
        setupRecyclerViews()
        setupCharts()
        observeViewModel()
        
        // Загружаем данные
        viewModel.loadDashboardData()
    }

    private fun setupRecyclerViews() {
        // Быстрые действия
        quickActionsAdapter = QuickActionsAdapter { action ->
            handleQuickAction(action)
        }
        binding.recyclerQuickActions.apply {
            layoutManager = LinearLayoutManager(context, LinearLayoutManager.HORIZONTAL, false)
            adapter = quickActionsAdapter
        }

        // Последние заказы
        recentOrdersAdapter = RecentOrdersAdapter { order ->
            // Открыть детали заказа
        }
        binding.recyclerRecentOrders.apply {
            layoutManager = LinearLayoutManager(context)
            adapter = recentOrdersAdapter
        }
    }

    private fun setupCharts() {
        setupContractsChart()
        setupOrdersChart()
    }

    private fun setupContractsChart() {
        val chart = binding.chartContracts
        chart.description.isEnabled = false
        chart.legend.isEnabled = true
        chart.setUsePercentValues(true)
        chart.isRotationEnabled = false
        chart.isHighlightPerTapEnabled = true
    }

    private fun setupOrdersChart() {
        val chart = binding.chartOrders
        chart.description.isEnabled = false
        chart.legend.isEnabled = true
        chart.setDrawGridBackground(false)
        chart.isHighlightPerTapEnabled = true
    }

    private fun observeViewModel() {
        viewModel.dashboardData.observe(viewLifecycleOwner) { data ->
            updateDashboardCards(data)
            updateCharts(data)
        }

        viewModel.quickActions.observe(viewLifecycleOwner) { actions ->
            quickActionsAdapter.submitList(actions)
        }

        viewModel.recentOrders.observe(viewLifecycleOwner) { orders ->
            recentOrdersAdapter.submitList(orders)
        }

        viewModel.isLoading.observe(viewLifecycleOwner) { isLoading ->
            binding.progressBar.visibility = if (isLoading) View.VISIBLE else View.GONE
        }
    }

    private fun updateDashboardCards(data: DashboardData) {
        binding.textTotalContracts.text = data.totalContracts.toString()
        binding.textActiveOrders.text = data.activeOrders.toString()
        binding.textMaterialsDeficit.text = data.materialsDeficit.toString()
        binding.textActiveTrips.text = data.activeTrips.toString()
    }

    private fun updateCharts(data: DashboardData) {
        updateContractsChart(data)
        updateOrdersChart(data)
    }

    private fun updateContractsChart(data: DashboardData) {
        val entries = listOf(
            PieEntry(data.totalAdvances.toFloat(), "Авансы"),
            PieEntry((data.totalContractsValue - data.totalAdvances).toFloat(), "Остаток")
        )

        val dataSet = PieDataSet(entries, "Финансовое состояние")
        dataSet.colors = listOf(
            resources.getColor(R.color.colorPrimary, null),
            resources.getColor(R.color.colorAccent, null)
        )

        val pieData = PieData(dataSet)
        binding.chartContracts.data = pieData
        binding.chartContracts.invalidate()
    }

    private fun updateOrdersChart(data: DashboardData) {
        // Реализация графика заказов
        // Будет добавлена позже
    }

    private fun handleQuickAction(action: QuickAction) {
        when (action.type) {
            QuickActionType.ADD_CONTRACT -> {
                // Открыть форму добавления контракта
            }
            QuickActionType.ADD_ORDER -> {
                // Открыть форму добавления заказа
            }
            QuickActionType.SCAN_DOCUMENT -> {
                // Открыть сканер документов
            }
            QuickActionType.VIEW_MATERIALS -> {
                // Перейти к материалам
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}