"""
Модуль для работы с базой данных SQLite
Хранит всю информацию о контрактах, заказах, материалах, командировках и документах
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


class ServiceContractDB:
    def __init__(self, db_path: str = "service_contracts.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Получить подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализация структуры базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица сервисных контрактов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_number TEXT NOT NULL UNIQUE,
                customer TEXT NOT NULL,
                total_amount REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица субсчетов контрактов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contract_subaccounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                subaccount_name TEXT NOT NULL,
                total_budget REAL NOT NULL,
                current_balance REAL NOT NULL,
                reserved_amount REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id)
            )
        """)
        
        # Таблица заказов на выполнение работ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                order_number TEXT NOT NULL UNIQUE,
                device_name TEXT NOT NULL,
                device_location TEXT,
                arrived_to_factory BOOLEAN DEFAULT 0,
                defect_report_received BOOLEAN DEFAULT 0,
                defect_report_date TEXT,
                repair_deadline TEXT,
                status TEXT DEFAULT 'new',
                priority INTEGER DEFAULT 0,
                estimated_cost REAL,
                actual_cost REAL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id)
            )
        """)
        
        # Таблица комплектующих/материалов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_code TEXT NOT NULL UNIQUE,
                component_name TEXT NOT NULL,
                description TEXT,
                unit_of_measure TEXT DEFAULT 'шт',
                unit_price REAL,
                warehouse_stock INTEGER DEFAULT 0,
                min_stock_level INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица требований комплектующих для заказов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                required_quantity INTEGER NOT NULL,
                allocated_from_warehouse INTEGER DEFAULT 0,
                ordered_from_supplier INTEGER DEFAULT 0,
                received_from_supplier INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
                FOREIGN KEY (component_id) REFERENCES components(id)
            )
        """)
        
        # Таблица поставщиков
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT NOT NULL,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица заказов поставщикам
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                order_number TEXT NOT NULL UNIQUE,
                order_date TEXT NOT NULL,
                expected_delivery_date TEXT,
                actual_delivery_date TEXT,
                total_amount REAL,
                status TEXT DEFAULT 'ordered',
                payment_status TEXT DEFAULT 'not_paid',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        """)
        
        # Таблица позиций заказов поставщикам
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_order_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                work_order_id INTEGER,
                FOREIGN KEY (supplier_order_id) REFERENCES supplier_orders(id),
                FOREIGN KEY (component_id) REFERENCES components(id),
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
            )
        """)
        
        # Таблица сотрудников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                position TEXT,
                department TEXT,
                phone TEXT,
                email TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица командировок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                work_order_id INTEGER,
                contract_id INTEGER NOT NULL,
                destination TEXT NOT NULL,
                start_date TEXT NOT NULL,
                planned_end_date TEXT NOT NULL,
                actual_end_date TEXT,
                extension_count INTEGER DEFAULT 0,
                last_extension_date TEXT,
                hr_approval_status TEXT DEFAULT 'pending',
                budget_allocated REAL,
                status TEXT DEFAULT 'planned',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id),
                FOREIGN KEY (contract_id) REFERENCES contracts(id)
            )
        """)
        
        # Таблица платежей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                work_order_id INTEGER,
                payment_type TEXT NOT NULL,
                payment_stage TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_date TEXT,
                expected_date TEXT,
                status TEXT DEFAULT 'pending',
                invoice_number TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
            )
        """)
        
        # Таблица документов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL,
                document_number TEXT,
                contract_id INTEGER,
                work_order_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                file_path TEXT,
                scan_path TEXT,
                paper_storage_location TEXT,
                status TEXT DEFAULT 'draft',
                created_date TEXT NOT NULL,
                signed_date TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
            )
        """)
        
        # Таблица протоколов совещаний
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meeting_protocols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER,
                meeting_date TEXT NOT NULL,
                meeting_type TEXT,
                participants TEXT,
                agenda TEXT,
                decisions TEXT,
                action_items TEXT,
                file_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id)
            )
        """)
        
        # Таблица задач из протоколов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS protocol_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                protocol_id INTEGER NOT NULL,
                task_description TEXT NOT NULL,
                responsible_party TEXT NOT NULL,
                deadline TEXT,
                status TEXT DEFAULT 'pending',
                completion_date TEXT,
                notes TEXT,
                FOREIGN KEY (protocol_id) REFERENCES meeting_protocols(id)
            )
        """)
        
        # Таблица переписки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS correspondence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER,
                work_order_id INTEGER,
                correspondence_type TEXT NOT NULL,
                counterparty TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT,
                sent_date TEXT,
                received_date TEXT,
                direction TEXT NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'sent',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contract_id) REFERENCES contracts(id),
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
            )
        """)
        
        # Таблица актов дефектации
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS defect_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                report_number TEXT NOT NULL,
                report_date TEXT NOT NULL,
                defects_found TEXT NOT NULL,
                required_work TEXT,
                file_path TEXT,
                status TEXT DEFAULT 'received',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
            )
        """)
        
        # Индексы для оптимизации
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_orders_contract ON work_orders(contract_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_orders_status ON work_orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_contract ON payments(contract_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_contract ON documents(contract_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_business_trips_employee ON business_trips(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_business_trips_status ON business_trips(status)")
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Выполнить SELECT запрос"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Выполнить INSERT запрос и вернуть ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Выполнить UPDATE/DELETE запрос"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        return rows_affected


# Создание экземпляра БД при импорте
db = ServiceContractDB()
