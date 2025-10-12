"""
Скрипт для добавления примерных данных в систему
Используется для демонстрации и тестирования
"""

from database import db
from datetime import datetime, timedelta

def add_sample_data():
    """Добавить примерные данные"""
    
    print("Добавление примерных данных...")
    
    # 1. Добавить контракты
    print("\n1. Создание контрактов...")
    contracts = [
        {
            'contract_number': 'СК-2023-001',
            'customer': 'ООО "Оборонпром"',
            'total_amount': 5000000.0,
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'description': 'Сервисное обслуживание военной техники',
            'status': 'active'
        },
        {
            'contract_number': 'СК-2023-002',
            'customer': 'АО "Спецтехника"',
            'total_amount': 3000000.0,
            'start_date': '2023-03-01',
            'end_date': '2024-02-29',
            'description': 'Ремонт и модернизация оборудования',
            'status': 'active'
        }
    ]
    
    contract_ids = []
    for contract in contracts:
        contract_id = db.execute_insert("""
            INSERT INTO contracts (contract_number, customer, total_amount, start_date, end_date, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tuple(contract.values()))
        contract_ids.append(contract_id)
        print(f"   ✓ Контракт {contract['contract_number']} создан (ID: {contract_id})")
    
    # 2. Добавить субсчета
    print("\n2. Создание субсчетов...")
    for contract_id in contract_ids:
        db.execute_insert("""
            INSERT INTO contract_subaccounts (contract_id, subaccount_name, total_budget, current_balance)
            VALUES (?, ?, ?, ?)
        """, (contract_id, 'Основной субсчет', 1000000.0, 500000.0))
        print(f"   ✓ Субсчет для контракта ID {contract_id} создан")
    
    # 3. Добавить сотрудников
    print("\n3. Создание сотрудников...")
    employees = [
        ('Иванов Иван Иванович', 'Инженер', 'Сервисный отдел'),
        ('Петров Петр Петрович', 'Старший специалист', 'Сервисный отдел'),
        ('Сидорова Анна Сергеевна', 'Техник', 'Сервисный отдел')
    ]
    
    employee_ids = []
    for emp in employees:
        emp_id = db.execute_insert("""
            INSERT INTO employees (full_name, position, department)
            VALUES (?, ?, ?)
        """, emp)
        employee_ids.append(emp_id)
        print(f"   ✓ Сотрудник {emp[0]} добавлен (ID: {emp_id})")
    
    # 4. Добавить заказы
    print("\n4. Создание заказов...")
    orders = [
        {
            'contract_id': contract_ids[0],
            'order_number': 'ЗАК-001',
            'device_name': 'Радиостанция Р-168-25У',
            'device_location': 'Москва, военная часть 12345',
            'arrived_to_factory': False,
            'repair_deadline': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'estimated_cost': 150000.0,
            'priority': 2,
            'status': 'new'
        },
        {
            'contract_id': contract_ids[0],
            'order_number': 'ЗАК-002',
            'device_name': 'Навигационная система',
            'device_location': None,
            'arrived_to_factory': True,
            'repair_deadline': (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
            'estimated_cost': 200000.0,
            'priority': 3,
            'status': 'in_progress'
        },
        {
            'contract_id': contract_ids[1],
            'order_number': 'ЗАК-003',
            'device_name': 'Блок управления БУ-3М',
            'device_location': 'Санкт-Петербург',
            'arrived_to_factory': False,
            'repair_deadline': (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d'),
            'estimated_cost': 180000.0,
            'priority': 1,
            'status': 'new'
        }
    ]
    
    order_ids = []
    for order in orders:
        order_id = db.execute_insert("""
            INSERT INTO work_orders 
            (contract_id, order_number, device_name, device_location, arrived_to_factory, 
             repair_deadline, estimated_cost, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order['contract_id'], order['order_number'], order['device_name'],
            order['device_location'], order['arrived_to_factory'], order['repair_deadline'],
            order['estimated_cost'], order['priority'], order['status']
        ))
        order_ids.append(order_id)
        print(f"   ✓ Заказ {order['order_number']} создан (ID: {order_id})")
    
    # 5. Добавить комплектующие
    print("\n5. Создание комплектующих...")
    components = [
        ('РЛ-001', 'Резистор R-125', 'шт', 50.0, 100, 10),
        ('КП-002', 'Конденсатор К-50', 'шт', 80.0, 50, 20),
        ('МС-003', 'Микросхема МС-1234', 'шт', 1200.0, 5, 10),
        ('ПР-004', 'Провод МГТФ 0.5', 'м', 15.0, 500, 100),
        ('КР-005', 'Корпус защитный КЗ-10', 'шт', 350.0, 3, 5)
    ]
    
    component_ids = []
    for comp in components:
        comp_id = db.execute_insert("""
            INSERT INTO components 
            (component_code, component_name, unit_of_measure, unit_price, warehouse_stock, min_stock_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, comp)
        component_ids.append(comp_id)
        print(f"   ✓ Компонент {comp[0]} добавлен (ID: {comp_id})")
    
    # 6. Добавить требования материалов для заказов
    print("\n6. Создание требований материалов...")
    order_components = [
        # Для заказа 1
        (order_ids[0], component_ids[0], 50, 30, 0, 0),  # Резисторы - дефицит 20
        (order_ids[0], component_ids[1], 30, 30, 0, 0),  # Конденсаторы - хватает
        (order_ids[0], component_ids[2], 10, 5, 0, 0),   # Микросхемы - дефицит 5
        # Для заказа 2
        (order_ids[1], component_ids[2], 8, 0, 0, 0),    # Микросхемы - дефицит 8
        (order_ids[1], component_ids[3], 200, 200, 0, 0), # Провод - хватает
        (order_ids[1], component_ids[4], 5, 3, 0, 0),    # Корпуса - дефицит 2
    ]
    
    for oc in order_components:
        db.execute_insert("""
            INSERT INTO order_components 
            (work_order_id, component_id, required_quantity, allocated_from_warehouse, 
             ordered_from_supplier, received_from_supplier)
            VALUES (?, ?, ?, ?, ?, ?)
        """, oc)
    print(f"   ✓ Добавлено {len(order_components)} требований материалов")
    
    # 7. Добавить командировки
    print("\n7. Создание командировок...")
    trips = [
        {
            'employee_id': employee_ids[0],
            'work_order_id': order_ids[0],
            'contract_id': contract_ids[0],
            'destination': 'Москва',
            'start_date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'planned_end_date': (datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d'),
            'status': 'planned'
        },
        {
            'employee_id': employee_ids[1],
            'work_order_id': order_ids[2],
            'contract_id': contract_ids[1],
            'destination': 'Санкт-Петербург',
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'planned_end_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'status': 'active'
        }
    ]
    
    for trip in trips:
        db.execute_insert("""
            INSERT INTO business_trips 
            (employee_id, work_order_id, contract_id, destination, start_date, planned_end_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tuple(trip.values()))
        print(f"   ✓ Командировка в {trip['destination']} создана")
    
    # 8. Добавить платежи
    print("\n8. Создание платежей...")
    payments = [
        (contract_ids[0], None, 'incoming', 'advance', 1500000.0, '2023-01-15', 'completed'),
        (contract_ids[0], None, 'incoming', 'advance', 1000000.0, '2023-03-20', 'completed'),
        (contract_ids[0], None, 'incoming', 'final', 500000.0, None, 'pending'),
        (contract_ids[1], None, 'incoming', 'advance', 900000.0, '2023-03-10', 'completed'),
    ]
    
    for payment in payments:
        db.execute_insert("""
            INSERT INTO payments 
            (contract_id, work_order_id, payment_type, payment_stage, amount, payment_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, payment)
    print(f"   ✓ Добавлено {len(payments)} платежей")
    
    # 9. Добавить поставщиков
    print("\n9. Создание поставщиков...")
    suppliers = [
        ('ООО "ЭлектроКомплект"', 'Иванов И.И.', '+7-495-123-45-67', 'elektro@example.com'),
        ('АО "РадиоДеталь"', 'Петрова А.С.', '+7-812-987-65-43', 'radio@example.com')
    ]
    
    for supplier in suppliers:
        db.execute_insert("""
            INSERT INTO suppliers (supplier_name, contact_person, phone, email)
            VALUES (?, ?, ?, ?)
        """, supplier)
        print(f"   ✓ Поставщик {supplier[0]} добавлен")
    
    print("\n✅ Примерные данные успешно добавлены!")
    print("\nТеперь вы можете:")
    print("  - Просмотреть контракты и заказы")
    print("  - Увидеть дефицит материалов")
    print("  - Проверить командировки")
    print("  - Посмотреть финансовый баланс")
    print("\nЗапустите систему: python backend.py")

if __name__ == '__main__':
    add_sample_data()
