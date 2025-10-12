"""
Модуль аналитики и отчетности
"""

from typing import Dict, List, Any
from datetime import datetime, date, timedelta
import json
from database import DatabaseManager

class AnalyticsEngine:
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Получение данных для главного дашборда"""
        dashboard = {}
        
        # Общая статистика по контрактам
        contracts_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_contracts,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_contracts,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_contracts,
                SUM(total_amount) as total_value,
                SUM(advance_received + final_received) as total_received,
                SUM(total_amount - advance_received - final_received) as total_pending
            FROM contracts
        ''')[0]
        dashboard['contracts'] = contracts_stats
        
        # Статистика по заказам
        orders_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_orders,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_orders,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN status = 'delayed' THEN 1 END) as delayed_orders
            FROM orders
        ''')[0]
        dashboard['orders'] = orders_stats
        
        # Активные командировки
        active_trips = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_active_trips,
                COUNT(DISTINCT employee_name) as employees_on_trip,
                COUNT(DISTINCT location) as unique_locations,
                SUM(estimated_expenses) as total_estimated_expenses
            FROM business_trips
            WHERE status IN ('active', 'planned')
            AND end_date >= date('now')
        ''')[0]
        dashboard['business_trips'] = active_trips
        
        # Дефицит материалов
        materials_deficit = self.db.execute_query('''
            SELECT 
                COUNT(*) as deficit_items,
                COUNT(*) as total_items
            FROM materials
            WHERE (quantity_warehouse - quantity_reserved) < quantity_minimum
        ''')[0]
        dashboard['materials'] = materials_deficit
        
        # Критические материалы (топ-5 с наибольшим дефицитом)
        critical_materials = self.db.execute_query('''
            SELECT 
                name,
                article,
                quantity_warehouse,
                quantity_reserved,
                quantity_minimum,
                (quantity_minimum - (quantity_warehouse - quantity_reserved)) as deficit_amount
            FROM materials
            WHERE (quantity_warehouse - quantity_reserved) < quantity_minimum
            ORDER BY deficit_amount DESC
            LIMIT 5
        ''')
        dashboard['critical_materials'] = critical_materials
        
        # Предстоящие задачи (на ближайшую неделю)
        upcoming_tasks = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN deadline <= date('now', '+3 days') THEN 1 END) as urgent_tasks,
                COUNT(CASE WHEN deadline < date('now') THEN 1 END) as overdue_tasks
            FROM tasks
            WHERE status != 'completed'
            AND deadline <= date('now', '+7 days')
        ''')[0]
        dashboard['upcoming_tasks'] = upcoming_tasks
        
        # Финансовая сводка за последний месяц
        monthly_finance = self.db.execute_query('''
            SELECT 
                SUM(CASE WHEN transaction_type = 'advance' THEN amount ELSE 0 END) as advance_received,
                SUM(CASE WHEN transaction_type = 'final' THEN amount ELSE 0 END) as final_received,
                SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as expenses,
                COUNT(DISTINCT contract_id) as contracts_with_transactions
            FROM financial_transactions
            WHERE payment_date >= date('now', '-30 days')
        ''')[0]
        dashboard['monthly_finance'] = monthly_finance
        
        # Заказы по локациям
        orders_by_location = self.db.execute_query('''
            SELECT 
                location,
                COUNT(*) as order_count,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as active_orders
            FROM orders
            WHERE status != 'completed'
            GROUP BY location
            ORDER BY order_count DESC
            LIMIT 10
        ''')
        dashboard['orders_by_location'] = orders_by_location
        
        # Устройства на заводе для ремонта
        devices_at_factory = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_devices,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_repair,
                COUNT(CASE WHEN status = 'waiting_parts' THEN 1 END) as waiting_parts,
                AVG(JULIANDAY('now') - JULIANDAY(actual_start)) as avg_days_in_repair
            FROM orders
            WHERE location LIKE '%завод%' OR location LIKE '%цех%'
            AND status NOT IN ('completed', 'cancelled')
        ''')[0]
        dashboard['devices_at_factory'] = devices_at_factory
        
        return dashboard
    
    def generate_contract_report(self, contract_id: int) -> Dict[str, Any]:
        """Генерация подробного отчета по контракту"""
        report = {}
        
        # Основная информация о контракте
        contract_info = self.db.execute_query(
            "SELECT * FROM contracts WHERE id = ?", (contract_id,)
        )[0]
        report['contract'] = contract_info
        
        # Финансовый статус
        report['financial_status'] = self.db.get_contract_financial_status(contract_id)
        
        # Все заказы по контракту
        orders = self.db.execute_query('''
            SELECT 
                *,
                JULIANDAY(planned_end) - JULIANDAY('now') as days_to_deadline,
                CASE 
                    WHEN status != 'completed' AND planned_end < date('now') THEN 'overdue'
                    WHEN status != 'completed' AND planned_end <= date('now', '+7 days') THEN 'urgent'
                    ELSE 'normal'
                END as urgency
            FROM orders
            WHERE contract_id = ?
            ORDER BY created_at DESC
        ''', (contract_id,))
        report['orders'] = orders
        
        # Статистика по заказам
        orders_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN status = 'new' THEN 1 END) as new,
                SUM(estimated_cost) as total_estimated_cost,
                SUM(actual_cost) as total_actual_cost,
                AVG(JULIANDAY(actual_end) - JULIANDAY(actual_start)) as avg_completion_days
            FROM orders
            WHERE contract_id = ?
        ''', (contract_id,))[0]
        report['orders_statistics'] = orders_stats
        
        # История платежей
        payments = self.db.execute_query('''
            SELECT 
                transaction_type,
                amount,
                payment_date,
                document_number,
                notes
            FROM financial_transactions
            WHERE contract_id = ?
            ORDER BY payment_date DESC
        ''', (contract_id,))
        report['payments'] = payments
        
        # Командировки по контракту
        business_trips = self.db.execute_query('''
            SELECT 
                bt.*,
                o.order_number,
                o.description
            FROM business_trips bt
            JOIN orders o ON bt.order_id = o.id
            WHERE o.contract_id = ?
            ORDER BY bt.start_date DESC
        ''', (contract_id,))
        report['business_trips'] = business_trips
        
        # Материалы, используемые в заказах контракта
        materials = self.db.execute_query('''
            SELECT 
                m.name,
                m.article,
                SUM(om.quantity_required) as total_required,
                SUM(om.quantity_allocated) as total_allocated,
                m.quantity_warehouse as current_stock,
                m.price,
                SUM(om.quantity_required * m.price) as total_cost
            FROM order_materials om
            JOIN materials m ON om.material_id = m.id
            JOIN orders o ON om.order_id = o.id
            WHERE o.contract_id = ?
            GROUP BY m.id
            ORDER BY total_cost DESC
        ''', (contract_id,))
        report['materials'] = materials
        
        # Документы по контракту
        documents = self.db.execute_query('''
            SELECT 
                document_type,
                title,
                creation_date,
                signing_date,
                status,
                file_path,
                scan_path
            FROM documents
            WHERE contract_id = ?
            ORDER BY created_at DESC
        ''', (contract_id,))
        report['documents'] = documents
        
        # Невыполненные задачи по контракту
        pending_tasks = self.db.execute_query('''
            SELECT 
                task_description,
                responsible,
                deadline,
                status,
                JULIANDAY(deadline) - JULIANDAY('now') as days_remaining
            FROM tasks
            WHERE contract_id = ?
            AND status != 'completed'
            ORDER BY deadline
        ''', (contract_id,))
        report['pending_tasks'] = pending_tasks
        
        # Расчет процента выполнения контракта
        if orders_stats['total_orders'] > 0:
            completion_percentage = (orders_stats['completed'] / orders_stats['total_orders']) * 100
        else:
            completion_percentage = 0
        report['completion_percentage'] = round(completion_percentage, 2)
        
        # Прогноз завершения
        if orders_stats['avg_completion_days'] and orders_stats['in_progress']:
            estimated_days_remaining = orders_stats['avg_completion_days'] * (
                orders_stats['in_progress'] + orders_stats['new']
            )
            estimated_completion_date = (
                datetime.now() + timedelta(days=estimated_days_remaining)
            ).date()
            report['estimated_completion_date'] = str(estimated_completion_date)
        else:
            report['estimated_completion_date'] = None
        
        return report
    
    def get_materials_analytics(self) -> Dict[str, Any]:
        """Аналитика по материалам и складу"""
        analytics = {}
        
        # Общая статистика склада
        warehouse_stats = self.db.execute_query('''
            SELECT 
                COUNT(*) as total_items,
                SUM(quantity_warehouse * price) as total_value,
                COUNT(CASE WHEN quantity_warehouse <= quantity_minimum THEN 1 END) as low_stock_items,
                COUNT(CASE WHEN quantity_warehouse = 0 THEN 1 END) as out_of_stock_items
            FROM materials
        ''')[0]
        analytics['warehouse_stats'] = warehouse_stats
        
        # Топ-10 самых используемых материалов
        most_used = self.db.execute_query('''
            SELECT 
                m.name,
                m.article,
                COUNT(DISTINCT om.order_id) as orders_count,
                SUM(om.quantity_required) as total_used,
                m.quantity_warehouse as current_stock,
                m.price,
                SUM(om.quantity_required * m.price) as total_value
            FROM materials m
            JOIN order_materials om ON m.id = om.material_id
            GROUP BY m.id
            ORDER BY orders_count DESC
            LIMIT 10
        ''')
        analytics['most_used_materials'] = most_used
        
        # Материалы с критическим уровнем запасов
        critical_stock = self.db.execute_query('''
            SELECT 
                name,
                article,
                quantity_warehouse,
                quantity_minimum,
                quantity_reserved,
                (quantity_warehouse - quantity_reserved) as available,
                supplier,
                lead_time_days,
                price * quantity_minimum as reorder_value
            FROM materials
            WHERE (quantity_warehouse - quantity_reserved) <= quantity_minimum
            ORDER BY (quantity_warehouse - quantity_reserved) / NULLIF(quantity_minimum, 0)
            LIMIT 20
        ''')
        analytics['critical_stock'] = critical_stock
        
        # Прогноз потребности в материалах на основе активных заказов
        future_needs = self.db.execute_query('''
            SELECT 
                m.name,
                m.article,
                SUM(om.quantity_required - om.quantity_allocated) as pending_requirement,
                m.quantity_warehouse - m.quantity_reserved as available,
                CASE 
                    WHEN (m.quantity_warehouse - m.quantity_reserved) >= 
                         SUM(om.quantity_required - om.quantity_allocated) 
                    THEN 'sufficient'
                    ELSE 'deficit'
                END as status,
                MAX(SUM(om.quantity_required - om.quantity_allocated) - 
                    (m.quantity_warehouse - m.quantity_reserved), 0) as deficit_amount
            FROM order_materials om
            JOIN materials m ON om.material_id = m.id
            JOIN orders o ON om.order_id = o.id
            WHERE o.status NOT IN ('completed', 'cancelled')
            AND om.status != 'allocated'
            GROUP BY m.id
            HAVING pending_requirement > 0
            ORDER BY deficit_amount DESC
        ''')
        analytics['future_needs'] = future_needs
        
        return analytics
    
    def get_employee_workload(self) -> List[Dict[str, Any]]:
        """Анализ загрузки сотрудников"""
        workload = self.db.execute_query('''
            SELECT 
                employee_name,
                COUNT(*) as total_trips,
                SUM(JULIANDAY(end_date) - JULIANDAY(start_date) + 1) as total_days,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_trips,
                COUNT(CASE WHEN extended_to IS NOT NULL THEN 1 END) as extended_trips,
                SUM(estimated_expenses) as total_estimated_expenses,
                SUM(actual_expenses) as total_actual_expenses,
                GROUP_CONCAT(DISTINCT location) as locations
            FROM business_trips
            WHERE start_date >= date('now', '-90 days')
            GROUP BY employee_name
            ORDER BY total_days DESC
        ''')
        
        return workload