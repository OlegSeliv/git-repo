from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os

class DocumentGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_styles()
    
    def setup_styles(self):
        # Попытаемся загрузить русский шрифт
        try:
            # Можно добавить TTF шрифт для поддержки кириллицы
            pass
        except:
            pass
        
        # Создаем кастомные стили
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # CENTER
        )
        
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.darkblue
        )

class ActTemplate(DocumentGenerator):
    """Шаблон акта выполненных работ"""
    
    def generate_act(self, contract, order, work_items, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Заголовок
        title = Paragraph("АКТ ВЫПОЛНЕННЫХ РАБОТ", self.title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Информация о договоре
        contract_info = f"""
        Договор: {contract.contract_number}<br/>
        Заказчик: {contract.customer}<br/>
        Исполнитель: ООО "Ваша компания"<br/>
        Дата составления: {datetime.now().strftime('%d.%m.%Y')}
        """
        story.append(Paragraph(contract_info, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Информация о заказе
        order_header = Paragraph("Информация о заказе:", self.header_style)
        story.append(order_header)
        
        order_info = f"""
        Номер заказа: {order.order_number}<br/>
        Описание: {order.description or 'Не указано'}<br/>
        Местоположение: {order.location or 'Не указано'}<br/>
        Тип устройства: {order.device_type or 'Не указано'}<br/>
        Серийный номер: {order.device_serial or 'Не указано'}
        """
        story.append(Paragraph(order_info, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Таблица выполненных работ
        work_header = Paragraph("Выполненные работы:", self.header_style)
        story.append(work_header)
        
        # Создаем таблицу работ
        data = [['№', 'Наименование работ', 'Ед. изм.', 'Кол-во', 'Цена', 'Сумма']]
        
        total_amount = 0
        for i, item in enumerate(work_items, 1):
            amount = item.get('quantity', 0) * item.get('price', 0)
            total_amount += amount
            data.append([
                str(i),
                item.get('name', ''),
                item.get('unit', 'шт.'),
                str(item.get('quantity', 0)),
                f"{item.get('price', 0):,.2f} ₽",
                f"{amount:,.2f} ₽"
            ])
        
        # Строка итого
        data.append(['', 'ИТОГО:', '', '', '', f"{total_amount:,.2f} ₽"])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Подписи
        signatures = """
        Заказчик: _________________ / _________________ /        Дата: __________<br/><br/>
        Исполнитель: _________________ / _________________ /     Дата: __________
        """
        story.append(Paragraph(signatures, self.styles['Normal']))
        
        doc.build(story)
        return output_path

class CertificateTemplate(DocumentGenerator):
    """Шаблон удостоверения военного представителя"""
    
    def generate_certificate(self, act_data, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Заголовок
        title = Paragraph("УДОСТОВЕРЕНИЕ ВОЕННОГО ПРЕДСТАВИТЕЛЯ", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Номер и дата
        cert_info = f"""
        № {act_data.get('certificate_number', '_______')}<br/>
        от {act_data.get('certificate_date', datetime.now().strftime('%d.%m.%Y'))}
        """
        story.append(Paragraph(cert_info, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Основной текст
        main_text = f"""
        На основании акта выполненных работ № {act_data.get('act_number', '_______')} 
        от {act_data.get('act_date', datetime.now().strftime('%d.%m.%Y'))} 
        удостоверяю качественное выполнение работ по договору № {act_data.get('contract_number', '_______')}.
        """
        story.append(Paragraph(main_text, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Подпись военпреда
        signature = """
        Военный представитель: _________________ / _________________ /<br/><br/>
        Дата: __________<br/>
        М.П.
        """
        story.append(Paragraph(signature, self.styles['Normal']))
        
        doc.build(story)
        return output_path

class AcceptanceActTemplate(DocumentGenerator):
    """Шаблон акта сдачи-приемки выполненных работ"""
    
    def generate_acceptance_act(self, contract, order, certificate_data, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Заголовок
        title = Paragraph("АКТ СДАЧИ-ПРИЕМКИ ВЫПОЛНЕННЫХ РАБОТ", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Основная информация
        main_info = f"""
        Договор: {contract.contract_number}<br/>
        Заказчик: {contract.customer}<br/>
        Исполнитель: ООО "Ваша компания"<br/>
        Дата составления: {datetime.now().strftime('%d.%m.%Y')}<br/><br/>
        
        На основании удостоверения военного представителя 
        № {certificate_data.get('certificate_number', '_______')} 
        от {certificate_data.get('certificate_date', datetime.now().strftime('%d.%m.%Y'))} 
        настоящим актом подтверждается сдача-приемка выполненных работ.
        """
        story.append(Paragraph(main_info, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Сумма к доплате
        if order.actual_cost:
            amount_info = f"""
            Общая стоимость выполненных работ: {order.actual_cost:,.2f} ₽<br/>
            К доплате: {order.actual_cost - (contract.advance_amount or 0):,.2f} ₽
            """
            story.append(Paragraph(amount_info, self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Подписи
        signatures = """
        Заказчик: _________________ / _________________ /        Дата: __________<br/><br/>
        Исполнитель: _________________ / _________________ /     Дата: __________<br/><br/>
        М.П.                                                   М.П.
        """
        story.append(Paragraph(signatures, self.styles['Normal']))
        
        doc.build(story)
        return output_path

class TravelOrderTemplate(DocumentGenerator):
    """Шаблон служебного задания на командировку"""
    
    def generate_travel_order(self, employee, business_trip, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Заголовок
        title = Paragraph("СЛУЖЕБНОЕ ЗАДАНИЕ", self.title_style)
        story.append(title)
        
        subtitle = Paragraph("для направления в служебную командировку", self.styles['Normal'])
        story.append(subtitle)
        story.append(Spacer(1, 30))
        
        # Информация о сотруднике
        employee_info = f"""
        ФИО: {employee.full_name}<br/>
        Должность: {employee.position or 'Не указано'}<br/>
        Подразделение: {employee.department or 'Не указано'}<br/>
        Табельный номер: {employee.employee_number or 'Не указано'}
        """
        story.append(Paragraph(employee_info, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Информация о командировке
        trip_info = f"""
        Пункт назначения: {business_trip.destination}<br/>
        Срок командировки: с {business_trip.start_date.strftime('%d.%m.%Y')} 
        по {business_trip.end_date.strftime('%d.%m.%Y')}<br/>
        Цель командировки: {business_trip.purpose or 'Выполнение сервисных работ'}<br/>
        Основание: Заказ № {business_trip.order.order_number if business_trip.order else 'Не указано'}
        """
        story.append(Paragraph(trip_info, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Подписи
        signatures = """
        Руководитель: _________________ / _________________ /    Дата: __________<br/><br/>
        С заданием ознакомлен:<br/>
        Сотрудник: _________________ / {employee.full_name} /    Дата: __________
        """.format(employee=employee)
        story.append(Paragraph(signatures, self.styles['Normal']))
        
        doc.build(story)
        return output_path

# Система автозаполнения документов
class DocumentAutoFill:
    def __init__(self, db_session):
        self.db = db_session
        
    def create_work_completion_act(self, order_id, work_items):
        """Создает акт выполненных работ"""
        from app import Order, Contract
        
        order = self.db.query(Order).get(order_id)
        if not order:
            raise ValueError("Заказ не найден")
        
        contract = order.contract
        
        # Генерируем имя файла
        filename = f"act_work_{order.order_number}_{datetime.now().strftime('%Y%m%d')}.pdf"
        output_path = os.path.join('documents', filename)
        
        # Создаем документ
        template = ActTemplate()
        template.generate_act(contract, order, work_items, output_path)
        
        # Сохраняем в БД
        from app import Document
        doc = Document(
            document_type='work_act',
            document_number=f"АКТ-{order.order_number}-{datetime.now().strftime('%Y%m%d')}",
            title=f"Акт выполненных работ по заказу {order.order_number}",
            file_path=output_path,
            contract_id=contract.id,
            order_id=order.id,
            created_date=datetime.now().date(),
            status='signed'
        )
        
        self.db.add(doc)
        self.db.commit()
        
        return doc
    
    def create_certificate(self, act_document_id, certificate_number):
        """Создает удостоверение военпреда на основе акта работ"""
        from app import Document
        
        act_doc = self.db.query(Document).get(act_document_id)
        if not act_doc:
            raise ValueError("Акт работ не найден")
        
        act_data = {
            'certificate_number': certificate_number,
            'certificate_date': datetime.now().strftime('%d.%m.%Y'),
            'act_number': act_doc.document_number,
            'act_date': act_doc.created_date.strftime('%d.%m.%Y'),
            'contract_number': act_doc.contract.contract_number
        }
        
        # Генерируем имя файла
        filename = f"certificate_{certificate_number}_{datetime.now().strftime('%Y%m%d')}.pdf"
        output_path = os.path.join('documents', filename)
        
        # Создаем документ
        template = CertificateTemplate()
        template.generate_certificate(act_data, output_path)
        
        # Сохраняем в БД
        doc = Document(
            document_type='military_certificate',
            document_number=certificate_number,
            title=f"Удостоверение военпреда {certificate_number}",
            file_path=output_path,
            contract_id=act_doc.contract_id,
            order_id=act_doc.order_id,
            created_date=datetime.now().date(),
            status='signed'
        )
        
        self.db.add(doc)
        self.db.commit()
        
        return doc
    
    def create_acceptance_act(self, certificate_document_id):
        """Создает акт сдачи-приемки на основе удостоверения военпреда"""
        from app import Document
        
        cert_doc = self.db.query(Document).get(certificate_document_id)
        if not cert_doc:
            raise ValueError("Удостоверение не найдено")
        
        contract = cert_doc.contract
        order = cert_doc.order
        
        certificate_data = {
            'certificate_number': cert_doc.document_number,
            'certificate_date': cert_doc.created_date.strftime('%d.%m.%Y')
        }
        
        # Генерируем имя файла
        filename = f"acceptance_act_{order.order_number}_{datetime.now().strftime('%Y%m%d')}.pdf"
        output_path = os.path.join('documents', filename)
        
        # Создаем документ
        template = AcceptanceActTemplate()
        template.generate_acceptance_act(contract, order, certificate_data, output_path)
        
        # Сохраняем в БД
        doc = Document(
            document_type='acceptance_act',
            document_number=f"ПРИЕМ-{order.order_number}-{datetime.now().strftime('%Y%m%d')}",
            title=f"Акт сдачи-приемки по заказу {order.order_number}",
            file_path=output_path,
            contract_id=contract.id,
            order_id=order.id,
            created_date=datetime.now().date(),
            status='signed'
        )
        
        self.db.add(doc)
        self.db.commit()
        
        return doc
    
    def create_travel_order(self, business_trip_id):
        """Создает служебное задание на командировку"""
        from app import BusinessTrip
        
        trip = self.db.query(BusinessTrip).get(business_trip_id)
        if not trip:
            raise ValueError("Командировка не найдена")
        
        employee = trip.employee
        
        # Генерируем имя файла
        filename = f"travel_order_{employee.employee_number}_{trip.start_date.strftime('%Y%m%d')}.pdf"
        output_path = os.path.join('documents', filename)
        
        # Создаем документ
        template = TravelOrderTemplate()
        template.generate_travel_order(employee, trip, output_path)
        
        # Сохраняем в БД
        from app import Document
        doc = Document(
            document_type='travel_order',
            document_number=f"КМ-{employee.employee_number}-{trip.start_date.strftime('%Y%m%d')}",
            title=f"Командировочное удостоверение {employee.full_name}",
            file_path=output_path,
            business_trip_id=trip.id,
            created_date=datetime.now().date(),
            status='signed'
        )
        
        self.db.add(doc)
        self.db.commit()
        
        return doc