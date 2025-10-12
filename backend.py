"""
Backend API для системы управления сервисными контрактами
Использует FastAPI для создания REST API
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import os
import shutil
from database import db
import json

app = FastAPI(title="Система управления сервисными контрактами")

# CORS middleware для доступа из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Директории для хранения файлов
UPLOAD_DIR = "uploads"
SCANS_DIR = "scans"
DOCUMENTS_DIR = "documents"

for directory in [UPLOAD_DIR, SCANS_DIR, DOCUMENTS_DIR]:
    os.makedirs(directory, exist_ok=True)


# ========== МОДЕЛИ ДАННЫХ ==========

class Contract(BaseModel):
    contract_number: str
    customer: str
    total_amount: float
    start_date: str
    end_date: str
    description: Optional[str] = None
    status: str = "active"


class WorkOrder(BaseModel):
    contract_id: int
    order_number: str
    device_name: str
    device_location: Optional[str] = None
    arrived_to_factory: bool = False
    repair_deadline: Optional[str] = None
    estimated_cost: Optional[float] = None
    description: Optional[str] = None
    priority: int = 0


class Component(BaseModel):
    component_code: str
    component_name: str
    description: Optional[str] = None
    unit_of_measure: str = "шт"
    unit_price: Optional[float] = None
    warehouse_stock: int = 0
    min_stock_level: int = 0


class BusinessTrip(BaseModel):
    employee_id: int
    work_order_id: Optional[int] = None
    contract_id: int
    destination: str
    start_date: str
    planned_end_date: str
    budget_allocated: Optional[float] = None
    notes: Optional[str] = None


class Payment(BaseModel):
    contract_id: int
    work_order_id: Optional[int] = None
    payment_type: str
    payment_stage: str
    amount: float
    payment_date: Optional[str] = None
    expected_date: Optional[str] = None
    invoice_number: Optional[str] = None


class Document(BaseModel):
    document_type: str
    contract_id: Optional[int] = None
    work_order_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    created_date: str
    paper_storage_location: Optional[str] = None


class MeetingProtocol(BaseModel):
    contract_id: Optional[int] = None
    meeting_date: str
    meeting_type: Optional[str] = None
    participants: str
    agenda: Optional[str] = None
    decisions: Optional[str] = None
    action_items: Optional[str] = None


# ========== API ENDPOINTS ==========

@app.get("/")
async def root():
    return {"message": "Система управления сервисными контрактами API"}


# ===== КОНТРАКТЫ =====

@app.get("/api/contracts")
async def get_contracts(status: Optional[str] = None):
    """Получить список всех контрактов"""
    query = "SELECT * FROM contracts"
    params = ()
    if status:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY created_at DESC"
    return db.execute_query(query, params)


@app.get("/api/contracts/{contract_id}")
async def get_contract(contract_id: int):
    """Получить детали контракта"""
    result = db.execute_query("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not result:
        raise HTTPException(status_code=404, detail="Контракт не найден")
    return result[0]


@app.post("/api/contracts")
async def create_contract(contract: Contract):
    """Создать новый контракт"""
    query = """
        INSERT INTO contracts (contract_number, customer, total_amount, start_date, end_date, description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    try:
        contract_id = db.execute_insert(query, (
            contract.contract_number, contract.customer, contract.total_amount,
            contract.start_date, contract.end_date, contract.description, contract.status
        ))
        return {"id": contract_id, "message": "Контракт создан"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/contracts/{contract_id}")
async def update_contract(contract_id: int, contract: Contract):
    """Обновить контракт"""
    query = """
        UPDATE contracts 
        SET contract_number=?, customer=?, total_amount=?, start_date=?, end_date=?, 
            description=?, status=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """
    db.execute_update(query, (
        contract.contract_number, contract.customer, contract.total_amount,
        contract.start_date, contract.end_date, contract.description, contract.status, contract_id
    ))
    return {"message": "Контракт обновлен"}


@app.get("/api/contracts/{contract_id}/dashboard")
async def get_contract_dashboard(contract_id: int):
    """Получить дашборд контракта с основной информацией"""
    # Основная информация о контракте
    contract = db.execute_query("SELECT * FROM contracts WHERE id = ?", (contract_id,))[0]
    
    # Заказы
    orders = db.execute_query(
        "SELECT * FROM work_orders WHERE contract_id = ? ORDER BY priority DESC, created_at DESC",
        (contract_id,)
    )
    
    # Платежи
    payments = db.execute_query(
        "SELECT * FROM payments WHERE contract_id = ? ORDER BY created_at DESC",
        (contract_id,)
    )
    
    total_paid = sum(p['amount'] for p in payments if p['status'] == 'completed')
    total_expected = sum(p['amount'] for p in payments if p['status'] == 'pending')
    
    # Командировки
    trips = db.execute_query(
        """SELECT bt.*, e.full_name, wo.device_location 
           FROM business_trips bt
           JOIN employees e ON bt.employee_id = e.id
           LEFT JOIN work_orders wo ON bt.work_order_id = wo.id
           WHERE bt.contract_id = ? AND bt.status IN ('planned', 'active')
           ORDER BY bt.start_date""",
        (contract_id,)
    )
    
    # Дефицит комплектующих
    deficit_query = """
        SELECT c.component_name, c.component_code, 
               SUM(oc.required_quantity) as total_required,
               SUM(oc.allocated_from_warehouse + oc.received_from_supplier) as total_allocated,
               SUM(oc.required_quantity - oc.allocated_from_warehouse - oc.received_from_supplier) as deficit
        FROM order_components oc
        JOIN components c ON oc.component_id = c.id
        JOIN work_orders wo ON oc.work_order_id = wo.id
        WHERE wo.contract_id = ? AND oc.status != 'completed'
        GROUP BY c.id
        HAVING deficit > 0
    """
    deficit = db.execute_query(deficit_query, (contract_id,))
    
    return {
        "contract": contract,
        "statistics": {
            "total_orders": len(orders),
            "active_orders": len([o for o in orders if o['status'] not in ['completed', 'cancelled']]),
            "total_paid": total_paid,
            "total_expected": total_expected,
            "budget_remaining": contract['total_amount'] - total_paid,
            "active_trips": len(trips)
        },
        "recent_orders": orders[:10],
        "deficit_components": deficit,
        "active_trips": trips,
        "payment_summary": {
            "total_amount": contract['total_amount'],
            "paid": total_paid,
            "expected": total_expected,
            "remaining": contract['total_amount'] - total_paid - total_expected
        }
    }


# ===== ЗАКАЗЫ НА РАБОТЫ =====

@app.get("/api/work-orders")
async def get_work_orders(
    contract_id: Optional[int] = None,
    status: Optional[str] = None
):
    """Получить список заказов"""
    query = "SELECT * FROM work_orders WHERE 1=1"
    params = []
    if contract_id:
        query += " AND contract_id = ?"
        params.append(contract_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY priority DESC, created_at DESC"
    return db.execute_query(query, tuple(params))


@app.post("/api/work-orders")
async def create_work_order(order: WorkOrder):
    """Создать новый заказ"""
    query = """
        INSERT INTO work_orders 
        (contract_id, order_number, device_name, device_location, arrived_to_factory,
         repair_deadline, estimated_cost, description, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    order_id = db.execute_insert(query, (
        order.contract_id, order.order_number, order.device_name, order.device_location,
        order.arrived_to_factory, order.repair_deadline, order.estimated_cost,
        order.description, order.priority
    ))
    return {"id": order_id, "message": "Заказ создан"}


@app.get("/api/work-orders/{order_id}")
async def get_work_order_details(order_id: int):
    """Получить детали заказа с компонентами"""
    order = db.execute_query("SELECT * FROM work_orders WHERE id = ?", (order_id,))
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    components = db.execute_query("""
        SELECT oc.*, c.component_name, c.component_code, c.unit_of_measure
        FROM order_components oc
        JOIN components c ON oc.component_id = c.id
        WHERE oc.work_order_id = ?
    """, (order_id,))
    
    return {
        "order": order[0],
        "components": components
    }


@app.put("/api/work-orders/{order_id}/status")
async def update_work_order_status(order_id: int, status: str):
    """Обновить статус заказа"""
    db.execute_update(
        "UPDATE work_orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, order_id)
    )
    return {"message": "Статус обновлен"}


# ===== КОМПЛЕКТУЮЩИЕ =====

@app.get("/api/components")
async def get_components():
    """Получить список всех комплектующих"""
    return db.execute_query("SELECT * FROM components ORDER BY component_name")


@app.get("/api/components/deficit")
async def get_component_deficit(contract_id: Optional[int] = None):
    """Получить список комплектующих с дефицитом"""
    query = """
        SELECT c.*, 
               SUM(oc.required_quantity) as total_required,
               SUM(oc.allocated_from_warehouse + oc.received_from_supplier) as total_allocated,
               SUM(oc.required_quantity - oc.allocated_from_warehouse - oc.received_from_supplier) as deficit,
               GROUP_CONCAT(DISTINCT wo.order_number) as affected_orders
        FROM order_components oc
        JOIN components c ON oc.component_id = c.id
        JOIN work_orders wo ON oc.work_order_id = wo.id
    """
    params = []
    if contract_id:
        query += " WHERE wo.contract_id = ?"
        params.append(contract_id)
    query += """
        GROUP BY c.id
        HAVING deficit > 0
        ORDER BY deficit DESC
    """
    return db.execute_query(query, tuple(params))


@app.post("/api/components")
async def create_component(component: Component):
    """Добавить новый компонент"""
    query = """
        INSERT INTO components 
        (component_code, component_name, description, unit_of_measure, unit_price, warehouse_stock, min_stock_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    component_id = db.execute_insert(query, (
        component.component_code, component.component_name, component.description,
        component.unit_of_measure, component.unit_price, component.warehouse_stock,
        component.min_stock_level
    ))
    return {"id": component_id, "message": "Компонент добавлен"}


# ===== КОМАНДИРОВКИ =====

@app.get("/api/business-trips")
async def get_business_trips(
    status: Optional[str] = None,
    contract_id: Optional[int] = None
):
    """Получить список командировок"""
    query = """
        SELECT bt.*, e.full_name as employee_name, c.contract_number,
               wo.order_number, wo.device_location
        FROM business_trips bt
        JOIN employees e ON bt.employee_id = e.id
        JOIN contracts c ON bt.contract_id = c.id
        LEFT JOIN work_orders wo ON bt.work_order_id = wo.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND bt.status = ?"
        params.append(status)
    if contract_id:
        query += " AND bt.contract_id = ?"
        params.append(contract_id)
    query += " ORDER BY bt.start_date DESC"
    return db.execute_query(query, tuple(params))


@app.post("/api/business-trips")
async def create_business_trip(trip: BusinessTrip):
    """Создать новую командировку"""
    query = """
        INSERT INTO business_trips 
        (employee_id, work_order_id, contract_id, destination, start_date, 
         planned_end_date, budget_allocated, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    trip_id = db.execute_insert(query, (
        trip.employee_id, trip.work_order_id, trip.contract_id, trip.destination,
        trip.start_date, trip.planned_end_date, trip.budget_allocated, trip.notes
    ))
    return {"id": trip_id, "message": "Командировка создана"}


@app.put("/api/business-trips/{trip_id}/extend")
async def extend_business_trip(trip_id: int, new_end_date: str):
    """Продлить командировку"""
    query = """
        UPDATE business_trips 
        SET planned_end_date = ?, extension_count = extension_count + 1,
            last_extension_date = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    db.execute_update(query, (new_end_date, trip_id))
    return {"message": "Командировка продлена"}


@app.get("/api/business-trips/map")
async def get_trips_map():
    """Получить карту текущих командировок"""
    query = """
        SELECT bt.*, e.full_name, wo.device_location, wo.order_number, c.contract_number
        FROM business_trips bt
        JOIN employees e ON bt.employee_id = e.id
        LEFT JOIN work_orders wo ON bt.work_order_id = wo.id
        JOIN contracts c ON bt.contract_id = c.id
        WHERE bt.status IN ('planned', 'active')
        ORDER BY bt.destination
    """
    return db.execute_query(query)


# ===== ПЛАТЕЖИ =====

@app.get("/api/payments")
async def get_payments(contract_id: Optional[int] = None):
    """Получить список платежей"""
    query = "SELECT * FROM payments WHERE 1=1"
    params = []
    if contract_id:
        query += " AND contract_id = ?"
        params.append(contract_id)
    query += " ORDER BY created_at DESC"
    return db.execute_query(query, tuple(params))


@app.post("/api/payments")
async def create_payment(payment: Payment):
    """Зарегистрировать платеж"""
    query = """
        INSERT INTO payments 
        (contract_id, work_order_id, payment_type, payment_stage, amount,
         payment_date, expected_date, invoice_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    payment_id = db.execute_insert(query, (
        payment.contract_id, payment.work_order_id, payment.payment_type,
        payment.payment_stage, payment.amount, payment.payment_date,
        payment.expected_date, payment.invoice_number
    ))
    return {"id": payment_id, "message": "Платеж зарегистрирован"}


@app.get("/api/payments/balance/{contract_id}")
async def get_contract_balance(contract_id: int):
    """Получить баланс по контракту"""
    contract = db.execute_query("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract:
        raise HTTPException(status_code=404, detail="Контракт не найден")
    
    payments = db.execute_query(
        "SELECT * FROM payments WHERE contract_id = ?", (contract_id,)
    )
    
    total_paid = sum(p['amount'] for p in payments if p['status'] == 'completed')
    total_pending = sum(p['amount'] for p in payments if p['status'] == 'pending')
    
    orders = db.execute_query(
        "SELECT SUM(actual_cost) as total_cost FROM work_orders WHERE contract_id = ? AND actual_cost IS NOT NULL",
        (contract_id,)
    )
    total_spent = orders[0]['total_cost'] or 0
    
    return {
        "contract_amount": contract[0]['total_amount'],
        "total_paid": total_paid,
        "total_pending": total_pending,
        "total_spent": total_spent,
        "available_balance": total_paid - total_spent,
        "expected_balance": total_paid + total_pending - total_spent
    }


# ===== ДОКУМЕНТЫ =====

@app.get("/api/documents")
async def get_documents(
    contract_id: Optional[int] = None,
    work_order_id: Optional[int] = None,
    document_type: Optional[str] = None
):
    """Получить список документов"""
    query = "SELECT * FROM documents WHERE 1=1"
    params = []
    if contract_id:
        query += " AND contract_id = ?"
        params.append(contract_id)
    if work_order_id:
        query += " AND work_order_id = ?"
        params.append(work_order_id)
    if document_type:
        query += " AND document_type = ?"
        params.append(document_type)
    query += " ORDER BY created_at DESC"
    return db.execute_query(query, tuple(params))


@app.post("/api/documents")
async def create_document(document: Document):
    """Создать новый документ"""
    query = """
        INSERT INTO documents 
        (document_type, contract_id, work_order_id, title, description,
         created_date, paper_storage_location)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    doc_id = db.execute_insert(query, (
        document.document_type, document.contract_id, document.work_order_id,
        document.title, document.description, document.created_date,
        document.paper_storage_location
    ))
    return {"id": doc_id, "message": "Документ создан"}


@app.post("/api/documents/{doc_id}/upload-scan")
async def upload_scan(doc_id: int, file: UploadFile = File(...)):
    """Загрузить скан документа"""
    file_path = os.path.join(SCANS_DIR, f"{doc_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    db.execute_update(
        "UPDATE documents SET scan_path = ? WHERE id = ?",
        (file_path, doc_id)
    )
    return {"message": "Скан загружен", "path": file_path}


@app.get("/api/documents/{doc_id}/download-scan")
async def download_scan(doc_id: int):
    """Скачать скан документа"""
    doc = db.execute_query("SELECT scan_path FROM documents WHERE id = ?", (doc_id,))
    if not doc or not doc[0]['scan_path']:
        raise HTTPException(status_code=404, detail="Скан не найден")
    return FileResponse(doc[0]['scan_path'])


# ===== ПРОТОКОЛЫ СОВЕЩАНИЙ =====

@app.get("/api/meeting-protocols")
async def get_meeting_protocols(contract_id: Optional[int] = None):
    """Получить список протоколов"""
    query = "SELECT * FROM meeting_protocols WHERE 1=1"
    params = []
    if contract_id:
        query += " AND contract_id = ?"
        params.append(contract_id)
    query += " ORDER BY meeting_date DESC"
    return db.execute_query(query, tuple(params))


@app.post("/api/meeting-protocols")
async def create_meeting_protocol(protocol: MeetingProtocol):
    """Создать протокол совещания"""
    query = """
        INSERT INTO meeting_protocols 
        (contract_id, meeting_date, meeting_type, participants, agenda, decisions, action_items)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    protocol_id = db.execute_insert(query, (
        protocol.contract_id, protocol.meeting_date, protocol.meeting_type,
        protocol.participants, protocol.agenda, protocol.decisions, protocol.action_items
    ))
    return {"id": protocol_id, "message": "Протокол создан"}


@app.get("/api/protocol-tasks")
async def get_protocol_tasks(status: Optional[str] = None):
    """Получить задачи из протоколов"""
    query = "SELECT * FROM protocol_tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY deadline ASC"
    return db.execute_query(query, tuple(params))


# ===== АНАЛИТИКА =====

@app.get("/api/analytics/overview")
async def get_analytics_overview():
    """Получить общую аналитику"""
    contracts = db.execute_query("SELECT COUNT(*) as count, status FROM contracts GROUP BY status")
    orders = db.execute_query("SELECT COUNT(*) as count, status FROM work_orders GROUP BY status")
    trips = db.execute_query("SELECT COUNT(*) as count, status FROM business_trips GROUP BY status")
    
    total_budget = db.execute_query("SELECT SUM(total_amount) as total FROM contracts WHERE status = 'active'")[0]['total']
    total_paid = db.execute_query("SELECT SUM(amount) as total FROM payments WHERE status = 'completed'")[0]['total']
    
    return {
        "contracts_by_status": contracts,
        "orders_by_status": orders,
        "trips_by_status": trips,
        "financial": {
            "total_budget": total_budget or 0,
            "total_paid": total_paid or 0
        }
    }


# Подключение расширенного API
try:
    from api_extended import init_extended_api
    init_extended_api(app)
except ImportError:
    print("⚠ Extended API module not found, skipping...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
