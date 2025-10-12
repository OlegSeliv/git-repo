# Windows Desktop Application для системы управления контрактами
# Используем tkinter для нативного интерфейса Windows

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter.scrolledtext import ScrolledText
import sqlite3
import requests
import json
from datetime import datetime, timedelta
import threading
from PIL import Image, ImageTk
import os
import webbrowser

class ContractManagerWindows:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Система управления сервисными контрактами")
        self.root.geometry("1200x800")
        self.root.state('zoomed')  # Максимизировать окно
        
        # Настройка стилей
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Переменные
        self.server_url = tk.StringVar(value="http://localhost:5000")
        self.username = tk.StringVar()
        self.current_user = None
        self.auto_refresh = tk.BooleanVar(value=True)
        
        # Создаем БД для локального кеширования
        self.init_local_db()
        
        # Создаем интерфейс
        self.create_main_interface()
        
        # Запуск автообновления
        self.auto_refresh_data()
    
    def init_local_db(self):
        """Инициализация локальной БД для кеширования"""
        self.local_db = sqlite3.connect('local_cache.db', check_same_thread=False)
        cursor = self.local_db.cursor()
        
        # Таблица для кеширования данных
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_data (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp REAL
            )
        ''')
        
        # Таблица для настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        self.local_db.commit()
    
    def create_main_interface(self):
        """Создание основного интерфейса"""
        # Главное меню
        self.create_menu()
        
        # Панель инструментов
        self.create_toolbar()
        
        # Основной фрейм с вкладками
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладки
        self.create_dashboard_tab()
        self.create_contracts_tab()
        self.create_orders_tab()
        self.create_materials_tab()
        self.create_trips_tab()
        self.create_documents_tab()
        self.create_analytics_tab()
        
        # Строка состояния
        self.create_status_bar()
        
        # Проверяем авторизацию при запуске
        self.check_saved_credentials()
    
    def create_menu(self):
        """Создание главного меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Подключиться к серверу", command=self.connect_to_server)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт данных", command=self.export_data)
        file_menu.add_command(label="Импорт данных", command=self.import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        # Меню "Документы"
        docs_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Документы", menu=docs_menu)
        docs_menu.add_command(label="Сканировать документ", command=self.scan_document)
        docs_menu.add_command(label="Создать акт работ", command=self.create_work_act)
        docs_menu.add_command(label="Создать удостоверение", command=self.create_certificate)
        
        # Меню "Отчеты"
        reports_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Отчеты", menu=reports_menu)
        reports_menu.add_command(label="Финансовый отчет", command=self.financial_report)
        reports_menu.add_command(label="Отчет по материалам", command=self.materials_report)
        reports_menu.add_command(label="Отчет по командировкам", command=self.trips_report)
        
        # Меню "Настройки"
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Настройки", menu=settings_menu)
        settings_menu.add_command(label="Настройки приложения", command=self.app_settings)
        settings_menu.add_command(label="Настройки сервера", command=self.server_settings)
        
        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="Руководство пользователя", command=self.show_help)
        help_menu.add_command(label="О программе", command=self.show_about)
    
    def create_toolbar(self):
        """Создание панели инструментов"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        # Кнопки быстрого доступа
        ttk.Button(toolbar, text="Обновить", command=self.refresh_all_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Новый контракт", command=self.new_contract).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Новый заказ", command=self.new_order).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Статус подключения
        self.connection_label = ttk.Label(toolbar, text="Не подключен", foreground="red")
        self.connection_label.pack(side=tk.RIGHT, padx=5)
        
        # Автообновление
        ttk.Checkbutton(toolbar, text="Автообновление", 
                       variable=self.auto_refresh).pack(side=tk.RIGHT, padx=5)
    
    def create_dashboard_tab(self):
        """Создание вкладки дашборда"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Дашборд")
        
        # Статистические карточки
        stats_frame = ttk.LabelFrame(dashboard_frame, text="Статистика")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Создаем сетку для статистики
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Карточки статистики
        self.stats_widgets = {}
        
        stats_data = [
            ("contracts", "Активные контракты", "blue"),
            ("urgent_orders", "Срочные заказы", "orange"),
            ("active_trips", "Командировки", "green"),
            ("material_deficit", "Дефицит материалов", "red")
        ]
        
        for i, (key, label, color) in enumerate(stats_data):
            frame = ttk.LabelFrame(stats_grid, text=label)
            frame.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            
            value_label = ttk.Label(frame, text="0", font=("Arial", 24, "bold"))
            value_label.pack(pady=10)
            
            self.stats_widgets[key] = value_label
        
        # Настройка весов колонок
        for i in range(4):
            stats_grid.columnconfigure(i, weight=1)
        
        # Область уведомлений
        notif_frame = ttk.LabelFrame(dashboard_frame, text="Уведомления")
        notif_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.notifications_tree = ttk.Treeview(notif_frame, 
                                             columns=("type", "message", "date"),
                                             show="headings", height=10)
        
        self.notifications_tree.heading("type", text="Тип")
        self.notifications_tree.heading("message", text="Сообщение")
        self.notifications_tree.heading("date", text="Дата")
        
        self.notifications_tree.column("type", width=100)
        self.notifications_tree.column("message", width=400)
        self.notifications_tree.column("date", width=150)
        
        # Скроллбар для уведомлений
        notif_scrollbar = ttk.Scrollbar(notif_frame, orient=tk.VERTICAL, 
                                       command=self.notifications_tree.yview)
        self.notifications_tree.configure(yscrollcommand=notif_scrollbar.set)
        
        self.notifications_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notif_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_contracts_tab(self):
        """Создание вкладки контрактов"""
        contracts_frame = ttk.Frame(self.notebook)
        self.notebook.add(contracts_frame, text="Контракты")
        
        # Панель поиска и фильтров
        search_frame = ttk.Frame(contracts_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=5)
        self.contracts_search = ttk.Entry(search_frame, width=30)
        self.contracts_search.pack(side=tk.LEFT, padx=5)
        self.contracts_search.bind('<KeyRelease>', self.filter_contracts)
        
        ttk.Button(search_frame, text="Новый контракт", 
                  command=self.new_contract).pack(side=tk.RIGHT, padx=5)
        
        # Таблица контрактов
        contracts_list_frame = ttk.Frame(contracts_frame)
        contracts_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.contracts_tree = ttk.Treeview(contracts_list_frame, 
                                         columns=("number", "name", "customer", "amount", "status"),
                                         show="headings")
        
        self.contracts_tree.heading("number", text="Номер")
        self.contracts_tree.heading("name", text="Название")
        self.contracts_tree.heading("customer", text="Заказчик")
        self.contracts_tree.heading("amount", text="Сумма")
        self.contracts_tree.heading("status", text="Статус")
        
        # Ширина колонок
        self.contracts_tree.column("number", width=120)
        self.contracts_tree.column("name", width=300)
        self.contracts_tree.column("customer", width=200)
        self.contracts_tree.column("amount", width=120)
        self.contracts_tree.column("status", width=100)
        
        # Скроллбары
        contracts_v_scrollbar = ttk.Scrollbar(contracts_list_frame, orient=tk.VERTICAL, 
                                            command=self.contracts_tree.yview)
        contracts_h_scrollbar = ttk.Scrollbar(contracts_list_frame, orient=tk.HORIZONTAL, 
                                            command=self.contracts_tree.xview)
        
        self.contracts_tree.configure(yscrollcommand=contracts_v_scrollbar.set,
                                    xscrollcommand=contracts_h_scrollbar.set)
        
        # Размещение элементов
        self.contracts_tree.grid(row=0, column=0, sticky="nsew")
        contracts_v_scrollbar.grid(row=0, column=1, sticky="ns")
        contracts_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        contracts_list_frame.rowconfigure(0, weight=1)
        contracts_list_frame.columnconfigure(0, weight=1)
        
        # Контекстное меню для контрактов
        self.contracts_context_menu = tk.Menu(self.root, tearoff=0)
        self.contracts_context_menu.add_command(label="Просмотр заказов", 
                                               command=self.view_contract_orders)
        self.contracts_context_menu.add_command(label="Проверить баланс", 
                                               command=self.check_contract_balance)
        self.contracts_context_menu.add_separator()
        self.contracts_context_menu.add_command(label="Редактировать", 
                                               command=self.edit_contract)
        
        self.contracts_tree.bind("<Button-3>", self.show_contracts_context_menu)
        self.contracts_tree.bind("<Double-1>", self.view_contract_details)
    
    def create_orders_tab(self):
        """Создание вкладки заказов"""
        orders_frame = ttk.Frame(self.notebook)
        self.notebook.add(orders_frame, text="Заказы")
        
        # Панель фильтров
        filter_frame = ttk.LabelFrame(orders_frame, text="Фильтры")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        filter_grid = ttk.Frame(filter_frame)
        filter_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Фильтр по контракту
        ttk.Label(filter_grid, text="Контракт:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.order_contract_filter = ttk.Combobox(filter_grid, width=20)
        self.order_contract_filter.grid(row=0, column=1, padx=5, pady=2)
        
        # Фильтр по статусу
        ttk.Label(filter_grid, text="Статус:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        self.order_status_filter = ttk.Combobox(filter_grid, 
                                               values=["Все", "created", "in_progress", "completed"],
                                               width=15)
        self.order_status_filter.set("Все")
        self.order_status_filter.grid(row=0, column=3, padx=5, pady=2)
        
        # Фильтр по приоритету
        ttk.Label(filter_grid, text="Приоритет:").grid(row=0, column=4, padx=5, pady=2, sticky=tk.W)
        self.order_priority_filter = ttk.Combobox(filter_grid, 
                                                 values=["Все", "low", "normal", "high", "urgent"],
                                                 width=15)
        self.order_priority_filter.set("Все")
        self.order_priority_filter.grid(row=0, column=5, padx=5, pady=2)
        
        # Кнопки
        ttk.Button(filter_grid, text="Применить фильтры", 
                  command=self.apply_order_filters).grid(row=1, column=0, columnspan=3, pady=5)
        
        ttk.Button(filter_grid, text="Новый заказ", 
                  command=self.new_order).grid(row=1, column=3, columnspan=3, pady=5)
        
        # Таблица заказов
        orders_list_frame = ttk.Frame(orders_frame)
        orders_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.orders_tree = ttk.Treeview(orders_list_frame, 
                                       columns=("number", "description", "location", "status", 
                                               "priority", "start_date", "end_date"),
                                       show="headings")
        
        # Заголовки
        headers = [
            ("number", "Номер", 100),
            ("description", "Описание", 200),
            ("location", "Место", 150),
            ("status", "Статус", 100),
            ("priority", "Приоритет", 80),
            ("start_date", "Начало", 100),
            ("end_date", "Окончание", 100)
        ]
        
        for col, text, width in headers:
            self.orders_tree.heading(col, text=text)
            self.orders_tree.column(col, width=width)
        
        # Скроллбары
        orders_v_scrollbar = ttk.Scrollbar(orders_list_frame, orient=tk.VERTICAL, 
                                          command=self.orders_tree.yview)
        orders_h_scrollbar = ttk.Scrollbar(orders_list_frame, orient=tk.HORIZONTAL, 
                                          command=self.orders_tree.xview)
        
        self.orders_tree.configure(yscrollcommand=orders_v_scrollbar.set,
                                  xscrollcommand=orders_h_scrollbar.set)
        
        # Размещение
        self.orders_tree.grid(row=0, column=0, sticky="nsew")
        orders_v_scrollbar.grid(row=0, column=1, sticky="ns")
        orders_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        orders_list_frame.rowconfigure(0, weight=1)
        orders_list_frame.columnconfigure(0, weight=1)
        
        # Контекстное меню для заказов
        self.orders_context_menu = tk.Menu(self.root, tearoff=0)
        self.orders_context_menu.add_command(label="Начать выполнение", 
                                            command=self.start_order)
        self.orders_context_menu.add_command(label="Материалы", 
                                            command=self.view_order_materials)
        self.orders_context_menu.add_command(label="Командировка", 
                                            command=self.plan_business_trip)
        self.orders_context_menu.add_separator()
        self.orders_context_menu.add_command(label="Создать акт работ", 
                                            command=self.create_work_act)
        
        self.orders_tree.bind("<Button-3>", self.show_orders_context_menu)
        
        # Цветовое кодирование строк по приоритету
        self.orders_tree.tag_configure("urgent", background="#ffcccc")
        self.orders_tree.tag_configure("high", background="#ffffcc")
        self.orders_tree.tag_configure("completed", background="#ccffcc")
    
    def create_materials_tab(self):
        """Создание вкладки материалов"""
        materials_frame = ttk.Frame(self.notebook)
        self.notebook.add(materials_frame, text="Материалы")
        
        # Панель поиска
        search_frame = ttk.Frame(materials_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Поиск по артикулу/названию:").pack(side=tk.LEFT, padx=5)
        self.materials_search = ttk.Entry(search_frame, width=30)
        self.materials_search.pack(side=tk.LEFT, padx=5)
        self.materials_search.bind('<KeyRelease>', self.filter_materials)
        
        ttk.Button(search_frame, text="Добавить материал", 
                  command=self.add_material).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(search_frame, text="Показать дефицит", 
                  command=self.show_material_deficit).pack(side=tk.RIGHT, padx=5)
        
        # Таблица материалов
        materials_list_frame = ttk.Frame(materials_frame)
        materials_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.materials_tree = ttk.Treeview(materials_list_frame, 
                                         columns=("part_number", "name", "current_stock", 
                                                 "min_stock", "price", "supplier"),
                                         show="headings")
        
        # Заголовки
        headers = [
            ("part_number", "Артикул", 120),
            ("name", "Наименование", 300),
            ("current_stock", "На складе", 80),
            ("min_stock", "Минимум", 80),
            ("price", "Цена", 100),
            ("supplier", "Поставщик", 200)
        ]
        
        for col, text, width in headers:
            self.materials_tree.heading(col, text=text)
            self.materials_tree.column(col, width=width)
        
        # Скроллбары
        materials_v_scrollbar = ttk.Scrollbar(materials_list_frame, orient=tk.VERTICAL, 
                                            command=self.materials_tree.yview)
        self.materials_tree.configure(yscrollcommand=materials_v_scrollbar.set)
        
        self.materials_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        materials_v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Цветовое кодирование для дефицита
        self.materials_tree.tag_configure("deficit", background="#ffcccc")
        self.materials_tree.tag_configure("low_stock", background="#ffffcc")
    
    def create_trips_tab(self):
        """Создание вкладки командировок"""
        trips_frame = ttk.Frame(self.notebook)
        self.notebook.add(trips_frame, text="Командировки")
        
        # Панель управления
        control_frame = ttk.Frame(trips_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="Новая командировка", 
                  command=self.new_business_trip).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Календарь командировок", 
                  command=self.show_trips_calendar).pack(side=tk.LEFT, padx=5)
        
        # Фильтр по статусу
        ttk.Label(control_frame, text="Статус:").pack(side=tk.RIGHT, padx=5)
        self.trips_status_filter = ttk.Combobox(control_frame, 
                                              values=["Все", "planned", "in_progress", "completed"],
                                              width=15)
        self.trips_status_filter.set("Все")
        self.trips_status_filter.pack(side=tk.RIGHT, padx=5)
        
        # Таблица командировок
        trips_list_frame = ttk.Frame(trips_frame)
        trips_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.trips_tree = ttk.Treeview(trips_list_frame, 
                                     columns=("employee", "destination", "start_date", 
                                             "end_date", "status", "purpose"),
                                     show="headings")
        
        # Заголовки
        headers = [
            ("employee", "Сотрудник", 150),
            ("destination", "Направление", 200),
            ("start_date", "Начало", 100),
            ("end_date", "Окончание", 100),
            ("status", "Статус", 100),
            ("purpose", "Цель", 250)
        ]
        
        for col, text, width in headers:
            self.trips_tree.heading(col, text=text)
            self.trips_tree.column(col, width=width)
        
        # Скроллбар
        trips_scrollbar = ttk.Scrollbar(trips_list_frame, orient=tk.VERTICAL, 
                                       command=self.trips_tree.yview)
        self.trips_tree.configure(yscrollcommand=trips_scrollbar.set)
        
        self.trips_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        trips_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Контекстное меню
        self.trips_context_menu = tk.Menu(self.root, tearoff=0)
        self.trips_context_menu.add_command(label="Продлить командировку", 
                                           command=self.extend_trip)
        self.trips_context_menu.add_command(label="Создать служебку", 
                                           command=self.create_travel_order)
        
        self.trips_tree.bind("<Button-3>", self.show_trips_context_menu)
    
    def create_documents_tab(self):
        """Создание вкладки документов"""
        documents_frame = ttk.Frame(self.notebook)
        self.notebook.add(documents_frame, text="Документы")
        
        # Разделяем на две панели - дерево папок и список документов
        paned = ttk.PanedWindow(documents_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Левая панель - дерево папок
        tree_frame = ttk.LabelFrame(paned, text="Структура документов")
        paned.add(tree_frame, weight=1)
        
        self.docs_tree = ttk.Treeview(tree_frame, show="tree")
        self.docs_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Правая панель - список документов
        docs_list_frame = ttk.LabelFrame(paned, text="Документы")
        paned.add(docs_list_frame, weight=3)
        
        # Панель управления документами
        docs_control_frame = ttk.Frame(docs_list_frame)
        docs_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(docs_control_frame, text="Сканировать", 
                  command=self.scan_document).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(docs_control_frame, text="Добавить файл", 
                  command=self.add_document).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(docs_control_frame, text="Создать акт", 
                  command=self.create_work_act).pack(side=tk.LEFT, padx=2)
        
        # Список документов
        self.documents_list = ttk.Treeview(docs_list_frame, 
                                         columns=("name", "type", "date", "status"),
                                         show="headings")
        
        headers = [
            ("name", "Название", 300),
            ("type", "Тип", 150),
            ("date", "Дата", 100),
            ("status", "Статус", 100)
        ]
        
        for col, text, width in headers:
            self.documents_list.heading(col, text=text)
            self.documents_list.column(col, width=width)
        
        self.documents_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Инициализируем структуру папок
        self.init_document_tree()
    
    def create_analytics_tab(self):
        """Создание вкладки аналитики"""
        analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(analytics_frame, text="Аналитика")
        
        # Панель выбора отчетов
        reports_frame = ttk.LabelFrame(analytics_frame, text="Отчеты")
        reports_frame.pack(fill=tk.X, padx=10, pady=5)
        
        reports_grid = ttk.Frame(reports_frame)
        reports_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Кнопки отчетов
        reports = [
            ("Финансовый отчет", self.financial_report),
            ("Отчет по контрактам", self.contracts_report),
            ("Отчет по материалам", self.materials_report),
            ("Отчет по командировкам", self.trips_report)
        ]
        
        for i, (name, command) in enumerate(reports):
            row, col = divmod(i, 2)
            ttk.Button(reports_grid, text=name, command=command, width=25).grid(
                row=row, column=col, padx=5, pady=5)
        
        # Область для отображения отчетов
        self.analytics_text = ScrolledText(analytics_frame, height=25)
        self.analytics_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_text = ttk.Label(self.status_bar, text="Готов")
        self.status_text.pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(self.status_bar, length=200, mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
    
    def init_document_tree(self):
        """Инициализация дерева документов"""
        folders = [
            "Контракты",
            "Заказы", 
            "Акты работ",
            "Удостоверения",
            "Командировки",
            "Протоколы совещаний",
            "Переписка"
        ]
        
        for folder in folders:
            self.docs_tree.insert("", tk.END, text=folder, open=True)
    
    def connect_to_server(self):
        """Подключение к серверу"""
        dialog = ServerConnectionDialog(self.root, self.server_url.get())
        if dialog.result:
            self.server_url.set(dialog.result['server'])
            self.username.set(dialog.result['username'])
            
            # Попытка подключения
            if self.test_connection():
                self.connection_label.config(text="Подключен", foreground="green")
                self.refresh_all_data()
            else:
                self.connection_label.config(text="Ошибка подключения", foreground="red")
                messagebox.showerror("Ошибка", "Не удалось подключиться к серверу")
    
    def test_connection(self):
        """Тест подключения к серверу"""
        try:
            response = requests.get(f"{self.server_url.get()}/api/ping", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def refresh_all_data(self):
        """Обновление всех данных"""
        if not self.test_connection():
            return
        
        self.status_text.config(text="Обновление данных...")
        self.progress_bar.start()
        
        # Запускаем обновление в отдельном потоке
        thread = threading.Thread(target=self._refresh_data_thread)
        thread.daemon = True
        thread.start()
    
    def _refresh_data_thread(self):
        """Обновление данных в отдельном потоке"""
        try:
            # Обновляем статистику дашборда
            self.load_dashboard_stats()
            
            # Обновляем контракты
            self.load_contracts()
            
            # Обновляем заказы
            self.load_orders()
            
            # Обновляем материалы
            self.load_materials()
            
            # Обновляем командировки
            self.load_business_trips()
            
            # Обновляем документы
            self.load_documents()
            
            # Обновляем интерфейс в главном потоке
            self.root.after(0, self._update_ui_after_refresh)
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"Ошибка обновления: {str(e)}"))
    
    def _update_ui_after_refresh(self):
        """Обновление интерфейса после загрузки данных"""
        self.progress_bar.stop()
        self.status_text.config(text=f"Обновлено: {datetime.now().strftime('%H:%M:%S')}")
    
    def load_dashboard_stats(self):
        """Загрузка статистики для дашборда"""
        try:
            response = requests.get(f"{self.server_url.get()}/api/dashboard_stats")
            if response.status_code == 200:
                stats = response.json()
                
                # Обновляем в главном потоке
                self.root.after(0, lambda: self.update_stats_widgets(stats))
        except Exception as e:
            print(f"Ошибка загрузки статистики: {e}")
    
    def update_stats_widgets(self, stats):
        """Обновление виджетов статистики"""
        for key, widget in self.stats_widgets.items():
            value = stats.get(key, 0)
            widget.config(text=str(value))
    
    def auto_refresh_data(self):
        """Автоматическое обновление данных"""
        if self.auto_refresh.get() and self.test_connection():
            self.refresh_all_data()
        
        # Планируем следующее обновление через 60 секунд
        self.root.after(60000, self.auto_refresh_data)
    
    def load_contracts(self):
        """Загрузка контрактов"""
        try:
            response = requests.get(f"{self.server_url.get()}/api/contracts")
            if response.status_code == 200:
                contracts = response.json()
                self.root.after(0, lambda: self.populate_contracts_tree(contracts))
        except Exception as e:
            print(f"Ошибка загрузки контрактов: {e}")
    
    def populate_contracts_tree(self, contracts):
        """Заполнение таблицы контрактов"""
        # Очищаем таблицу
        for item in self.contracts_tree.get_children():
            self.contracts_tree.delete(item)
        
        # Добавляем контракты
        for contract in contracts:
            self.contracts_tree.insert("", tk.END, values=(
                contract.get('contract_number', ''),
                contract.get('contract_name', '')[:50],
                contract.get('customer', ''),
                f"{contract.get('total_amount', 0):,.0f} ₽" if contract.get('total_amount') else '',
                contract.get('status', '')
            ), tags=(contract.get('id'),))
    
    def show_error(self, message):
        """Показать сообщение об ошибке"""
        messagebox.showerror("Ошибка", message)
    
    def new_contract(self):
        """Создание нового контракта"""
        dialog = ContractDialog(self.root)
        if dialog.result:
            # Отправляем данные на сервер
            try:
                response = requests.post(f"{self.server_url.get()}/api/contracts", 
                                       json=dialog.result)
                if response.status_code == 201:
                    messagebox.showinfo("Успех", "Контракт создан успешно")
                    self.load_contracts()
                else:
                    messagebox.showerror("Ошибка", "Не удалось создать контракт")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка сети: {str(e)}")
    
    def check_saved_credentials(self):
        """Проверка сохраненных учетных данных"""
        cursor = self.local_db.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'server_url'")
        result = cursor.fetchone()
        if result:
            self.server_url.set(result[0])
        
        cursor.execute("SELECT value FROM settings WHERE key = 'username'")
        result = cursor.fetchone()
        if result:
            self.username.set(result[0])
    
    def run(self):
        """Запуск приложения"""
        # Устанавливаем иконку окна (если есть)
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        self.root.mainloop()

# Диалоговые окна
class ServerConnectionDialog:
    def __init__(self, parent, default_server=""):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Подключение к серверу")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрируем окно
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Создаем форму
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Поля ввода
        ttk.Label(main_frame, text="Адрес сервера:").pack(anchor=tk.W)
        self.server_entry = ttk.Entry(main_frame, width=40)
        self.server_entry.pack(fill=tk.X, pady=5)
        self.server_entry.insert(0, default_server)
        
        ttk.Label(main_frame, text="Имя пользователя:").pack(anchor=tk.W, pady=(10,0))
        self.username_entry = ttk.Entry(main_frame, width=40)
        self.username_entry.pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Пароль:").pack(anchor=tk.W, pady=(10,0))
        self.password_entry = ttk.Entry(main_frame, show="*", width=40)
        self.password_entry.pack(fill=tk.X, pady=5)
        
        # Кнопки
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20,0))
        
        ttk.Button(buttons_frame, text="Подключиться", 
                  command=self.connect).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", 
                  command=self.cancel).pack(side=tk.RIGHT)
        
        # Фокус на первое поле
        self.server_entry.focus()
        
        # Обработка Enter
        self.dialog.bind('<Return>', lambda e: self.connect())
        
        # Ждем закрытия диалога
        self.dialog.wait_window()
    
    def connect(self):
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not server or not username or not password:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return
        
        self.result = {
            'server': server,
            'username': username,
            'password': password
        }
        
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()

class ContractDialog:
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Новый контракт")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрируем окно
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Создаем форму
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Поля формы
        self.create_form_fields(main_frame)
        
        # Кнопки
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20,0))
        
        ttk.Button(buttons_frame, text="Создать", 
                  command=self.create_contract).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", 
                  command=self.cancel).pack(side=tk.RIGHT)
        
        # Ждем закрытия диалога
        self.dialog.wait_window()
    
    def create_form_fields(self, parent):
        """Создание полей формы"""
        fields = [
            ("contract_number", "Номер контракта:"),
            ("contract_name", "Название контракта:"),
            ("customer", "Заказчик:"),
            ("start_date", "Дата начала:"),
            ("end_date", "Дата окончания:"),
            ("total_amount", "Общая сумма:"),
            ("advance_amount", "Аванс:")
        ]
        
        self.entries = {}
        
        for field_name, label_text in fields:
            ttk.Label(parent, text=label_text).pack(anchor=tk.W, pady=(10,0))
            
            if field_name in ['start_date', 'end_date']:
                entry = ttk.Entry(parent, width=50)
                entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            else:
                entry = ttk.Entry(parent, width=50)
            
            entry.pack(fill=tk.X, pady=2)
            self.entries[field_name] = entry
    
    def create_contract(self):
        data = {}
        for field_name, entry in self.entries.items():
            data[field_name] = entry.get().strip()
        
        # Валидация
        if not data['contract_number'] or not data['contract_name'] or not data['customer']:
            messagebox.showwarning("Внимание", "Заполните обязательные поля")
            return
        
        self.result = data
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()

if __name__ == "__main__":
    app = ContractManagerWindows()
    app.run()