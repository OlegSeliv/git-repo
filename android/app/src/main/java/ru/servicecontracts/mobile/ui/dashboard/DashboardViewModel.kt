package ru.servicecontracts.mobile.ui.dashboard

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import ru.servicecontracts.mobile.data.model.Contract
import ru.servicecontracts.mobile.data.model.Order
import ru.servicecontracts.mobile.data.repository.DashboardRepository

class DashboardViewModel(
    private val repository: DashboardRepository
) : ViewModel() {

    private val _dashboardData = MutableLiveData<DashboardData>()
    val dashboardData: LiveData<DashboardData> = _dashboardData

    private val _quickActions = MutableLiveData<List<QuickAction>>()
    val quickActions: LiveData<List<QuickAction>> = _quickActions

    private val _recentOrders = MutableLiveData<List<Order>>()
    val recentOrders: LiveData<List<Order>> = _recentOrders

    private val _isLoading = MutableLiveData<Boolean>()
    val isLoading: LiveData<Boolean> = _isLoading

    init {
        loadQuickActions()
    }

    fun loadDashboardData() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val contracts = repository.getContracts()
                val orders = repository.getOrders()
                val materialsDeficit = repository.getMaterialsDeficit()
                val activeTrips = repository.getActiveTrips()

                val data = DashboardData(
                    totalContracts = contracts.size,
                    activeContracts = contracts.count { it.status == "active" },
                    totalContractsValue = contracts.sumOf { it.totalAmount ?: 0.0 },
                    totalAdvances = contracts.sumOf { it.advanceAmount ?: 0.0 },
                    activeOrders = orders.count { it.status == "in_progress" },
                    materialsDeficit = materialsDeficit.size,
                    activeTrips = activeTrips.size
                )

                _dashboardData.value = data
                _recentOrders.value = orders.take(5)
            } catch (e: Exception) {
                // Обработка ошибок
            } finally {
                _isLoading.value = false
            }
        }
    }

    private fun loadQuickActions() {
        val actions = listOf(
            QuickAction(
                type = QuickActionType.ADD_CONTRACT,
                title = "Добавить контракт",
                icon = R.drawable.ic_add_contract,
                color = R.color.colorPrimary
            ),
            QuickAction(
                type = QuickActionType.ADD_ORDER,
                title = "Новый заказ",
                icon = R.drawable.ic_add_order,
                color = R.color.colorAccent
            ),
            QuickAction(
                type = QuickActionType.SCAN_DOCUMENT,
                title = "Сканировать",
                icon = R.drawable.ic_scan,
                color = R.color.colorSecondary
            ),
            QuickAction(
                type = QuickActionType.VIEW_MATERIALS,
                title = "Материалы",
                icon = R.drawable.ic_materials,
                color = R.color.colorTertiary
            )
        )
        _quickActions.value = actions
    }
}

data class DashboardData(
    val totalContracts: Int,
    val activeContracts: Int,
    val totalContractsValue: Double,
    val totalAdvances: Double,
    val activeOrders: Int,
    val materialsDeficit: Int,
    val activeTrips: Int
)

data class QuickAction(
    val type: QuickActionType,
    val title: String,
    val icon: Int,
    val color: Int
)

enum class QuickActionType {
    ADD_CONTRACT,
    ADD_ORDER,
    SCAN_DOCUMENT,
    VIEW_MATERIALS
}