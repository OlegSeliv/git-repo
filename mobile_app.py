# Мобильное приложение для Android - Менеджер контрактов
# Используем Kivy для кроссплатформенной разработки

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
import requests
import json
from datetime import datetime, timedelta

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Заголовок
        title = Label(text='Система управления контрактами', 
                     font_size=24, size_hint_y=None, height=50)
        layout.add_widget(title)
        
        # Форма входа
        form_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=120)
        
        form_layout.add_widget(Label(text='Логин:', size_hint_x=0.3))
        self.username_input = TextInput(multiline=False)
        form_layout.add_widget(self.username_input)
        
        form_layout.add_widget(Label(text='Пароль:', size_hint_x=0.3))
        self.password_input = TextInput(password=True, multiline=False)
        form_layout.add_widget(self.password_input)
        
        layout.add_widget(form_layout)
        
        # Кнопка входа
        login_btn = Button(text='Войти', size_hint_y=None, height=50)
        login_btn.bind(on_press=self.login)
        layout.add_widget(login_btn)
        
        # Настройки сервера
        server_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=40)
        server_layout.add_widget(Label(text='Сервер:', size_hint_x=0.3))
        self.server_input = TextInput(text='http://localhost:5000', multiline=False)
        server_layout.add_widget(self.server_input)
        layout.add_widget(server_layout)
        
        self.add_widget(layout)
    
    def login(self, instance):
        username = self.username_input.text
        password = self.password_input.text
        server_url = self.server_input.text
        
        try:
            # Попытка авторизации
            response = requests.post(f"{server_url}/api/login", 
                                   json={'username': username, 'password': password})
            
            if response.status_code == 200:
                # Сохраняем данные авторизации
                store = JsonStore('user_data.json')
                store.put('auth', 
                         username=username, 
                         server_url=server_url,
                         token=response.json().get('token'))
                
                # Переходим к главному экрану
                self.manager.current = 'dashboard'
            else:
                self.show_error('Неверные учетные данные')
        
        except Exception as e:
            self.show_error(f'Ошибка подключения: {str(e)}')
    
    def show_error(self, message):
        popup = Popup(title='Ошибка', content=Label(text=message),
                     size_hint=(0.8, 0.3))
        popup.open()

class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
        Clock.schedule_interval(self.update_data, 30)  # Обновляем каждые 30 секунд
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Заголовок
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        header.add_widget(Label(text='Дашборд', font_size=20))
        
        refresh_btn = Button(text='Обновить', size_hint_x=None, width=100)
        refresh_btn.bind(on_press=self.update_data)
        header.add_widget(refresh_btn)
        
        layout.add_widget(header)
        
        # Статистика
        self.stats_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=200)
        layout.add_widget(self.stats_layout)
        
        # Кнопки навигации
        nav_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=150)
        
        contracts_btn = Button(text='Контракты')
        contracts_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'contracts'))
        nav_layout.add_widget(contracts_btn)
        
        orders_btn = Button(text='Заказы')
        orders_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'orders'))
        nav_layout.add_widget(orders_btn)
        
        trips_btn = Button(text='Командировки')
        trips_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'trips'))
        nav_layout.add_widget(trips_btn)
        
        materials_btn = Button(text='Материалы')
        materials_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'materials'))
        nav_layout.add_widget(materials_btn)
        
        layout.add_widget(nav_layout)
        
        # Последние уведомления
        notifications_label = Label(text='Последние уведомления:', 
                                   size_hint_y=None, height=30)
        layout.add_widget(notifications_label)
        
        scroll = ScrollView()
        self.notifications_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.notifications_layout.bind(minimum_height=self.notifications_layout.setter('height'))
        scroll.add_widget(self.notifications_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        # Загружаем данные при запуске
        Clock.schedule_once(self.update_data, 0.1)
    
    def update_data(self, dt=None):
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            # Получаем статистику
            response = requests.get(f"{server_url}/api/dashboard_stats")
            if response.status_code == 200:
                data = response.json()
                self.update_stats(data)
                self.update_notifications(data.get('notifications', []))
        
        except Exception as e:
            print(f"Ошибка обновления данных: {e}")
    
    def update_stats(self, data):
        self.stats_layout.clear_widgets()
        
        # Активные контракты
        contracts_widget = BoxLayout(orientation='vertical')
        contracts_widget.add_widget(Label(text=str(data.get('active_contracts', 0)), font_size=24))
        contracts_widget.add_widget(Label(text='Активные контракты'))
        self.stats_layout.add_widget(contracts_widget)
        
        # Срочные заказы
        urgent_widget = BoxLayout(orientation='vertical')
        urgent_widget.add_widget(Label(text=str(data.get('urgent_orders', 0)), font_size=24))
        urgent_widget.add_widget(Label(text='Срочные заказы'))
        self.stats_layout.add_widget(urgent_widget)
        
        # Командировки
        trips_widget = BoxLayout(orientation='vertical')
        trips_widget.add_widget(Label(text=str(data.get('active_trips', 0)), font_size=24))
        trips_widget.add_widget(Label(text='Командировки'))
        self.stats_layout.add_widget(trips_widget)
        
        # Дефицит материалов
        deficit_widget = BoxLayout(orientation='vertical')
        deficit_widget.add_widget(Label(text=str(data.get('material_deficit', 0)), font_size=24))
        deficit_widget.add_widget(Label(text='Дефицит'))
        self.stats_layout.add_widget(deficit_widget)
    
    def update_notifications(self, notifications):
        self.notifications_layout.clear_widgets()
        
        for notif in notifications[:10]:  # Показываем только последние 10
            notif_widget = BoxLayout(orientation='vertical', size_hint_y=None, height=60)
            notif_widget.add_widget(Label(text=notif.get('title', ''), font_size=14))
            notif_widget.add_widget(Label(text=notif.get('message', ''), font_size=12))
            self.notifications_layout.add_widget(notif_widget)

class ContractsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Заголовок
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        header.add_widget(Label(text='Контракты', font_size=20))
        
        back_btn = Button(text='Назад', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'dashboard'))
        header.add_widget(back_btn)
        
        layout.add_widget(header)
        
        # Список контрактов
        scroll = ScrollView()
        self.contracts_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.contracts_layout.bind(minimum_height=self.contracts_layout.setter('height'))
        scroll.add_widget(self.contracts_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        # Загружаем контракты
        Clock.schedule_once(self.load_contracts, 0.1)
    
    def load_contracts(self, dt=None):
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            response = requests.get(f"{server_url}/api/contracts")
            if response.status_code == 200:
                contracts = response.json()
                self.display_contracts(contracts)
        
        except Exception as e:
            print(f"Ошибка загрузки контрактов: {e}")
    
    def display_contracts(self, contracts):
        self.contracts_layout.clear_widgets()
        
        for contract in contracts:
            contract_widget = BoxLayout(orientation='vertical', 
                                      size_hint_y=None, height=120, 
                                      padding=5)
            
            # Номер и название
            title_layout = BoxLayout(orientation='horizontal')
            title_layout.add_widget(Label(text=contract['contract_number'], 
                                        font_size=16, size_hint_x=0.3))
            title_layout.add_widget(Label(text=contract['contract_name'][:30] + '...', 
                                        size_hint_x=0.7))
            contract_widget.add_widget(title_layout)
            
            # Заказчик и сумма
            info_layout = BoxLayout(orientation='horizontal')
            info_layout.add_widget(Label(text=contract['customer'], size_hint_x=0.6))
            info_layout.add_widget(Label(text=f"{contract.get('total_amount', 0):,.0f} ₽", 
                                       size_hint_x=0.4))
            contract_widget.add_widget(info_layout)
            
            # Кнопки действий
            actions_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            
            orders_btn = Button(text='Заказы', size_hint_x=0.5)
            orders_btn.bind(on_press=lambda x, cid=contract['id']: self.view_orders(cid))
            actions_layout.add_widget(orders_btn)
            
            balance_btn = Button(text='Баланс', size_hint_x=0.5)
            balance_btn.bind(on_press=lambda x, cid=contract['id']: self.check_balance(cid))
            actions_layout.add_widget(balance_btn)
            
            contract_widget.add_widget(actions_layout)
            
            self.contracts_layout.add_widget(contract_widget)
    
    def view_orders(self, contract_id):
        # Сохраняем ID контракта для экрана заказов
        store = JsonStore('user_data.json')
        store.put('selected_contract', contract_id=contract_id)
        self.manager.current = 'orders'
    
    def check_balance(self, contract_id):
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            response = requests.get(f"{server_url}/api/contract_balance/{contract_id}")
            if response.status_code == 200:
                balance_data = response.json()
                
                content = BoxLayout(orientation='vertical')
                content.add_widget(Label(text=f"Общий баланс: {balance_data['balance']:,.0f} ₽"))
                content.add_widget(Label(text=f"Доступно: {balance_data['available']:,.0f} ₽"))
                content.add_widget(Label(text=f"Зарезервировано: {balance_data['reserved']:,.0f} ₽"))
                
                popup = Popup(title='Баланс контракта', content=content, size_hint=(0.8, 0.5))
                popup.open()
        
        except Exception as e:
            popup = Popup(title='Ошибка', content=Label(text=str(e)), size_hint=(0.8, 0.3))
            popup.open()

class OrdersScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Заголовок с фильтром
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        header.add_widget(Label(text='Заказы', font_size=20, size_hint_x=0.3))
        
        self.status_filter = Spinner(text='Все статусы',
                                   values=['Все статусы', 'created', 'in_progress', 
                                          'completed', 'cancelled'],
                                   size_hint_x=0.4)
        self.status_filter.bind(text=self.filter_orders)
        header.add_widget(self.status_filter)
        
        back_btn = Button(text='Назад', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'contracts'))
        header.add_widget(back_btn)
        
        layout.add_widget(header)
        
        # Список заказов
        scroll = ScrollView()
        self.orders_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.orders_layout.bind(minimum_height=self.orders_layout.setter('height'))
        scroll.add_widget(self.orders_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        self.orders_data = []
        Clock.schedule_once(self.load_orders, 0.1)
    
    def load_orders(self, dt=None):
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            # Проверяем, есть ли выбранный контракт
            contract_id = None
            try:
                contract_data = store.get('selected_contract')
                contract_id = contract_data['contract_id']
            except:
                pass
            
            url = f"{server_url}/api/orders"
            if contract_id:
                url += f"?contract_id={contract_id}"
            
            response = requests.get(url)
            if response.status_code == 200:
                self.orders_data = response.json()
                self.display_orders(self.orders_data)
        
        except Exception as e:
            print(f"Ошибка загрузки заказов: {e}")
    
    def display_orders(self, orders):
        self.orders_layout.clear_widgets()
        
        for order in orders:
            order_widget = BoxLayout(orientation='vertical', 
                                   size_hint_y=None, height=140, 
                                   padding=5)
            
            # Номер заказа и статус
            title_layout = BoxLayout(orientation='horizontal')
            title_layout.add_widget(Label(text=order['order_number'], 
                                        font_size=16, size_hint_x=0.5))
            
            status_color = [1, 1, 1, 1]  # Белый по умолчанию
            if order['priority'] == 'urgent':
                status_color = [1, 0, 0, 1]  # Красный для срочных
            elif order['status'] == 'completed':
                status_color = [0, 1, 0, 1]  # Зеленый для завершенных
            
            status_btn = Button(text=order['status'], size_hint_x=0.5, 
                              background_color=status_color)
            title_layout.add_widget(status_btn)
            
            order_widget.add_widget(title_layout)
            
            # Описание
            if order.get('description'):
                desc_text = order['description'][:50] + '...' if len(order['description']) > 50 else order['description']
                order_widget.add_widget(Label(text=desc_text, size_hint_y=None, height=30))
            
            # Локация и даты
            info_layout = BoxLayout(orientation='horizontal')
            info_layout.add_widget(Label(text=order.get('location', 'Не указано'), 
                                       size_hint_x=0.5))
            
            if order.get('planned_end_date'):
                info_layout.add_widget(Label(text=f"До: {order['planned_end_date']}", 
                                           size_hint_x=0.5))
            order_widget.add_widget(info_layout)
            
            # Кнопки действий
            actions_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            
            if order['status'] == 'created':
                start_btn = Button(text='Начать', size_hint_x=0.33)
                start_btn.bind(on_press=lambda x, oid=order['id']: self.start_order(oid))
                actions_layout.add_widget(start_btn)
            
            materials_btn = Button(text='Материалы', size_hint_x=0.33)
            materials_btn.bind(on_press=lambda x, oid=order['id']: self.view_materials(oid))
            actions_layout.add_widget(materials_btn)
            
            if order.get('is_business_trip'):
                trip_btn = Button(text='Командировка', size_hint_x=0.33)
                trip_btn.bind(on_press=lambda x, oid=order['id']: self.view_trip(oid))
                actions_layout.add_widget(trip_btn)
            
            order_widget.add_widget(actions_layout)
            
            self.orders_layout.add_widget(order_widget)
    
    def filter_orders(self, spinner, text):
        if text == 'Все статусы':
            filtered_orders = self.orders_data
        else:
            filtered_orders = [order for order in self.orders_data if order['status'] == text]
        
        self.display_orders(filtered_orders)
    
    def start_order(self, order_id):
        # Логика начала выполнения заказа
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            response = requests.put(f"{server_url}/api/orders/{order_id}/start")
            if response.status_code == 200:
                self.load_orders()  # Обновляем список
        
        except Exception as e:
            popup = Popup(title='Ошибка', content=Label(text=str(e)), size_hint=(0.8, 0.3))
            popup.open()
    
    def view_materials(self, order_id):
        # Переходим к экрану материалов для заказа
        store = JsonStore('user_data.json')
        store.put('selected_order', order_id=order_id)
        self.manager.current = 'materials'
    
    def view_trip(self, order_id):
        # Переходим к экрану командировок
        store = JsonStore('user_data.json')
        store.put('selected_order', order_id=order_id)
        self.manager.current = 'trips'

class MaterialsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Заголовок
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        header.add_widget(Label(text='Материалы', font_size=20))
        
        back_btn = Button(text='Назад', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'orders'))
        header.add_widget(back_btn)
        
        layout.add_widget(header)
        
        # Поиск
        search_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        search_layout.add_widget(Label(text='Поиск:', size_hint_x=None, width=60))
        
        self.search_input = TextInput(multiline=False)
        self.search_input.bind(text=self.search_materials)
        search_layout.add_widget(self.search_input)
        
        layout.add_widget(search_layout)
        
        # Список материалов
        scroll = ScrollView()
        self.materials_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.materials_layout.bind(minimum_height=self.materials_layout.setter('height'))
        scroll.add_widget(self.materials_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        self.materials_data = []
        Clock.schedule_once(self.load_materials, 0.1)
    
    def load_materials(self, dt=None):
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            response = requests.get(f"{server_url}/api/materials")
            if response.status_code == 200:
                self.materials_data = response.json()
                self.display_materials(self.materials_data)
        
        except Exception as e:
            print(f"Ошибка загрузки материалов: {e}")
    
    def display_materials(self, materials):
        self.materials_layout.clear_widgets()
        
        for material in materials:
            material_widget = BoxLayout(orientation='vertical', 
                                      size_hint_y=None, height=100, 
                                      padding=5)
            
            # Артикул и название
            title_layout = BoxLayout(orientation='horizontal')
            title_layout.add_widget(Label(text=material['part_number'], 
                                        font_size=14, size_hint_x=0.3))
            title_layout.add_widget(Label(text=material['name'][:30] + '...', 
                                        size_hint_x=0.7))
            material_widget.add_widget(title_layout)
            
            # Остаток и статус
            stock_layout = BoxLayout(orientation='horizontal')
            
            stock_text = f"На складе: {material.get('current_stock', 0)}"
            if material.get('current_stock', 0) < material.get('min_stock', 0):
                stock_text += " (ДЕФИЦИТ!)"
            
            stock_layout.add_widget(Label(text=stock_text, size_hint_x=0.7))
            stock_layout.add_widget(Label(text=f"{material.get('price', 0):.2f} ₽", 
                                        size_hint_x=0.3))
            
            material_widget.add_widget(stock_layout)
            
            self.materials_layout.add_widget(material_widget)
    
    def search_materials(self, instance, text):
        if not text:
            filtered_materials = self.materials_data
        else:
            filtered_materials = [m for m in self.materials_data 
                                if text.lower() in m['name'].lower() or 
                                   text.lower() in m['part_number'].lower()]
        
        self.display_materials(filtered_materials)

class BusinessTripsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()
    
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Заголовок
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        header.add_widget(Label(text='Командировки', font_size=20))
        
        back_btn = Button(text='Назад', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'dashboard'))
        header.add_widget(back_btn)
        
        layout.add_widget(header)
        
        # Список командировок
        scroll = ScrollView()
        self.trips_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.trips_layout.bind(minimum_height=self.trips_layout.setter('height'))
        scroll.add_widget(self.trips_layout)
        layout.add_widget(scroll)
        
        self.add_widget(layout)
        
        Clock.schedule_once(self.load_trips, 0.1)
    
    def load_trips(self, dt=None):
        try:
            store = JsonStore('user_data.json')
            auth_data = store.get('auth')
            server_url = auth_data['server_url']
            
            response = requests.get(f"{server_url}/api/business_trips")
            if response.status_code == 200:
                trips = response.json()
                self.display_trips(trips)
        
        except Exception as e:
            print(f"Ошибка загрузки командировок: {e}")
    
    def display_trips(self, trips):
        self.trips_layout.clear_widgets()
        
        for trip in trips:
            trip_widget = BoxLayout(orientation='vertical', 
                                  size_hint_y=None, height=120, 
                                  padding=5)
            
            # Сотрудник и направление
            title_layout = BoxLayout(orientation='horizontal')
            title_layout.add_widget(Label(text=trip['employee_name'], 
                                        font_size=14, size_hint_x=0.5))
            title_layout.add_widget(Label(text=trip['destination'], 
                                        size_hint_x=0.5))
            trip_widget.add_widget(title_layout)
            
            # Даты
            dates_layout = BoxLayout(orientation='horizontal')
            dates_text = f"{trip['start_date']} - {trip['end_date']}"
            dates_layout.add_widget(Label(text=dates_text))
            trip_widget.add_widget(dates_layout)
            
            # Статус и действия
            status_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            
            status_color = [0.8, 0.8, 0.8, 1]  # Серый по умолчанию
            if trip['status'] == 'in_progress':
                status_color = [0, 1, 0, 1]  # Зеленый
            elif trip['status'] == 'planned':
                status_color = [1, 1, 0, 1]  # Желтый
            
            status_btn = Button(text=trip['status'], size_hint_x=0.5, 
                              background_color=status_color)
            status_layout.add_widget(status_btn)
            
            extend_btn = Button(text='Продлить', size_hint_x=0.5)
            extend_btn.bind(on_press=lambda x, tid=trip['id']: self.extend_trip(tid))
            status_layout.add_widget(extend_btn)
            
            trip_widget.add_widget(status_layout)
            
            self.trips_layout.add_widget(trip_widget)
    
    def extend_trip(self, trip_id):
        # Форма продления командировки
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='Новая дата окончания:'))
        
        date_input = TextInput(text=datetime.now().strftime('%Y-%m-%d'), multiline=False)
        content.add_widget(date_input)
        
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        
        save_btn = Button(text='Сохранить')
        def save_extension(instance):
            # Логика сохранения продления
            popup.dismiss()
        
        save_btn.bind(on_press=save_extension)
        buttons_layout.add_widget(save_btn)
        
        cancel_btn = Button(text='Отмена')
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        buttons_layout.add_widget(cancel_btn)
        
        content.add_widget(buttons_layout)
        
        popup = Popup(title='Продление командировки', content=content, 
                     size_hint=(0.8, 0.6))
        popup.open()

class ContractManagerApp(App):
    def build(self):
        # Создаем менеджер экранов
        sm = ScreenManager()
        
        # Добавляем экраны
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        sm.add_widget(ContractsScreen(name='contracts'))
        sm.add_widget(OrdersScreen(name='orders'))
        sm.add_widget(MaterialsScreen(name='materials'))
        sm.add_widget(BusinessTripsScreen(name='trips'))
        
        return sm

if __name__ == '__main__':
    ContractManagerApp().run()