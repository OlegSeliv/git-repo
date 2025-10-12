"""
Схема базы данных для системы управления сервисными контрактами
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

class DatabaseManager:
    def __init__(self, db_path: str = "service_contracts.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация всех таблиц базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица контрактов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            total_amount REAL NOT NULL,
            advance_amount REAL DEFAULT 0,
            advance_received REAL DEFAULT 0,
            final_amount REAL DEFAULT 0,
            final_received REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица заказов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            contract_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            device_serial TEXT,
            planned_start DATE,
            planned_end DATE,
            actual_start DATE,
            actual_end DATE,
            status TEXT DEFAULT 'new',
            priority TEXT DEFAULT 'normal',
            estimated_cost REAL DEFAULT 0,
            actual_cost REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        )''')
        
        # Таблица материалов и комплектующих
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            unit TEXT DEFAULT 'шт',
            quantity_warehouse REAL DEFAULT 0,
            quantity_reserved REAL DEFAULT 0,
            quantity_minimum REAL DEFAULT 0,
            price REAL DEFAULT 0,
            supplier TEXT,
            lead_time_days INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица требований материалов для заказов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            quantity_required REAL NOT NULL,
            quantity_allocated REAL DEFAULT 0,
            quantity_ordered REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (material_id) REFERENCES materials(id)
        )''')
        
        # Таблица командировок
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS business_trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            order_id INTEGER,
            location TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            extended_to DATE,
            status TEXT DEFAULT 'planned',
            travel_order_number TEXT,
            accommodation TEXT,
            transport_type TEXT,
            estimated_expenses REAL DEFAULT 0,
            actual_expenses REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )''')
        
        # Таблица финансовых операций
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            order_id INTEGER,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date DATE NOT NULL,
            document_number TEXT,
            subaccount_balance REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )''')
        
        # Таблица документов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL,
            document_number TEXT,
            contract_id INTEGER,
            order_id INTEGER,
            title TEXT NOT NULL,
            file_path TEXT,
            scan_path TEXT,
            physical_location TEXT,
            creation_date DATE,
            signing_date DATE,
            status TEXT DEFAULT 'draft',
            metadata JSON,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )''')
        
        # Таблица актов дефектации
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS defect_acts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            act_number TEXT UNIQUE NOT NULL,
            act_date DATE NOT NULL,
            device_info TEXT NOT NULL,
            defects_found TEXT NOT NULL,
            materials_required JSON,
            estimated_repair_time INTEGER,
            file_path TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )''')
        
        # Таблица протоколов совещаний
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meeting_protocols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_date DATE NOT NULL,
            meeting_type TEXT NOT NULL,
            participants TEXT NOT NULL,
            agenda TEXT NOT NULL,
            decisions TEXT NOT NULL,
            tasks JSON,
            file_path TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Таблица задач из протоколов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_id INTEGER,
            contract_id INTEGER,
            order_id INTEGER,
            task_description TEXT NOT NULL,
            responsible TEXT NOT NULL,
            deadline DATE,
            status TEXT DEFAULT 'new',
            completion_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (protocol_id) REFERENCES meeting_protocols(id),
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )''')
        
        # Таблица уведомлений и напоминаний
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_type TEXT NOT NULL,
            related_table TEXT,
            related_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'normal',
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Создание индексов для оптимизации запросов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_contract ON orders(contract_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_materials_order ON order_materials(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_business_trips_order ON business_trips(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_contract ON documents(contract_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_order ON documents(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_contract ON financial_transactions(contract_id)')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Выполнение SELECT запроса"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Выполнение INSERT/UPDATE/DELETE запроса"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def check_material_availability(self, order_id: int) -> Dict[str, Any]:
        """Проверка наличия материалов для заказа"""
        query = '''
        SELECT 
            m.name,
            m.article,
            om.quantity_required,
            m.quantity_warehouse,
            m.quantity_reserved,
            (m.quantity_warehouse - m.quantity_reserved) as available,
            CASE 
                WHEN (m.quantity_warehouse - m.quantity_reserved) >= om.quantity_required 
                THEN 'available'
                ELSE 'deficit'
            END as status
        FROM order_materials om
        JOIN materials m ON om.material_id = m.id
        WHERE om.order_id = ?
        '''
        return self.execute_query(query, (order_id,))
    
    def get_contract_financial_status(self, contract_id: int) -> Dict[str, Any]:
        """Получение финансового статуса контракта"""
        query = '''
        SELECT 
            c.contract_number,
            c.total_amount,
            c.advance_received,
            c.final_received,
            (c.advance_received + c.final_received) as total_received,
            (c.total_amount - c.advance_received - c.final_received) as balance,
            COALESCE(SUM(o.actual_cost), 0) as total_expenses
        FROM contracts c
        LEFT JOIN orders o ON c.id = o.contract_id
        WHERE c.id = ?
        GROUP BY c.id
        '''
        result = self.execute_query(query, (contract_id,))
        return result[0] if result else None
    
    def get_active_business_trips(self) -> List[Dict[str, Any]]:
        """Получение активных командировок"""
        query = '''
        SELECT 
            bt.*,
            o.order_number,
            o.description as order_description,
            c.contract_number
        FROM business_trips bt
        LEFT JOIN orders o ON bt.order_id = o.id
        LEFT JOIN contracts c ON o.contract_id = c.id
        WHERE bt.status IN ('active', 'planned')
        AND bt.end_date >= date('now')
        ORDER BY bt.start_date
        '''
        return self.execute_query(query)
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Получение невыполненных задач"""
        query = '''
        SELECT 
            t.*,
            mp.meeting_date,
            c.contract_number,
            o.order_number
        FROM tasks t
        LEFT JOIN meeting_protocols mp ON t.protocol_id = mp.id
        LEFT JOIN contracts c ON t.contract_id = c.id
        LEFT JOIN orders o ON t.order_id = o.id
        WHERE t.status != 'completed'
        ORDER BY t.deadline
        '''
        return self.execute_query(query)