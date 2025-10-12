# Система аналитики и отчетности
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime, timedelta
import sqlite3
import io
import base64
from decimal import Decimal
import numpy as np

class AnalyticsEngine:
    def __init__(self, db_connection):
        self.db = db_connection
        plt.style.use('seaborn-v0_8')
        plt.rcParams['font.size'] = 10
        plt.rcParams['figure.figsize'] = (12, 8)
        
        # Настройка для русского языка
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    
    def get_contract_analytics(self, date_from=None, date_to=None):
        """Аналитика по контрактам"""
        query = """
        SELECT 
            c.id,
            c.contract_number,
            c.contract_name,
            c.customer,
            c.total_amount,
            c.advance_amount,
            c.status,
            c.start_date,
            c.end_date,
            cs.balance,
            cs.available_amount,
            cs.reserved_amount,
            COUNT(o.id) as total_orders,
            COUNT(CASE WHEN o.status = 'completed' THEN 1 END) as completed_orders,
            COUNT(CASE WHEN o.status = 'in_progress' THEN 1 END) as active_orders,
            SUM(CASE WHEN p.status = 'received' THEN p.amount ELSE 0 END) as received_payments,
            SUM(CASE WHEN p.status = 'pending' THEN p.amount ELSE 0 END) as pending_payments
        FROM contracts c
        LEFT JOIN contract_subaccounts cs ON c.id = cs.contract_id
        LEFT JOIN orders o ON c.id = o.contract_id
        LEFT JOIN payments p ON c.id = p.contract_id
        """
        
        params = []
        
        if date_from:
            query += " AND c.start_date >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND c.start_date <= ?"
            params.append(date_to)
        
        query += " GROUP BY c.id ORDER BY c.start_date DESC"
        
        df = pd.read_sql_query(query, self.db, params=params)
        
        # Вычисляем дополнительные метрики
        df['completion_rate'] = (df['completed_orders'] / df['total_orders'] * 100).fillna(0)
        df['payment_rate'] = (df['received_payments'] / df['total_amount'] * 100).fillna(0)
        df['remaining_amount'] = df['total_amount'] - df['received_payments']
        
        return df
    
    def get_financial_summary(self, period='month'):
        """Финансовая сводка"""
        if period == 'month':
            date_format = '%Y-%m'
        elif period == 'quarter':
            date_format = '%Y-Q%q'
        else:
            date_format = '%Y'
        
        query = f"""
        SELECT 
            strftime('{date_format}', p.payment_date) as period,
            p.payment_type,
            SUM(p.amount) as total_amount,
            COUNT(*) as payment_count,
            AVG(p.amount) as avg_amount
        FROM payments p
        WHERE p.status = 'received' AND p.payment_date IS NOT NULL
        GROUP BY strftime('{date_format}', p.payment_date), p.payment_type
        ORDER BY period DESC
        """
        
        df = pd.read_sql_query(query, self.db)
        return df
    
    def get_orders_analytics(self, date_from=None, date_to=None):
        """Аналитика по заказам"""
        query = """
        SELECT 
            o.*,
            c.contract_number,
            c.customer,
            CASE 
                WHEN o.actual_end_date IS NOT NULL AND o.planned_end_date IS NOT NULL 
                THEN julianday(o.actual_end_date) - julianday(o.planned_end_date)
                ELSE NULL 
            END as schedule_deviation,
            CASE 
                WHEN o.actual_cost IS NOT NULL AND o.estimated_cost IS NOT NULL 
                THEN (o.actual_cost - o.estimated_cost) / o.estimated_cost * 100
                ELSE NULL 
            END as cost_deviation
        FROM orders o
        JOIN contracts c ON o.contract_id = c.id
        """
        
        params = []
        
        if date_from:
            query += " WHERE o.created_at >= ?"
            params.append(date_from)
        
        if date_to:
            condition = " AND " if date_from else " WHERE "
            query += f"{condition} o.created_at <= ?"
            params.append(date_to)
        
        query += " ORDER BY o.created_at DESC"
        
        df = pd.read_sql_query(query, self.db, params=params)
        return df
    
    def get_materials_analytics(self):
        """Аналитика по материалам"""
        query = """
        SELECT 
            m.*,
            CASE 
                WHEN m.current_stock <= 0 THEN 'out_of_stock'
                WHEN m.current_stock <= m.min_stock THEN 'low_stock'
                ELSE 'in_stock'
            END as stock_status,
            SUM(om.required_quantity) as total_required,
            SUM(om.allocated_quantity) as total_allocated,
            COUNT(DISTINCT om.order_id) as orders_count
        FROM materials m
        LEFT JOIN order_materials om ON m.id = om.material_id
        GROUP BY m.id
        ORDER BY m.current_stock / NULLIF(m.min_stock, 0) ASC
        """
        
        df = pd.read_sql_query(query, self.db)
        return df
    
    def get_business_trips_analytics(self, date_from=None, date_to=None):
        """Аналитика по командировкам"""
        query = """
        SELECT 
            bt.*,
            e.full_name as employee_name,
            e.department,
            o.order_number,
            c.contract_number,
            julianday(bt.end_date) - julianday(bt.start_date) + 1 as duration_days,
            CASE 
                WHEN bt.extension_date IS NOT NULL 
                THEN julianday(bt.extension_date) - julianday(bt.end_date)
                ELSE 0 
            END as extension_days
        FROM business_trips bt
        JOIN employees e ON bt.employee_id = e.id
        LEFT JOIN orders o ON bt.order_id = o.id
        LEFT JOIN contracts c ON o.contract_id = c.id
        """
        
        params = []
        
        if date_from:
            query += " WHERE bt.start_date >= ?"
            params.append(date_from)
        
        if date_to:
            condition = " AND " if date_from else " WHERE "
            query += f"{condition} bt.start_date <= ?"
            params.append(date_to)
        
        query += " ORDER BY bt.start_date DESC"
        
        df = pd.read_sql_query(query, self.db)
        return df
    
    def create_contract_performance_chart(self, contracts_df):
        """График производительности контрактов"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Статус контрактов
        status_counts = contracts_df['status'].value_counts()
        ax1.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%')
        ax1.set_title('Распределение статусов контрактов')
        
        # 2. Процент выполнения по контрактам
        top_contracts = contracts_df.nlargest(10, 'total_amount')
        ax2.barh(top_contracts['contract_number'], top_contracts['completion_rate'])
        ax2.set_xlabel('Процент выполнения (%)')
        ax2.set_title('Процент выполнения топ-10 контрактов')
        ax2.grid(True, alpha=0.3)
        
        # 3. Суммы контрактов vs полученные платежи
        ax3.scatter(contracts_df['total_amount'], contracts_df['received_payments'], 
                   alpha=0.6, s=50)
        ax3.plot([0, contracts_df['total_amount'].max()], 
                [0, contracts_df['total_amount'].max()], 'r--', alpha=0.5)
        ax3.set_xlabel('Общая сумма контракта')
        ax3.set_ylabel('Полученные платежи')
        ax3.set_title('Контрактная сумма vs Полученные платежи')
        ax3.grid(True, alpha=0.3)
        
        # 4. Баланс по контрактам
        balance_data = contracts_df[contracts_df['balance'].notna()]
        ax4.bar(range(len(balance_data)), balance_data['balance'])
        ax4.set_xlabel('Контракты')
        ax4.set_ylabel('Баланс')
        ax4.set_title('Баланс по контрактам')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Сохраняем в буфер
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        
        # Конвертируем в base64 для веб-отображения
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def create_financial_trends_chart(self, financial_df):
        """График финансовых трендов"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Группируем по периодам и типам платежей
        pivot_data = financial_df.pivot_table(
            index='period', 
            columns='payment_type', 
            values='total_amount', 
            fill_value=0
        )
        
        # 1. Динамика поступлений по типам
        pivot_data.plot(kind='bar', stacked=True, ax=ax1)
        ax1.set_title('Динамика поступлений по типам платежей')
        ax1.set_ylabel('Сумма')
        ax1.legend(title='Тип платежа')
        ax1.grid(True, alpha=0.3)
        
        # 2. Общая динамика
        total_by_period = financial_df.groupby('period')['total_amount'].sum()
        ax2.plot(total_by_period.index, total_by_period.values, marker='o', linewidth=2)
        ax2.fill_between(total_by_period.index, total_by_period.values, alpha=0.3)
        ax2.set_title('Общая динамика поступлений')
        ax2.set_ylabel('Общая сумма')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Сохраняем в буфер
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def create_orders_analysis_chart(self, orders_df):
        """Анализ заказов"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Распределение статусов заказов
        status_counts = orders_df['status'].value_counts()
        colors_map = {'created': '#FFA07A', 'in_progress': '#98FB98', 
                     'completed': '#87CEEB', 'cancelled': '#F0E68C'}
        colors_list = [colors_map.get(status, '#D3D3D3') for status in status_counts.index]
        
        ax1.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
                colors=colors_list)
        ax1.set_title('Распределение статусов заказов')
        
        # 2. Распределение приоритетов
        priority_counts = orders_df['priority'].value_counts()
        ax2.bar(priority_counts.index, priority_counts.values, 
                color=['red' if p == 'urgent' else 'orange' if p == 'high' 
                       else 'yellow' if p == 'normal' else 'green' for p in priority_counts.index])
        ax2.set_title('Распределение приоритетов заказов')
        ax2.set_ylabel('Количество')
        ax2.grid(True, alpha=0.3)
        
        # 3. Отклонения по срокам (только завершенные заказы)
        completed_orders = orders_df[orders_df['schedule_deviation'].notna()]
        if len(completed_orders) > 0:
            ax3.hist(completed_orders['schedule_deviation'], bins=20, alpha=0.7, 
                    color='skyblue', edgecolor='black')
            ax3.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='План')
            ax3.set_xlabel('Отклонение от плана (дни)')
            ax3.set_ylabel('Количество заказов')
            ax3.set_title('Отклонения по срокам выполнения')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # 4. Отклонения по стоимости
        cost_deviation_orders = orders_df[orders_df['cost_deviation'].notna()]
        if len(cost_deviation_orders) > 0:
            ax4.hist(cost_deviation_orders['cost_deviation'], bins=20, alpha=0.7, 
                    color='lightcoral', edgecolor='black')
            ax4.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='План')
            ax4.set_xlabel('Отклонение от плана (%)')
            ax4.set_ylabel('Количество заказов')
            ax4.set_title('Отклонения по стоимости')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def create_materials_dashboard_chart(self, materials_df):
        """Дашборд по материалам"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Статус складских запасов
        stock_status_counts = materials_df['stock_status'].value_counts()
        colors_map = {'out_of_stock': '#FF4444', 'low_stock': '#FFA500', 'in_stock': '#32CD32'}
        colors_list = [colors_map.get(status, '#D3D3D3') for status in stock_status_counts.index]
        
        ax1.pie(stock_status_counts.values, labels=stock_status_counts.index, 
                autopct='%1.1f%%', colors=colors_list)
        ax1.set_title('Статус складских запасов')
        
        # 2. Топ материалов с дефицитом
        deficit_materials = materials_df[materials_df['stock_status'] != 'in_stock']
        if len(deficit_materials) > 0:
            top_deficit = deficit_materials.nsmallest(10, 'current_stock')
            ax2.barh(range(len(top_deficit)), top_deficit['current_stock'], 
                    color='red', alpha=0.7)
            ax2.set_yticks(range(len(top_deficit)))
            ax2.set_yticklabels(top_deficit['name'].str[:20])
            ax2.set_xlabel('Количество на складе')
            ax2.set_title('Топ-10 материалов с дефицитом')
            ax2.grid(True, alpha=0.3)
        
        # 3. Стоимость запасов
        materials_with_price = materials_df[materials_df['price'].notna()]
        if len(materials_with_price) > 0:
            materials_with_price['stock_value'] = materials_with_price['current_stock'] * materials_with_price['price']
            top_value = materials_with_price.nlargest(10, 'stock_value')
            
            ax3.bar(range(len(top_value)), top_value['stock_value'])
            ax3.set_xticks(range(len(top_value)))
            ax3.set_xticklabels(top_value['name'].str[:10], rotation=45)
            ax3.set_ylabel('Стоимость запасов')
            ax3.set_title('Топ-10 по стоимости запасов')
            ax3.grid(True, alpha=0.3)
        
        # 4. Востребованность материалов
        popular_materials = materials_df[materials_df['orders_count'] > 0]
        if len(popular_materials) > 0:
            top_popular = popular_materials.nlargest(10, 'orders_count')
            ax4.bar(range(len(top_popular)), top_popular['orders_count'], color='green', alpha=0.7)
            ax4.set_xticks(range(len(top_popular)))
            ax4.set_xticklabels(top_popular['name'].str[:10], rotation=45)
            ax4.set_ylabel('Количество заказов')
            ax4.set_title('Топ-10 востребованных материалов')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def create_trips_analytics_chart(self, trips_df):
        """Анализ командировок"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Статусы командировок
        status_counts = trips_df['status'].value_counts()
        ax1.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%')
        ax1.set_title('Статусы командировок')
        
        # 2. Продолжительность командировок
        ax2.hist(trips_df['duration_days'], bins=15, alpha=0.7, color='lightblue', edgecolor='black')
        ax2.set_xlabel('Продолжительность (дни)')
        ax2.set_ylabel('Количество командировок')
        ax2.set_title('Распределение продолжительности командировок')
        ax2.grid(True, alpha=0.3)
        
        # 3. Активность по сотрудникам
        employee_trips = trips_df['employee_name'].value_counts()
        if len(employee_trips) > 10:
            employee_trips = employee_trips.head(10)
        
        ax3.barh(range(len(employee_trips)), employee_trips.values)
        ax3.set_yticks(range(len(employee_trips)))
        ax3.set_yticklabels(employee_trips.index)
        ax3.set_xlabel('Количество командировок')
        ax3.set_title('Активность сотрудников')
        ax3.grid(True, alpha=0.3)
        
        # 4. Динамика по месяцам
        trips_df['start_month'] = pd.to_datetime(trips_df['start_date']).dt.to_period('M')
        monthly_trips = trips_df['start_month'].value_counts().sort_index()
        
        ax4.plot(monthly_trips.index.astype(str), monthly_trips.values, marker='o', linewidth=2)
        ax4.fill_between(range(len(monthly_trips)), monthly_trips.values, alpha=0.3)
        ax4.set_xlabel('Месяц')
        ax4.set_ylabel('Количество командировок')
        ax4.set_title('Динамика командировок по месяцам')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64

class ReportGenerator:
    def __init__(self, analytics_engine):
        self.analytics = analytics_engine
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Настройка кастомных стилей для отчетов"""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # CENTER
            textColor=colors.darkblue
        )
        
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            textColor=colors.darkgreen
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12
        )
    
    def generate_executive_summary_report(self, output_path, date_from=None, date_to=None):
        """Генерация исполнительного отчета"""
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Заголовок
        title = Paragraph("ИСПОЛНИТЕЛЬНЫЙ ОТЧЕТ", self.title_style)
        story.append(title)
        
        period_text = f"Период: {date_from or 'начало'} - {date_to or datetime.now().strftime('%Y-%m-%d')}"
        story.append(Paragraph(period_text, self.normal_style))
        story.append(Spacer(1, 20))
        
        # Получаем данные
        contracts_df = self.analytics.get_contract_analytics(date_from, date_to)
        orders_df = self.analytics.get_orders_analytics(date_from, date_to)
        materials_df = self.analytics.get_materials_analytics()
        trips_df = self.analytics.get_business_trips_analytics(date_from, date_to)
        
        # Основные показатели
        story.append(Paragraph("1. ОСНОВНЫЕ ПОКАЗАТЕЛИ", self.subtitle_style))
        
        metrics_data = [
            ['Показатель', 'Значение'],
            ['Общее количество контрактов', str(len(contracts_df))],
            ['Активные контракты', str(len(contracts_df[contracts_df['status'] == 'active']))],
            ['Общая сумма контрактов', f"{contracts_df['total_amount'].sum():,.0f} ₽"],
            ['Получено платежей', f"{contracts_df['received_payments'].sum():,.0f} ₽"],
            ['Общее количество заказов', str(len(orders_df))],
            ['Завершенные заказы', str(len(orders_df[orders_df['status'] == 'completed']))],
            ['Активные командировки', str(len(trips_df[trips_df['status'].isin(['planned', 'in_progress'])]))],
            ['Материалов с дефицитом', str(len(materials_df[materials_df['stock_status'] != 'in_stock']))]
        ]
        
        metrics_table = Table(metrics_data)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metrics_table)
        story.append(Spacer(1, 20))
        
        # Финансовые показатели
        story.append(Paragraph("2. ФИНАНСОВЫЕ ПОКАЗАТЕЛИ", self.subtitle_style))
        
        total_contract_sum = contracts_df['total_amount'].sum()
        received_payments = contracts_df['received_payments'].sum()
        payment_rate = (received_payments / total_contract_sum * 100) if total_contract_sum > 0 else 0
        
        financial_text = f"""
        Общая сумма контрактов: {total_contract_sum:,.0f} ₽<br/>
        Получено платежей: {received_payments:,.0f} ₽<br/>
        Процент оплаты: {payment_rate:.1f}%<br/>
        Остаток к получению: {total_contract_sum - received_payments:,.0f} ₽
        """
        
        story.append(Paragraph(financial_text, self.normal_style))
        story.append(Spacer(1, 20))
        
        # Проблемные области
        story.append(Paragraph("3. ПРОБЛЕМНЫЕ ОБЛАСТИ", self.subtitle_style))
        
        problems = []
        
        # Просроченные заказы
        overdue_orders = orders_df[
            (orders_df['planned_end_date'].notna()) & 
            (orders_df['status'] != 'completed') & 
            (pd.to_datetime(orders_df['planned_end_date']) < datetime.now())
        ]
        
        if len(overdue_orders) > 0:
            problems.append(f"• Просроченные заказы: {len(overdue_orders)}")
        
        # Дефицит материалов
        deficit_materials = materials_df[materials_df['stock_status'] != 'in_stock']
        if len(deficit_materials) > 0:
            problems.append(f"• Материалы с дефицитом: {len(deficit_materials)}")
        
        # Контракты с низким процентом оплаты
        low_payment_contracts = contracts_df[contracts_df['payment_rate'] < 50]
        if len(low_payment_contracts) > 0:
            problems.append(f"• Контракты с низким процентом оплаты: {len(low_payment_contracts)}")
        
        if problems:
            problems_text = "<br/>".join(problems)
            story.append(Paragraph(problems_text, self.normal_style))
        else:
            story.append(Paragraph("Критических проблем не выявлено.", self.normal_style))
        
        story.append(Spacer(1, 20))
        
        # Рекомендации
        story.append(Paragraph("4. РЕКОМЕНДАЦИИ", self.subtitle_style))
        
        recommendations = [
            "• Усилить контроль за выполнением сроков заказов",
            "• Провести инвентаризацию склада и пополнить запасы дефицитных материалов",
            "• Активизировать работу с заказчиками по ускорению платежей",
            "• Рассмотреть возможность оптимизации процессов выполнения заказов"
        ]
        
        recommendations_text = "<br/>".join(recommendations)
        story.append(Paragraph(recommendations_text, self.normal_style))
        
        # Подпись
        story.append(Spacer(1, 40))
        signature_text = f"""
        Отчет сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}<br/>
        Менеджер проекта: _________________ / _________________ /
        """
        story.append(Paragraph(signature_text, self.normal_style))
        
        doc.build(story)
        return output_path
    
    def generate_detailed_contract_report(self, contract_id, output_path):
        """Детальный отчет по контракту"""
        # Получаем данные по конкретному контракту
        query = """
        SELECT c.*, cs.balance, cs.available_amount, cs.reserved_amount
        FROM contracts c
        LEFT JOIN contract_subaccounts cs ON c.id = cs.contract_id
        WHERE c.id = ?
        """
        
        contract_data = pd.read_sql_query(query, self.analytics.db, params=[contract_id])
        
        if contract_data.empty:
            return None
        
        contract = contract_data.iloc[0]
        
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Заголовок
        title = Paragraph(f"ДЕТАЛЬНЫЙ ОТЧЕТ ПО КОНТРАКТУ {contract['contract_number']}", self.title_style)
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Основная информация о контракте
        story.append(Paragraph("ИНФОРМАЦИЯ О КОНТРАКТЕ", self.subtitle_style))
        
        contract_info_data = [
            ['Параметр', 'Значение'],
            ['Номер контракта', contract['contract_number']],
            ['Название', contract['contract_name']],
            ['Заказчик', contract['customer']],
            ['Дата начала', contract['start_date']],
            ['Дата окончания', contract['end_date'] or 'Не указана'],
            ['Общая сумма', f"{contract['total_amount']:,.0f} ₽" if contract['total_amount'] else 'Не указана'],
            ['Сумма аванса', f"{contract['advance_amount']:,.0f} ₽" if contract['advance_amount'] else 'Не указана'],
            ['Статус', contract['status']],
            ['Текущий баланс', f"{contract['balance']:,.0f} ₽" if contract['balance'] else '0 ₽']
        ]
        
        contract_info_table = Table(contract_info_data)
        contract_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(contract_info_table)
        story.append(Spacer(1, 30))
        
        # Заказы по контракту
        orders_query = """
        SELECT * FROM orders WHERE contract_id = ? ORDER BY created_at DESC
        """
        orders_data = pd.read_sql_query(orders_query, self.analytics.db, params=[contract_id])
        
        if not orders_data.empty:
            story.append(Paragraph("ЗАКАЗЫ ПО КОНТРАКТУ", self.subtitle_style))
            
            orders_table_data = [['Номер', 'Описание', 'Статус', 'Приоритет', 'Сумма']]
            
            for _, order in orders_data.iterrows():
                orders_table_data.append([
                    order['order_number'],
                    (order['description'] or '')[:30] + '...' if order['description'] and len(order['description']) > 30 else (order['description'] or ''),
                    order['status'],
                    order['priority'],
                    f"{order['actual_cost']:,.0f} ₽" if order['actual_cost'] else f"{order['estimated_cost']:,.0f} ₽" if order['estimated_cost'] else 'Не указана'
                ])
            
            orders_table = Table(orders_table_data)
            orders_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(orders_table)
            story.append(Spacer(1, 30))
        
        # Платежи по контракту
        payments_query = """
        SELECT * FROM payments WHERE contract_id = ? ORDER BY payment_date DESC
        """
        payments_data = pd.read_sql_query(payments_query, self.analytics.db, params=[contract_id])
        
        if not payments_data.empty:
            story.append(Paragraph("ПЛАТЕЖИ ПО КОНТРАКТУ", self.subtitle_style))
            
            payments_table_data = [['Тип', 'Сумма', 'Дата', 'Статус', 'Документ']]
            
            for _, payment in payments_data.iterrows():
                payments_table_data.append([
                    payment['payment_type'],
                    f"{payment['amount']:,.0f} ₽",
                    payment['payment_date'] or 'Не указана',
                    payment['status'],
                    payment['payment_document'] or 'Не указан'
                ])
            
            payments_table = Table(payments_table_data)
            payments_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(payments_table)
        
        doc.build(story)
        return output_path
    
    def export_data_to_excel(self, output_path, include_charts=True):
        """Экспорт всех данных в Excel с диаграммами"""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # Получаем все данные
            contracts_df = self.analytics.get_contract_analytics()
            orders_df = self.analytics.get_orders_analytics()
            materials_df = self.analytics.get_materials_analytics()
            trips_df = self.analytics.get_business_trips_analytics()
            financial_df = self.analytics.get_financial_summary()
            
            # Экспортируем в отдельные листы
            contracts_df.to_excel(writer, sheet_name='Контракты', index=False)
            orders_df.to_excel(writer, sheet_name='Заказы', index=False)
            materials_df.to_excel(writer, sheet_name='Материалы', index=False)
            trips_df.to_excel(writer, sheet_name='Командировки', index=False)
            financial_df.to_excel(writer, sheet_name='Финансы', index=False)
            
            # Создаем сводный лист
            summary_data = {
                'Показатель': [
                    'Всего контрактов',
                    'Активные контракты',
                    'Общая сумма контрактов',
                    'Получено платежей',
                    'Всего заказов',
                    'Завершенные заказы',
                    'Материалов с дефицитом',
                    'Активные командировки'
                ],
                'Значение': [
                    len(contracts_df),
                    len(contracts_df[contracts_df['status'] == 'active']),
                    f"{contracts_df['total_amount'].sum():,.0f} ₽",
                    f"{contracts_df['received_payments'].sum():,.0f} ₽",
                    len(orders_df),
                    len(orders_df[orders_df['status'] == 'completed']),
                    len(materials_df[materials_df['stock_status'] != 'in_stock']),
                    len(trips_df[trips_df['status'].isin(['planned', 'in_progress'])])
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Сводка', index=False)
        
        return output_path