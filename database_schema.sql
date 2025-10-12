-- Система управления сервисными контрактами
-- Database Schema for Service Contract Management System

-- Основная таблица контрактов
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_number VARCHAR(100) UNIQUE NOT NULL,
    contract_name VARCHAR(500) NOT NULL,
    customer VARCHAR(300) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    total_amount DECIMAL(15,2),
    advance_amount DECIMAL(15,2),
    final_amount DECIMAL(15,2),
    status VARCHAR(50) DEFAULT 'active', -- active, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Субсчета контрактов (для учета финансов)
CREATE TABLE contract_subaccounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    account_code VARCHAR(100) NOT NULL,
    balance DECIMAL(15,2) DEFAULT 0,
    reserved_amount DECIMAL(15,2) DEFAULT 0,
    available_amount DECIMAL(15,2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

-- Заказы в рамках контрактов
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    order_number VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(300),
    region VARCHAR(100),
    device_type VARCHAR(200),
    device_serial VARCHAR(200),
    defect_report_date DATE,
    planned_start_date DATE,
    planned_end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,
    status VARCHAR(50) DEFAULT 'created', -- created, planned, in_progress, completed, cancelled
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    estimated_cost DECIMAL(15,2),
    actual_cost DECIMAL(15,2),
    is_business_trip BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

-- Материалы и комплектующие
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    unit VARCHAR(50),
    current_stock INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 0,
    price DECIMAL(10,2),
    supplier VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Потребности в материалах для заказов
CREATE TABLE order_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    required_quantity INTEGER NOT NULL,
    allocated_quantity INTEGER DEFAULT 0,
    source VARCHAR(50), -- warehouse, external
    status VARCHAR(50) DEFAULT 'required', -- required, ordered, received, allocated
    notes TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

-- Сотрудники
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_number VARCHAR(50) UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    position VARCHAR(100),
    department VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(100),
    passport_data VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Командировки
CREATE TABLE business_trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    order_id INTEGER,
    destination VARCHAR(300) NOT NULL,
    purpose TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    extension_date DATE,
    status VARCHAR(50) DEFAULT 'planned', -- planned, approved, in_progress, completed, cancelled
    travel_order_number VARCHAR(100),
    accommodation VARCHAR(300),
    transport_info TEXT,
    daily_allowance DECIMAL(10,2),
    total_cost DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Платежи по контрактам
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    payment_type VARCHAR(50) NOT NULL, -- advance, final, additional
    amount DECIMAL(15,2) NOT NULL,
    payment_date DATE,
    expected_date DATE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, received, overdue
    invoice_number VARCHAR(100),
    payment_document VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

-- Документы
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_type VARCHAR(100) NOT NULL,
    document_number VARCHAR(100),
    title VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    scan_path VARCHAR(1000),
    physical_location VARCHAR(500),
    contract_id INTEGER,
    order_id INTEGER,
    business_trip_id INTEGER,
    created_date DATE,
    signed_date DATE,
    status VARCHAR(50) DEFAULT 'draft', -- draft, signed, archived
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (business_trip_id) REFERENCES business_trips(id)
);

-- Переписка и совещания
CREATE TABLE communications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50) NOT NULL, -- email, meeting, call, letter
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    participants TEXT,
    date_time DATETIME NOT NULL,
    contract_id INTEGER,
    order_id INTEGER,
    status VARCHAR(50) DEFAULT 'active', -- active, closed
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Задачи из протоколов совещаний
CREATE TABLE communication_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    communication_id INTEGER NOT NULL,
    task_description TEXT NOT NULL,
    responsible_party VARCHAR(200),
    due_date DATE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, overdue
    completion_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (communication_id) REFERENCES communications(id)
);

-- Поставщики
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(300) NOT NULL,
    contact_person VARCHAR(200),
    phone VARCHAR(50),
    email VARCHAR(100),
    address TEXT,
    payment_terms VARCHAR(200),
    rating INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Заказы поставщикам
CREATE TABLE supplier_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    order_id INTEGER,
    order_number VARCHAR(100),
    order_date DATE NOT NULL,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    total_amount DECIMAL(15,2),
    status VARCHAR(50) DEFAULT 'ordered', -- ordered, confirmed, shipped, received, cancelled
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Позиции в заказах поставщикам
CREATE TABLE supplier_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_order_id INTEGER NOT NULL,
    material_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    total_price DECIMAL(15,2),
    received_quantity INTEGER DEFAULT 0,
    FOREIGN KEY (supplier_order_id) REFERENCES supplier_orders(id),
    FOREIGN KEY (material_id) REFERENCES materials(id)
);

-- Индексы для оптимизации запросов
CREATE INDEX idx_contracts_number ON contracts(contract_number);
CREATE INDEX idx_orders_contract ON orders(contract_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_materials_part_number ON materials(part_number);
CREATE INDEX idx_business_trips_employee ON business_trips(employee_id);
CREATE INDEX idx_business_trips_dates ON business_trips(start_date, end_date);
CREATE INDEX idx_payments_contract ON payments(contract_id);
CREATE INDEX idx_documents_contract ON documents(contract_id);
CREATE INDEX idx_communications_contract ON communications(contract_id);

-- Представления для аналитики
CREATE VIEW contract_summary AS
SELECT 
    c.id,
    c.contract_number,
    c.contract_name,
    c.total_amount,
    COALESCE(cs.balance, 0) as current_balance,
    COUNT(o.id) as total_orders,
    COUNT(CASE WHEN o.status = 'completed' THEN 1 END) as completed_orders,
    COUNT(CASE WHEN o.status = 'in_progress' THEN 1 END) as active_orders,
    SUM(CASE WHEN p.status = 'received' THEN p.amount ELSE 0 END) as received_payments
FROM contracts c
LEFT JOIN contract_subaccounts cs ON c.id = cs.contract_id
LEFT JOIN orders o ON c.id = o.contract_id
LEFT JOIN payments p ON c.id = p.contract_id
GROUP BY c.id, c.contract_number, c.contract_name, c.total_amount, cs.balance;

CREATE VIEW material_deficit AS
SELECT 
    m.id,
    m.part_number,
    m.name,
    m.current_stock,
    m.min_stock,
    SUM(om.required_quantity - om.allocated_quantity) as total_deficit,
    COUNT(DISTINCT om.order_id) as orders_affected
FROM materials m
LEFT JOIN order_materials om ON m.id = om.material_id AND om.status != 'allocated'
WHERE m.current_stock < m.min_stock OR om.required_quantity > om.allocated_quantity
GROUP BY m.id, m.part_number, m.name, m.current_stock, m.min_stock
HAVING total_deficit > 0;

CREATE VIEW active_business_trips AS
SELECT 
    bt.id,
    e.full_name as employee_name,
    bt.destination,
    bt.start_date,
    bt.end_date,
    bt.status,
    o.order_number,
    c.contract_number
FROM business_trips bt
JOIN employees e ON bt.employee_id = e.id
LEFT JOIN orders o ON bt.order_id = o.id
LEFT JOIN contracts c ON o.contract_id = c.id
WHERE bt.status IN ('planned', 'approved', 'in_progress')
ORDER BY bt.start_date;