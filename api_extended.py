"""
Расширенные API endpoints для генерации документов и отчетов
Подключается к основному backend.py
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from document_generator import doc_generator
from excel_manager import excel_manager
from database import db

router = APIRouter(prefix="/api/extended", tags=["Extended Functions"])


# ========== МОДЕЛИ ==========

class AcceptanceActRequest(BaseModel):
    work_order_id: int
    act_number: str
    act_date: str
    customer_representative: str
    executor_representative: str


class MilitaryCertificateRequest(BaseModel):
    work_order_id: int
    certificate_number: str
    certificate_date: str
    military_rep: str


class PaymentRequestLetterRequest(BaseModel):
    contract_id: int
    requested_amount: float
    our_company: str
    our_address: str
    signatory: str


# ========== ГЕНЕРАЦИЯ ДОКУМЕНТОВ ==========

@router.post("/generate/acceptance-act")
async def generate_acceptance_act(request: AcceptanceActRequest):
    """
    Генерация акта сдачи-приемки выполненных работ
    """
    try:
        filepath = doc_generator.generate_acceptance_act(
            work_order_id=request.work_order_id,
            data=request.dict()
        )
        return {
            "success": True,
            "message": "Акт успешно сгенерирован",
            "filepath": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate/acceptance-act/{work_order_id}/download")
async def download_acceptance_act(work_order_id: int):
    """
    Скачать сгенерированный акт
    """
    # Найти последний сгенерированный акт для данного заказа
    docs = db.execute_query("""
        SELECT file_path FROM documents 
        WHERE work_order_id = ? AND document_type = 'act_acceptance'
        ORDER BY created_at DESC LIMIT 1
    """, (work_order_id,))
    
    if not docs or not docs[0]['file_path']:
        raise HTTPException(status_code=404, detail="Акт не найден")
    
    return FileResponse(docs[0]['file_path'], filename="act.docx")


@router.post("/generate/military-certificate")
async def generate_military_certificate(request: MilitaryCertificateRequest):
    """
    Генерация удостоверения военпреда
    """
    try:
        filepath = doc_generator.generate_military_certificate(
            work_order_id=request.work_order_id,
            data=request.dict()
        )
        return {
            "success": True,
            "message": "Удостоверение успешно сгенерировано",
            "filepath": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/payment-request-letter")
async def generate_payment_request_letter(request: PaymentRequestLetterRequest):
    """
    Генерация письма о необходимости доплаты
    """
    try:
        filepath = doc_generator.generate_payment_request_letter(
            contract_id=request.contract_id,
            data=request.dict()
        )
        return {
            "success": True,
            "message": "Письмо успешно сгенерировано",
            "filepath": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== EXCEL ОТЧЕТЫ ==========

@router.get("/reports/payment-tracking/{contract_id}")
async def generate_payment_tracking_report(contract_id: int):
    """
    Сформировать таблицу учета оплат против выполненных работ
    """
    try:
        filepath = excel_manager.create_payment_tracking_table(contract_id)
        return FileResponse(
            filepath,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f'payment_tracking_{contract_id}.xlsx'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/components-deficit")
async def generate_components_deficit_report(contract_id: Optional[int] = None):
    """
    Сформировать отчет по дефициту комплектующих
    """
    try:
        filepath = excel_manager.create_components_deficit_report(contract_id)
        return FileResponse(
            filepath,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename='components_deficit.xlsx'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/trips-schedule")
async def generate_trips_schedule(contract_id: Optional[int] = None):
    """
    Сформировать график командировок
    """
    try:
        filepath = excel_manager.create_trips_schedule(contract_id)
        return FileResponse(
            filepath,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename='trips_schedule.xlsx'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== БЫСТРЫЕ ЗАПРОСЫ ДЛЯ МЕНЕДЖЕРА ==========

@router.get("/quick/budget-status/{contract_id}")
async def get_budget_status(contract_id: int):
    """
    Быстрая проверка состояния бюджета контракта
    """
    contract = db.execute_query("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract:
        raise HTTPException(status_code=404, detail="Контракт не найден")
    
    contract = contract[0]
    
    # Платежи
    payments = db.execute_query(
        "SELECT SUM(amount) as total, status FROM payments WHERE contract_id = ? GROUP BY status",
        (contract_id,)
    )
    
    paid = sum(p['total'] for p in payments if p['status'] == 'completed')
    pending = sum(p['total'] for p in payments if p['status'] == 'pending')
    
    # Затраты
    spent = db.execute_query(
        "SELECT SUM(actual_cost) as total FROM work_orders WHERE contract_id = ? AND actual_cost IS NOT NULL",
        (contract_id,)
    )[0]['total'] or 0
    
    # Резерв под заказы
    reserved = db.execute_query(
        "SELECT SUM(estimated_cost) as total FROM work_orders WHERE contract_id = ? AND status != 'completed' AND estimated_cost IS NOT NULL",
        (contract_id,)
    )[0]['total'] or 0
    
    available = paid - spent - reserved
    
    return {
        "contract_number": contract['contract_number'],
        "total_amount": contract['total_amount'],
        "paid": paid,
        "pending": pending,
        "spent": spent,
        "reserved": reserved,
        "available": available,
        "can_proceed": available > 0,
        "warning": available < 0,
        "warning_message": f"Дефицит средств: {abs(available)} руб." if available < 0 else None
    }


@router.get("/quick/deficit-alert")
async def get_deficit_alert(contract_id: Optional[int] = None):
    """
    Предупреждение о дефиците комплектующих
    """
    query = """
        SELECT 
            c.component_name,
            SUM(oc.required_quantity - oc.allocated_from_warehouse - oc.received_from_supplier) as deficit,
            GROUP_CONCAT(DISTINCT wo.order_number) as affected_orders,
            MIN(wo.repair_deadline) as nearest_deadline
        FROM order_components oc
        JOIN components c ON oc.component_id = c.id
        JOIN work_orders wo ON oc.work_order_id = wo.id
        WHERE oc.status != 'completed'
    """
    
    params = []
    if contract_id:
        query += " AND wo.contract_id = ?"
        params.append(contract_id)
    
    query += " GROUP BY c.id HAVING deficit > 0 ORDER BY nearest_deadline"
    
    deficit_items = db.execute_query(query, tuple(params))
    
    if not deficit_items:
        return {
            "has_deficit": False,
            "message": "Дефицита комплектующих нет"
        }
    
    critical_count = len([d for d in deficit_items if d['nearest_deadline'] and 
                          (datetime.strptime(d['nearest_deadline'], '%Y-%m-%d') - datetime.now()).days < 7])
    
    return {
        "has_deficit": True,
        "total_components": len(deficit_items),
        "critical_count": critical_count,
        "message": f"⚠️ Дефицит {len(deficit_items)} комплектующих! {critical_count} критичных!",
        "items": deficit_items[:5],  # Топ 5 самых срочных
        "risk_level": "high" if critical_count > 0 else "medium"
    }


@router.get("/quick/trips-now")
async def get_current_trips():
    """
    Где сейчас находятся сотрудники
    """
    query = """
        SELECT 
            e.full_name,
            bt.destination,
            bt.start_date,
            bt.planned_end_date,
            c.contract_number,
            wo.order_number
        FROM business_trips bt
        JOIN employees e ON bt.employee_id = e.id
        JOIN contracts c ON bt.contract_id = c.id
        LEFT JOIN work_orders wo ON bt.work_order_id = wo.id
        WHERE bt.status = 'active'
        ORDER BY bt.destination
    """
    
    trips = db.execute_query(query)
    
    # Группировка по местоположению
    by_location = {}
    for trip in trips:
        loc = trip['destination']
        if loc not in by_location:
            by_location[loc] = []
        by_location[loc].append({
            'employee': trip['full_name'],
            'contract': trip['contract_number'],
            'order': trip['order_number'],
            'until': trip['planned_end_date']
        })
    
    return {
        "total_trips": len(trips),
        "locations": len(by_location),
        "by_location": by_location,
        "summary": [f"{loc}: {len(emps)} чел." for loc, emps in by_location.items()]
    }


@router.get("/quick/urgent-orders")
async def get_urgent_orders():
    """
    Срочные заказы, требующие внимания
    """
    from datetime import datetime, timedelta
    
    urgent_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    query = """
        SELECT 
            wo.*,
            c.contract_number,
            c.customer
        FROM work_orders wo
        JOIN contracts c ON wo.contract_id = c.id
        WHERE wo.status != 'completed' 
        AND wo.status != 'cancelled'
        AND wo.repair_deadline <= ?
        ORDER BY wo.repair_deadline, wo.priority DESC
    """
    
    orders = db.execute_query(query, (urgent_date,))
    
    return {
        "count": len(orders),
        "message": f"⚠️ {len(orders)} срочных заказов!" if orders else "✅ Срочных заказов нет",
        "orders": [
            {
                "order_number": o['order_number'],
                "device": o['device_name'],
                "deadline": o['repair_deadline'],
                "days_left": (datetime.strptime(o['repair_deadline'], '%Y-%m-%d') - datetime.now()).days,
                "contract": o['contract_number'],
                "status": o['status']
            }
            for o in orders
        ]
    }


@router.get("/quick/manager-dashboard")
async def get_manager_dashboard():
    """
    Полный дашборд для менеджера - вся критичная информация
    """
    # Контракты
    contracts = db.execute_query(
        "SELECT COUNT(*) as count, status FROM contracts GROUP BY status"
    )
    
    # Бюджет
    total_budget = db.execute_query(
        "SELECT SUM(total_amount) as total FROM contracts WHERE status = 'active'"
    )[0]['total'] or 0
    
    total_paid = db.execute_query(
        "SELECT SUM(amount) as total FROM payments WHERE status = 'completed'"
    )[0]['total'] or 0
    
    # Заказы
    orders_stats = db.execute_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as new,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN priority >= 2 THEN 1 ELSE 0 END) as high_priority
        FROM work_orders
        WHERE status != 'cancelled'
    """)[0]
    
    # Командировки
    active_trips = db.execute_query(
        "SELECT COUNT(*) as count FROM business_trips WHERE status = 'active'"
    )[0]['count']
    
    # Дефицит
    deficit = db.execute_query("""
        SELECT COUNT(DISTINCT c.id) as count
        FROM order_components oc
        JOIN components c ON oc.component_id = c.id
        WHERE oc.required_quantity > (oc.allocated_from_warehouse + oc.received_from_supplier)
        AND oc.status != 'completed'
    """)[0]['count']
    
    return {
        "contracts": {
            "active": next((c['count'] for c in contracts if c['status'] == 'active'), 0),
            "total": sum(c['count'] for c in contracts)
        },
        "budget": {
            "total": total_budget,
            "paid": total_paid,
            "utilization_percent": round((total_paid / total_budget * 100) if total_budget > 0 else 0, 1)
        },
        "orders": orders_stats,
        "trips": {
            "active": active_trips
        },
        "alerts": {
            "deficit_components": deficit,
            "has_critical_issues": deficit > 0 or orders_stats['high_priority'] > 3
        },
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# Подключение роутера к основному приложению
def init_extended_api(app):
    """Инициализация расширенного API"""
    app.include_router(router)
    print("✓ Extended API endpoints loaded")
