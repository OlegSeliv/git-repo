package ru.servicecontracts.mobile

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import ru.servicecontracts.mobile.databinding.ActivityMainBinding
import ru.servicecontracts.mobile.ui.contracts.ContractsFragment
import ru.servicecontracts.mobile.ui.dashboard.DashboardFragment
import ru.servicecontracts.mobile.ui.documents.DocumentsFragment
import ru.servicecontracts.mobile.ui.orders.OrdersFragment
import ru.servicecontracts.mobile.ui.trips.TripsFragment

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var bottomNavigation: BottomNavigationView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupBottomNavigation()
        
        if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.fragment_container, DashboardFragment())
                .commit()
        }
    }

    private fun setupBottomNavigation() {
        bottomNavigation = binding.bottomNavigation
        
        bottomNavigation.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_dashboard -> {
                    replaceFragment(DashboardFragment())
                    true
                }
                R.id.nav_contracts -> {
                    replaceFragment(ContractsFragment())
                    true
                }
                R.id.nav_orders -> {
                    replaceFragment(OrdersFragment())
                    true
                }
                R.id.nav_trips -> {
                    replaceFragment(TripsFragment())
                    true
                }
                R.id.nav_documents -> {
                    replaceFragment(DocumentsFragment())
                    true
                }
                else -> false
            }
        }
    }

    private fun replaceFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .commit()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_sync -> {
                syncData()
                true
            }
            R.id.action_settings -> {
                // Открыть настройки
                true
            }
            R.id.action_logout -> {
                logout()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun syncData() {
        // Синхронизация данных с сервером
        // Реализация будет добавлена позже
    }

    private fun logout() {
        // Очистка данных пользователя и возврат к экрану входа
        // Реализация будет добавлена позже
    }
}