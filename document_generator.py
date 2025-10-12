"""
Модуль для автоматической генерации документов
Создает акты, удостоверения, письма на основе шаблонов
"""

from docx import Document
from docx.shared import Pt, Inches
from datetime import datetime
from typing import Dict, Any
import os
from database import db


class DocumentGenerator:
    def __init__(self, templates_dir: str = "templates", output_dir: str = "generated_docs"):
        self.templates_dir = templates_dir
        self.output_dir = output_dir
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_acceptance_act(self, work_order_id: int, data: Dict[str, Any]) -> str:
        """
        Генерация акта сдачи-приемки выполненных работ
        
        Args:
            work_order_id: ID заказа
            data: Дополнительные данные для акта
        
        Returns:
            Путь к сгенерированному документу
        """
        # Получить данные заказа
        order = db.execute_query("SELECT * FROM work_orders WHERE id = ?", (work_order_id,))[0]
        contract = db.execute_query("SELECT * FROM contracts WHERE id = ?", (order['contract_id'],))[0]
        
        # Создать документ
        doc = Document()
        
        # Заголовок
        heading = doc.add_heading('АКТ', 0)
        heading.alignment = 1  # Центрирование
        
        doc.add_paragraph(f'сдачи-приемки выполненных работ')
        doc.add_paragraph(f'№ {data.get("act_number", "")} от {data.get("act_date", datetime.now().strftime("%d.%m.%Y"))}')
        doc.add_paragraph('')
        
        # Основная информация
        doc.add_paragraph(f'По контракту: {contract["contract_number"]}')
        doc.add_paragraph(f'Заказчик: {contract["customer"]}')
        doc.add_paragraph(f'Заказ № {order["order_number"]}')
        doc.add_paragraph('')
        
        # Описание работ
        doc.add_heading('1. Выполненные работы:', level=2)
        doc.add_paragraph(f'Устройство: {order["device_name"]}')
        doc.add_paragraph(f'Описание работ: {order.get("description", "")}')
        doc.add_paragraph('')
        
        # Стоимость
        doc.add_heading('2. Стоимость выполненных работ:', level=2)
        doc.add_paragraph(f'Общая стоимость: {order.get("actual_cost", 0)} руб.')
        doc.add_paragraph('')
        
        # Использованные материалы
        doc.add_heading('3. Использованные материалы:', level=2)
        components = db.execute_query("""
            SELECT c.component_name, c.component_code, oc.required_quantity, c.unit_of_measure
            FROM order_components oc
            JOIN components c ON oc.component_id = c.id
            WHERE oc.work_order_id = ?
        """, (work_order_id,))
        
        if components:
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Light Grid Accent 1'
            
            # Заголовки таблицы
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Код'
            hdr_cells[1].text = 'Наименование'
            hdr_cells[2].text = 'Количество'
            hdr_cells[3].text = 'Ед. изм.'
            
            # Данные
            for comp in components:
                row_cells = table.add_row().cells
                row_cells[0].text = comp['component_code']
                row_cells[1].text = comp['component_name']
                row_cells[2].text = str(comp['required_quantity'])
                row_cells[3].text = comp['unit_of_measure']
        
        doc.add_paragraph('')
        
        # Заключение
        doc.add_heading('4. Заключение:', level=2)
        doc.add_paragraph('Работы выполнены в полном объеме, в соответствии с требованиями технического задания.')
        doc.add_paragraph('Качество выполненных работ соответствует установленным стандартам.')
        doc.add_paragraph('')
        doc.add_paragraph('')
        
        # Подписи
        doc.add_paragraph('_' * 50)
        doc.add_paragraph(f'Представитель заказчика: _________________ ({data.get("customer_representative", "")})')
        doc.add_paragraph('')
        doc.add_paragraph('_' * 50)
        doc.add_paragraph(f'Представитель исполнителя: _________________ ({data.get("executor_representative", "")})')
        
        # Сохранить
        filename = f'act_acceptance_{order["order_number"]}_{datetime.now().strftime("%Y%m%d")}.docx'
        filepath = os.path.join(self.output_dir, filename)
        doc.save(filepath)
        
        # Зарегистрировать в БД
        db.execute_insert("""
            INSERT INTO documents 
            (document_type, contract_id, work_order_id, title, file_path, created_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'act_acceptance',
            order['contract_id'],
            work_order_id,
            f'Акт сдачи-приемки работ по заказу {order["order_number"]}',
            filepath,
            datetime.now().strftime("%Y-%m-%d"),
            'draft'
        ))
        
        return filepath
    
    def generate_military_certificate(self, work_order_id: int, data: Dict[str, Any]) -> str:
        """
        Генерация удостоверения военпреда
        """
        order = db.execute_query("SELECT * FROM work_orders WHERE id = ?", (work_order_id,))[0]
        contract = db.execute_query("SELECT * FROM contracts WHERE id = ?", (order['contract_id'],))[0]
        
        doc = Document()
        
        # Заголовок
        heading = doc.add_heading('УДОСТОВЕРЕНИЕ', 0)
        heading.alignment = 1
        
        doc.add_paragraph(f'№ {data.get("certificate_number", "")}')
        doc.add_paragraph(f'от {data.get("certificate_date", datetime.now().strftime("%d.%m.%Y"))}')
        doc.add_paragraph('')
        
        # Основная часть
        doc.add_paragraph(f'Настоящим удостоверяется, что по контракту {contract["contract_number"]}')
        doc.add_paragraph(f'заказчик: {contract["customer"]}')
        doc.add_paragraph('')
        doc.add_paragraph(f'выполнены работы по заказу № {order["order_number"]}:')
        doc.add_paragraph(f'{order["device_name"]}')
        doc.add_paragraph('')
        doc.add_paragraph('Работы выполнены в соответствии с техническим заданием.')
        doc.add_paragraph('Качество работ соответствует требованиям.')
        doc.add_paragraph('')
        doc.add_paragraph('')
        
        # Подпись
        doc.add_paragraph('_' * 50)
        doc.add_paragraph(f'Военный представитель: _________________ ({data.get("military_rep", "")})')
        doc.add_paragraph('')
        doc.add_paragraph('М.П.')
        
        # Сохранить
        filename = f'certificate_{order["order_number"]}_{datetime.now().strftime("%Y%m%d")}.docx'
        filepath = os.path.join(self.output_dir, filename)
        doc.save(filepath)
        
        db.execute_insert("""
            INSERT INTO documents 
            (document_type, contract_id, work_order_id, title, file_path, created_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'military_certificate',
            order['contract_id'],
            work_order_id,
            f'Удостоверение военпреда по заказу {order["order_number"]}',
            filepath,
            datetime.now().strftime("%Y-%m-%d"),
            'draft'
        ))
        
        return filepath
    
    def generate_payment_request_letter(self, contract_id: int, data: Dict[str, Any]) -> str:
        """
        Генерация письма-требования доплаты
        """
        contract = db.execute_query("SELECT * FROM contracts WHERE id = ?", (contract_id,))[0]
        
        # Рассчитать баланс
        payments = db.execute_query("SELECT * FROM payments WHERE contract_id = ?", (contract_id,))
        total_paid = sum(p['amount'] for p in payments if p['status'] == 'completed')
        total_spent = db.execute_query(
            "SELECT SUM(actual_cost) as total FROM work_orders WHERE contract_id = ? AND actual_cost IS NOT NULL",
            (contract_id,)
        )[0]['total'] or 0
        
        deficit = total_spent - total_paid
        
        doc = Document()
        
        # Шапка письма
        doc.add_paragraph(f'{data.get("our_company", "Наша организация")}')
        doc.add_paragraph(f'{data.get("our_address", "")}')
        doc.add_paragraph('')
        doc.add_paragraph(f'{contract["customer"]}')
        doc.add_paragraph('')
        doc.add_paragraph(f'от {datetime.now().strftime("%d.%m.%Y")}')
        doc.add_paragraph('')
        
        # Заголовок
        doc.add_heading('О необходимости дополнительного финансирования', level=1)
        doc.add_paragraph('')
        
        # Текст письма
        doc.add_paragraph(f'Уважаемые коллеги!')
        doc.add_paragraph('')
        doc.add_paragraph(
            f'В рамках выполнения контракта № {contract["contract_number"]} '
            f'от {contract["start_date"]} возникла необходимость в дополнительном финансировании.'
        )
        doc.add_paragraph('')
        doc.add_paragraph('Анализ текущего состояния показывает:')
        doc.add_paragraph(f'- Общая сумма контракта: {contract["total_amount"]} руб.')
        doc.add_paragraph(f'- Получено оплат: {total_paid} руб.')
        doc.add_paragraph(f'- Фактические затраты: {total_spent} руб.')
        doc.add_paragraph(f'- Дефицит средств: {deficit} руб.')
        doc.add_paragraph('')
        doc.add_paragraph(
            f'Для продолжения выполнения работ в установленные сроки просим '
            f'произвести доплату в размере {data.get("requested_amount", deficit)} руб.'
        )
        doc.add_paragraph('')
        doc.add_paragraph('С уважением,')
        doc.add_paragraph('')
        doc.add_paragraph('_' * 50)
        doc.add_paragraph(f'{data.get("signatory", "")}')
        
        # Сохранить
        filename = f'payment_request_{contract["contract_number"]}_{datetime.now().strftime("%Y%m%d")}.docx'
        filepath = os.path.join(self.output_dir, filename)
        doc.save(filepath)
        
        db.execute_insert("""
            INSERT INTO documents 
            (document_type, contract_id, title, file_path, created_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'payment_request',
            contract_id,
            f'Письмо о доплате по контракту {contract["contract_number"]}',
            filepath,
            datetime.now().strftime("%Y-%m-%d"),
            'draft'
        ))
        
        return filepath
    
    def generate_defect_report_based_order(self, defect_report_id: int) -> Dict[str, Any]:
        """
        На основе акта дефектации создать заявку на материалы
        """
        defect_report = db.execute_query(
            "SELECT * FROM defect_reports WHERE id = ?",
            (defect_report_id,)
        )[0]
        
        # Здесь должна быть логика парсинга акта дефектации
        # и извлечения необходимых материалов
        
        return {
            'work_order_id': defect_report['work_order_id'],
            'required_components': [],  # Список требуемых компонентов
            'message': 'Заявка на материалы создана на основе акта дефектации'
        }


# Создание экземпляра генератора
doc_generator = DocumentGenerator()
