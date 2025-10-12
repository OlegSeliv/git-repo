"""
Основной API сервер для системы управления сервисными контрактами
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uvicorn
import os
import shutil
from pathlib import Path

from database import DatabaseManager
from document_generator import DocumentGenerator
from analytics import AnalyticsEngine

app = FastAPI(title="Система управления сервисными контрактами")

# Настройка CORS для локальной работы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация компонентов
db = DatabaseManager()
doc_gen = DocumentGenerator()
analytics = AnalyticsEngine(db)

# Создание директорий для хранения файлов
UPLOAD_DIR = Path("uploads")
DOCUMENTS_DIR = Path("documents")
SCANS_DIR = Path("scans")

for dir in [UPLOAD_DIR, DOCUMENTS_DIR, SCANS_DIR]:
    dir.mkdir(exist_ok=True)

# Pydantic модели для API

class Contract(BaseModel):
    contract_number: str
    customer_name: str
    start_date: date
    end_date: date
    total_amount: float
    advance_amount: Optional[float] = 0
    notes: Optional[str] = ""

class Order(BaseModel):
    order_number: str
    contract_id: int
    description: str
    location: str
    device_serial: Optional[str] = ""
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    priority: Optional[str] = "normal"
    estimated_cost: Optional[float] = 0
    notes: Optional[str] = ""

class Material(BaseModel):
    article: str
    name: str
    unit: Optional[str] = "шт"
    quantity_warehouse: Optional[float] = 0
    quantity_minimum: Optional[float] = 0
    price: Optional[float] = 0
    supplier: Optional[str] = ""
    lead_time_days: Optional[int] = 0

class BusinessTrip(BaseModel):
    employee_name: str
    order_id: Optional[int] = None
    location: str
    start_date: date
    end_date: date
    travel_order_number: Optional[str] = ""
    accommodation: Optional[str] = ""
    transport_type: Optional[str] = ""
    estimated_expenses: Optional[float] = 0

class FinancialTransaction(BaseModel):
    contract_id: int
    order_id: Optional[int] = None
    transaction_type: str  # 'advance', 'final', 'expense'
    amount: float
    payment_date: date
    document_number: Optional[str] = ""
    notes: Optional[str] = ""

class DefectAct(BaseModel):
    order_id: int
    act_number: str
    act_date: date
    device_info: str
    defects_found: str
    materials_required: List[Dict[str, Any]]
    estimated_repair_time: Optional[int] = 0

# API Endpoints

# === КОНТРАКТЫ ===
@app.get("/api/contracts")
async def get_contracts(status: Optional[str] = None):
    """Получение списка контрактов"""
    query = "SELECT * FROM contracts"
    params = ()
    if status:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY created_at DESC"
    return db.execute_query(query, params)

@app.post("/api/contracts")
async def create_contract(contract: Contract):
    """Создание нового контракта"""
    query = '''
    INSERT INTO contracts (
        contract_number, customer_name, start_date, end_date, 
        total_amount, advance_amount, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        contract.contract_number, contract.customer_name,
        contract.start_date, contract.end_date,
        contract.total_amount, contract.advance_amount, contract.notes
    )
    contract_id = db.execute_update(query, params)
    return {"id": contract_id, "message": "Контракт создан"}

@app.get("/api/contracts/{contract_id}")
async def get_contract(contract_id: int):
    """Получение детальной информации о контракте"""
    # Основная информация о контракте
    contract = db.execute_query(
        "SELECT * FROM contracts WHERE id = ?", (contract_id,)
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Контракт не найден")
    
    result = contract[0]
    
    # Финансовый статус
    result['financial_status'] = db.get_contract_financial_status(contract_id)
    
    # Заказы по контракту
    result['orders'] = db.execute_query(
        "SELECT * FROM orders WHERE contract_id = ? ORDER BY created_at DESC",
        (contract_id,)
    )
    
    return result

# === ЗАКАЗЫ ===
@app.get("/api/orders")
async def get_orders(
    contract_id: Optional[int] = None,
    status: Optional[str] = None
):
    """Получение списка заказов"""
    query = "SELECT o.*, c.contract_number FROM orders o JOIN contracts c ON o.contract_id = c.id WHERE 1=1"
    params = []
    
    if contract_id:
        query += " AND o.contract_id = ?"
        params.append(contract_id)
    
    if status:
        query += " AND o.status = ?"
        params.append(status)
    
    query += " ORDER BY o.created_at DESC"
    return db.execute_query(query, tuple(params))

@app.post("/api/orders")
async def create_order(order: Order):
    """Создание нового заказа"""
    query = '''
    INSERT INTO orders (
        order_number, contract_id, description, location,
        device_serial, planned_start, planned_end, priority,
        estimated_cost, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        order.order_number, order.contract_id, order.description,
        order.location, order.device_serial, order.planned_start,
        order.planned_end, order.priority, order.estimated_cost, order.notes
    )
    order_id = db.execute_update(query, params)
    return {"id": order_id, "message": "Заказ создан"}

@app.get("/api/orders/{order_id}/materials")
async def get_order_materials(order_id: int):
    """Получение материалов для заказа с проверкой наличия"""
    return db.check_material_availability(order_id)

# === МАТЕРИАЛЫ И СКЛАД ===
@app.get("/api/materials")
async def get_materials(show_deficit: bool = False):
    """Получение списка материалов"""
    query = "SELECT * FROM materials"
    if show_deficit:
        query += " WHERE (quantity_warehouse - quantity_reserved) < quantity_minimum"
    query += " ORDER BY name"
    return db.execute_query(query)

@app.post("/api/materials")
async def create_material(material: Material):
    """Добавление нового материала"""
    query = '''
    INSERT INTO materials (
        article, name, unit, quantity_warehouse,
        quantity_minimum, price, supplier, lead_time_days
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        material.article, material.name, material.unit,
        material.quantity_warehouse, material.quantity_minimum,
        material.price, material.supplier, material.lead_time_days
    )
    material_id = db.execute_update(query, params)
    return {"id": material_id, "message": "Материал добавлен"}

@app.post("/api/orders/{order_id}/materials")
async def assign_materials_to_order(
    order_id: int,
    materials: List[Dict[str, Any]]
):
    """Назначение материалов на заказ"""
    for mat in materials:
        query = '''
        INSERT INTO order_materials (
            order_id, material_id, quantity_required
        ) VALUES (?, ?, ?)
        '''
        db.execute_update(query, (order_id, mat['material_id'], mat['quantity']))
    return {"message": "Материалы назначены на заказ"}

# === КОМАНДИРОВКИ ===
@app.get("/api/business-trips")
async def get_business_trips(active_only: bool = True):
    """Получение списка командировок"""
    if active_only:
        return db.get_active_business_trips()
    else:
        query = '''
        SELECT bt.*, o.order_number, c.contract_number
        FROM business_trips bt
        LEFT JOIN orders o ON bt.order_id = o.id
        LEFT JOIN contracts c ON o.contract_id = c.id
        ORDER BY bt.start_date DESC
        '''
        return db.execute_query(query)

@app.post("/api/business-trips")
async def create_business_trip(trip: BusinessTrip):
    """Создание командировки"""
    query = '''
    INSERT INTO business_trips (
        employee_name, order_id, location, start_date, end_date,
        travel_order_number, accommodation, transport_type,
        estimated_expenses, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned')
    '''
    params = (
        trip.employee_name, trip.order_id, trip.location,
        trip.start_date, trip.end_date, trip.travel_order_number,
        trip.accommodation, trip.transport_type, trip.estimated_expenses
    )
    trip_id = db.execute_update(query, params)
    return {"id": trip_id, "message": "Командировка создана"}

@app.put("/api/business-trips/{trip_id}/extend")
async def extend_business_trip(trip_id: int, new_end_date: date):
    """Продление командировки"""
    query = "UPDATE business_trips SET extended_to = ? WHERE id = ?"
    db.execute_update(query, (new_end_date, trip_id))
    return {"message": "Командировка продлена"}

# === ФИНАНСЫ ===
@app.get("/api/financial/summary")
async def get_financial_summary(contract_id: Optional[int] = None):
    """Получение финансовой сводки"""
    if contract_id:
        return db.get_contract_financial_status(contract_id)
    else:
        query = '''
        SELECT 
            COUNT(DISTINCT id) as total_contracts,
            SUM(total_amount) as total_contract_value,
            SUM(advance_received) as total_advance_received,
            SUM(final_received) as total_final_received,
            SUM(total_amount - advance_received - final_received) as total_balance
        FROM contracts
        WHERE status = 'active'
        '''
        return db.execute_query(query)[0]

@app.post("/api/financial/transactions")
async def create_transaction(transaction: FinancialTransaction):
    """Регистрация финансовой операции"""
    query = '''
    INSERT INTO financial_transactions (
        contract_id, order_id, transaction_type, amount,
        payment_date, document_number, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        transaction.contract_id, transaction.order_id,
        transaction.transaction_type, transaction.amount,
        transaction.payment_date, transaction.document_number,
        transaction.notes
    )
    trans_id = db.execute_update(query, params)
    
    # Обновление баланса контракта
    if transaction.transaction_type == 'advance':
        db.execute_update(
            "UPDATE contracts SET advance_received = advance_received + ? WHERE id = ?",
            (transaction.amount, transaction.contract_id)
        )
    elif transaction.transaction_type == 'final':
        db.execute_update(
            "UPDATE contracts SET final_received = final_received + ? WHERE id = ?",
            (transaction.amount, transaction.contract_id)
        )
    
    return {"id": trans_id, "message": "Транзакция зарегистрирована"}

# === ДОКУМЕНТЫ ===
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    contract_id: Optional[int] = Form(None),
    order_id: Optional[int] = Form(None),
    title: str = Form(...),
    physical_location: Optional[str] = Form("")
):
    """Загрузка документа"""
    # Сохранение файла
    file_path = DOCUMENTS_DIR / f"{datetime.now().timestamp()}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Запись в БД
    query = '''
    INSERT INTO documents (
        document_type, contract_id, order_id, title,
        file_path, physical_location, status
    ) VALUES (?, ?, ?, ?, ?, ?, 'active')
    '''
    params = (
        document_type, contract_id, order_id, title,
        str(file_path), physical_location
    )
    doc_id = db.execute_update(query, params)
    
    return {"id": doc_id, "file_path": str(file_path), "message": "Документ загружен"}

@app.post("/api/documents/{doc_id}/scan")
async def upload_scan(doc_id: int, file: UploadFile = File(...)):
    """Загрузка скана документа"""
    # Сохранение скана
    scan_path = SCANS_DIR / f"scan_{doc_id}_{file.filename}"
    with open(scan_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Обновление записи в БД
    query = "UPDATE documents SET scan_path = ? WHERE id = ?"
    db.execute_update(query, (str(scan_path), doc_id))
    
    return {"scan_path": str(scan_path), "message": "Скан загружен"}

@app.get("/api/documents")
async def get_documents(
    document_type: Optional[str] = None,
    contract_id: Optional[int] = None,
    order_id: Optional[int] = None
):
    """Получение списка документов"""
    query = "SELECT * FROM documents WHERE 1=1"
    params = []
    
    if document_type:
        query += " AND document_type = ?"
        params.append(document_type)
    
    if contract_id:
        query += " AND contract_id = ?"
        params.append(contract_id)
    
    if order_id:
        query += " AND order_id = ?"
        params.append(order_id)
    
    query += " ORDER BY created_at DESC"
    return db.execute_query(query, tuple(params))

# === АКТЫ ДЕФЕКТАЦИИ ===
@app.post("/api/defect-acts")
async def create_defect_act(act: DefectAct):
    """Создание акта дефектации"""
    import json
    query = '''
    INSERT INTO defect_acts (
        order_id, act_number, act_date, device_info,
        defects_found, materials_required, estimated_repair_time
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        act.order_id, act.act_number, act.act_date,
        act.device_info, act.defects_found,
        json.dumps(act.materials_required), act.estimated_repair_time
    )
    act_id = db.execute_update(query, params)
    
    # Автоматическое создание требований на материалы
    for mat in act.materials_required:
        # Проверяем, есть ли материал в базе
        material = db.execute_query(
            "SELECT id FROM materials WHERE article = ?",
            (mat['article'],)
        )
        if material:
            query = '''
            INSERT INTO order_materials (
                order_id, material_id, quantity_required, status
            ) VALUES (?, ?, ?, 'required')
            '''
            db.execute_update(query, (
                act.order_id, material[0]['id'], mat['quantity']
            ))
    
    return {"id": act_id, "message": "Акт дефектации создан"}

# === ЗАДАЧИ И ПРОТОКОЛЫ ===
@app.get("/api/tasks/pending")
async def get_pending_tasks():
    """Получение невыполненных задач"""
    return db.get_pending_tasks()

@app.put("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int, notes: Optional[str] = ""):
    """Отметка задачи как выполненной"""
    query = '''
    UPDATE tasks 
    SET status = 'completed', 
        completion_date = date('now'),
        notes = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    '''
    db.execute_update(query, (notes, task_id))
    return {"message": "Задача выполнена"}

# === АНАЛИТИКА ===
@app.get("/api/analytics/dashboard")
async def get_dashboard_data():
    """Получение данных для дашборда"""
    return analytics.get_dashboard_data()

@app.get("/api/analytics/contract/{contract_id}/report")
async def get_contract_report(contract_id: int):
    """Генерация отчета по контракту"""
    return analytics.generate_contract_report(contract_id)

# === ГЕНЕРАЦИЯ ДОКУМЕНТОВ ===
@app.post("/api/generate/completion-act")
async def generate_completion_act(order_id: int):
    """Генерация акта выполненных работ"""
    file_path = doc_gen.generate_completion_act(order_id)
    return FileResponse(file_path)

@app.post("/api/generate/deficiency-letter")
async def generate_deficiency_letter(contract_id: int):
    """Генерация письма о нехватке средств"""
    file_path = doc_gen.generate_deficiency_letter(contract_id)
    return FileResponse(file_path)

# === УВЕДОМЛЕНИЯ ===
@app.get("/api/notifications")
async def get_notifications(unread_only: bool = True):
    """Получение уведомлений"""
    query = "SELECT * FROM notifications"
    if unread_only:
        query += " WHERE is_read = 0"
    query += " ORDER BY created_at DESC LIMIT 50"
    return db.execute_query(query)

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int):
    """Отметка уведомления как прочитанного"""
    query = "UPDATE notifications SET is_read = 1 WHERE id = ?"
    db.execute_update(query, (notification_id,))
    return {"message": "Уведомление прочитано"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)