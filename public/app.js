// Основной JavaScript файл для системы управления сервисными контрактами

class ServiceContractsApp {
    constructor() {
        this.apiBase = '/api';
        this.token = localStorage.getItem('token');
        this.currentUser = null;
        this.charts = {};
        
        this.init();
    }

    async init() {
        // Проверяем наличие токена
        if (this.token) {
            try {
                await this.loadDashboardData();
                this.showMainInterface();
            } catch (error) {
                console.error('Ошибка загрузки данных:', error);
                this.showLoginScreen();
            }
        } else {
            this.showLoginScreen();
        }

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Форма входа
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Кнопка выхода
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        // Навигация
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                this.switchSection(e.currentTarget.dataset.section);
            });
        });

        // Кнопки добавления
        document.getElementById('add-contract-btn').addEventListener('click', () => {
            this.showContractModal();
        });

        document.getElementById('add-order-btn').addEventListener('click', () => {
            this.showOrderModal();
        });

        document.getElementById('add-material-btn').addEventListener('click', () => {
            this.showMaterialModal();
        });

        document.getElementById('add-trip-btn').addEventListener('click', () => {
            this.showTripModal();
        });

        document.getElementById('add-finance-operation-btn').addEventListener('click', () => {
            this.showFinanceOperationModal();
        });

        document.getElementById('upload-document-btn').addEventListener('click', () => {
            this.showDocumentUploadModal();
        });

        // Фильтры
        document.getElementById('contract-filter').addEventListener('change', () => {
            this.loadOrders();
        });

        document.getElementById('finance-contract-filter').addEventListener('change', () => {
            this.loadFinancialOperations();
        });

        document.getElementById('document-type-filter').addEventListener('change', () => {
            this.loadDocuments();
        });

        // Поиск материалов
        document.getElementById('material-search').addEventListener('input', (e) => {
            this.searchMaterials(e.target.value);
        });

        // Уведомления
        document.getElementById('notifications-btn').addEventListener('click', () => {
            this.toggleNotificationsPanel();
        });

        document.getElementById('close-notifications').addEventListener('click', () => {
            this.hideNotificationsPanel();
        });

        // Модальные окна
        document.getElementById('modal-close').addEventListener('click', () => {
            this.hideModal();
        });

        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.hideModal();
            }
        });

        // Отчеты
        document.getElementById('generate-report-btn').addEventListener('click', () => {
            this.generateReport();
        });
    }

    async handleLogin() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${this.apiBase}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.token = data.token;
                this.currentUser = data.user;
                localStorage.setItem('token', this.token);
                
                await this.loadDashboardData();
                this.showMainInterface();
            } else {
                alert('Ошибка входа: ' + data.error);
            }
        } catch (error) {
            console.error('Ошибка входа:', error);
            alert('Ошибка соединения с сервером');
        }
    }

    handleLogout() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('token');
        this.showLoginScreen();
    }

    showLoginScreen() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('main-interface').classList.add('hidden');
    }

    showMainInterface() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('main-interface').classList.remove('hidden');
    }

    switchSection(sectionName) {
        // Обновляем навигацию
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionName}"]`).classList.add('active');

        // Показываем нужную секцию
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionName).classList.add('active');

        // Загружаем данные для секции
        this.loadSectionData(sectionName);
    }

    async loadSectionData(sectionName) {
        switch (sectionName) {
            case 'dashboard':
                await this.loadDashboardData();
                break;
            case 'contracts':
                await this.loadContracts();
                break;
            case 'orders':
                await this.loadOrders();
                await this.loadContractFilter();
                break;
            case 'materials':
                await this.loadMaterials();
                break;
            case 'trips':
                await this.loadBusinessTrips();
                break;
            case 'finance':
                await this.loadFinancialOperations();
                await this.loadFinanceContractFilter();
                break;
            case 'documents':
                await this.loadDocuments();
                break;
            case 'reports':
                await this.loadReports();
                break;
        }
    }

    async loadDashboardData() {
        try {
            // Загружаем общую статистику
            const contractsResponse = await this.apiCall('/analytics/contracts-summary');
            const contractsData = contractsResponse;

            document.getElementById('total-contracts').textContent = contractsData.total_contracts || 0;
            document.getElementById('active-contracts').textContent = contractsData.active_contracts || 0;

            // Загружаем заказы для подсчета активных
            const ordersResponse = await this.apiCall('/orders');
            const activeOrders = ordersResponse.filter(order => order.status === 'in_progress').length;
            document.getElementById('active-orders').textContent = activeOrders;

            // Загружаем дефицит материалов
            const deficitResponse = await this.apiCall('/analytics/materials-deficit');
            document.getElementById('materials-deficit').textContent = deficitResponse.length || 0;

            // Загружаем командировки
            const tripsResponse = await this.apiCall('/business-trips');
            const activeTrips = tripsResponse.filter(trip => trip.status === 'in_progress').length;
            document.getElementById('active-trips').textContent = activeTrips;

            // Создаем графики
            this.createCharts(contractsData, ordersResponse);

        } catch (error) {
            console.error('Ошибка загрузки данных панели управления:', error);
        }
    }

    createCharts(contractsData, ordersData) {
        // График финансового состояния контрактов
        const contractsCtx = document.getElementById('contracts-chart');
        if (contractsCtx) {
            new Chart(contractsCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Авансы', 'Остаток'],
                    datasets: [{
                        data: [
                            contractsData.total_advances || 0,
                            (contractsData.total_contracts_value || 0) - (contractsData.total_advances || 0)
                        ],
                        backgroundColor: ['#667eea', '#f093fb']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        // График статуса заказов
        const ordersCtx = document.getElementById('orders-chart');
        if (ordersCtx) {
            const statusCounts = ordersData.reduce((acc, order) => {
                acc[order.status] = (acc[order.status] || 0) + 1;
                return acc;
            }, {});

            new Chart(ordersCtx, {
                type: 'bar',
                data: {
                    labels: Object.keys(statusCounts),
                    datasets: [{
                        label: 'Количество заказов',
                        data: Object.values(statusCounts),
                        backgroundColor: '#667eea'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }

    async loadContracts() {
        try {
            const contracts = await this.apiCall('/contracts');
            this.renderContractsTable(contracts);
        } catch (error) {
            console.error('Ошибка загрузки контрактов:', error);
        }
    }

    renderContractsTable(contracts) {
        const tbody = document.querySelector('#contracts-table tbody');
        tbody.innerHTML = '';

        contracts.forEach(contract => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${contract.contract_number}</td>
                <td>${contract.customer_name}</td>
                <td>${this.formatDate(contract.start_date)}</td>
                <td>${this.formatDate(contract.end_date)}</td>
                <td>${this.formatCurrency(contract.total_amount)}</td>
                <td>${this.formatCurrency(contract.advance_amount)}</td>
                <td><span class="status-badge status-${contract.status}">${contract.status}</span></td>
                <td class="actions">
                    <button class="btn-icon" onclick="app.editContract('${contract.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteContract('${contract.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadOrders() {
        try {
            const contractId = document.getElementById('contract-filter').value;
            const orders = await this.apiCall(`/orders${contractId ? `?contract_id=${contractId}` : ''}`);
            this.renderOrdersTable(orders);
        } catch (error) {
            console.error('Ошибка загрузки заказов:', error);
        }
    }

    renderOrdersTable(orders) {
        const tbody = document.querySelector('#orders-table tbody');
        tbody.innerHTML = '';

        orders.forEach(order => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${order.order_number}</td>
                <td>${order.contract_number || ''}</td>
                <td>${order.description || ''}</td>
                <td>${order.location || ''}</td>
                <td><span class="status-badge status-${order.priority}">${order.priority}</span></td>
                <td><span class="status-badge status-${order.status}">${order.status}</span></td>
                <td>${this.formatCurrency(order.actual_cost || order.estimated_cost)}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="app.editOrder('${order.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteOrder('${order.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadMaterials() {
        try {
            const materials = await this.apiCall('/materials');
            this.renderMaterialsTable(materials);
        } catch (error) {
            console.error('Ошибка загрузки материалов:', error);
        }
    }

    renderMaterialsTable(materials) {
        const tbody = document.querySelector('#materials-table tbody');
        tbody.innerHTML = '';

        materials.forEach(material => {
            const available = (material.stock_quantity || 0) - (material.reserved_quantity || 0);
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${material.material_code}</td>
                <td>${material.name}</td>
                <td>${material.unit}</td>
                <td>${this.formatCurrency(material.unit_price)}</td>
                <td>${material.stock_quantity || 0}</td>
                <td>${material.reserved_quantity || 0}</td>
                <td>${available}</td>
                <td>${material.supplier || ''}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="app.editMaterial('${material.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteMaterial('${material.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadBusinessTrips() {
        try {
            const trips = await this.apiCall('/business-trips');
            this.renderTripsTable(trips);
        } catch (error) {
            console.error('Ошибка загрузки командировок:', error);
        }
    }

    renderTripsTable(trips) {
        const tbody = document.querySelector('#trips-table tbody');
        tbody.innerHTML = '';

        trips.forEach(trip => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${trip.employee_name || ''}</td>
                <td>${trip.order_number || ''}</td>
                <td>${trip.destination}</td>
                <td>${this.formatDate(trip.start_date)}</td>
                <td>${this.formatDate(trip.end_date)}</td>
                <td><span class="status-badge status-${trip.status}">${trip.status}</span></td>
                <td>${this.formatCurrency(trip.actual_cost || trip.estimated_cost)}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="app.editTrip('${trip.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteTrip('${trip.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadFinancialOperations() {
        try {
            const contractId = document.getElementById('finance-contract-filter').value;
            const operations = await this.apiCall(`/financial-operations${contractId ? `?contract_id=${contractId}` : ''}`);
            this.renderFinancialTable(operations);
        } catch (error) {
            console.error('Ошибка загрузки финансовых операций:', error);
        }
    }

    renderFinancialTable(operations) {
        const tbody = document.querySelector('#finance-table tbody');
        tbody.innerHTML = '';

        operations.forEach(operation => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${this.formatDate(operation.operation_date)}</td>
                <td><span class="status-badge status-${operation.operation_type}">${operation.operation_type}</span></td>
                <td>${operation.contract_number || ''}</td>
                <td>${this.formatCurrency(operation.amount)}</td>
                <td>${operation.description || ''}</td>
                <td>${operation.document_number || ''}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="app.editFinancialOperation('${operation.id}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteFinancialOperation('${operation.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadDocuments() {
        try {
            const documentType = document.getElementById('document-type-filter').value;
            const documents = await this.apiCall(`/documents${documentType ? `?document_type=${documentType}` : ''}`);
            this.renderDocumentsTable(documents);
        } catch (error) {
            console.error('Ошибка загрузки документов:', error);
        }
    }

    renderDocumentsTable(documents) {
        const tbody = document.querySelector('#documents-table tbody');
        tbody.innerHTML = '';

        documents.forEach(document => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="status-badge status-${document.document_type}">${document.document_type}</span></td>
                <td>${document.title}</td>
                <td>${document.contract_number || ''}</td>
                <td>${this.formatDate(document.created_at)}</td>
                <td>${this.formatFileSize(document.file_size)}</td>
                <td>${document.physical_location || ''}</td>
                <td class="actions">
                    <button class="btn-icon" onclick="app.downloadDocument('${document.id}')">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteDocument('${document.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    async loadReports() {
        try {
            // Загружаем дефицит материалов
            const deficitData = await this.apiCall('/analytics/materials-deficit');
            this.renderMaterialsDeficitReport(deficitData);

            // Загружаем финансовое состояние
            const financialData = await this.apiCall('/analytics/contracts-summary');
            this.renderFinancialStatusReport(financialData);

        } catch (error) {
            console.error('Ошибка загрузки отчетов:', error);
        }
    }

    renderMaterialsDeficitReport(data) {
        const container = document.getElementById('materials-deficit-report');
        if (data.length === 0) {
            container.innerHTML = '<p>Дефицита материалов не обнаружено</p>';
            return;
        }

        let html = '<ul>';
        data.forEach(item => {
            const deficit = item.total_required - item.free_quantity;
            html += `<li><strong>${item.name}</strong> - дефицит: ${deficit.toFixed(2)} ${item.unit}</li>`;
        });
        html += '</ul>';
        container.innerHTML = html;
    }

    renderFinancialStatusReport(data) {
        const container = document.getElementById('financial-status-report');
        const remaining = (data.total_contracts_value || 0) - (data.total_advances || 0);
        
        container.innerHTML = `
            <div class="financial-summary">
                <p><strong>Общая стоимость контрактов:</strong> ${this.formatCurrency(data.total_contracts_value)}</p>
                <p><strong>Выплачено авансов:</strong> ${this.formatCurrency(data.total_advances)}</p>
                <p><strong>Остаток к доплате:</strong> ${this.formatCurrency(remaining)}</p>
            </div>
        `;
    }

    async loadContractFilter() {
        try {
            const contracts = await this.apiCall('/contracts');
            const select = document.getElementById('contract-filter');
            select.innerHTML = '<option value="">Все контракты</option>';
            
            contracts.forEach(contract => {
                const option = document.createElement('option');
                option.value = contract.id;
                option.textContent = `${contract.contract_number} - ${contract.customer_name}`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Ошибка загрузки списка контрактов:', error);
        }
    }

    async loadFinanceContractFilter() {
        try {
            const contracts = await this.apiCall('/contracts');
            const select = document.getElementById('finance-contract-filter');
            select.innerHTML = '<option value="">Все контракты</option>';
            
            contracts.forEach(contract => {
                const option = document.createElement('option');
                option.value = contract.id;
                option.textContent = `${contract.contract_number} - ${contract.customer_name}`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Ошибка загрузки списка контрактов:', error);
        }
    }

    async searchMaterials(query) {
        try {
            const materials = await this.apiCall(`/materials?search=${encodeURIComponent(query)}`);
            this.renderMaterialsTable(materials);
        } catch (error) {
            console.error('Ошибка поиска материалов:', error);
        }
    }

    // Модальные окна
    showModal(title, content, footer = '') {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = content;
        document.getElementById('modal-footer').innerHTML = footer;
        document.getElementById('modal-overlay').classList.remove('hidden');
    }

    hideModal() {
        document.getElementById('modal-overlay').classList.add('hidden');
    }

    showContractModal(contract = null) {
        const isEdit = contract !== null;
        const title = isEdit ? 'Редактировать контракт' : 'Добавить контракт';
        
        const content = `
            <form id="contract-form">
                <div class="form-group">
                    <label for="contract-number">Номер контракта:</label>
                    <input type="text" id="contract-number" name="contract_number" value="${contract?.contract_number || ''}" required>
                </div>
                <div class="form-group">
                    <label for="customer-name">Заказчик:</label>
                    <input type="text" id="customer-name" name="customer_name" value="${contract?.customer_name || ''}" required>
                </div>
                <div class="form-group">
                    <label for="customer-contact">Контактное лицо:</label>
                    <input type="text" id="customer-contact" name="customer_contact" value="${contract?.customer_contact || ''}">
                </div>
                <div class="form-group">
                    <label for="start-date">Дата начала:</label>
                    <input type="date" id="start-date" name="start_date" value="${contract?.start_date || ''}" required>
                </div>
                <div class="form-group">
                    <label for="end-date">Дата окончания:</label>
                    <input type="date" id="end-date" name="end_date" value="${contract?.end_date || ''}">
                </div>
                <div class="form-group">
                    <label for="total-amount">Общая сумма:</label>
                    <input type="number" id="total-amount" name="total_amount" step="0.01" value="${contract?.total_amount || ''}">
                </div>
                <div class="form-group">
                    <label for="advance-amount">Сумма аванса:</label>
                    <input type="number" id="advance-amount" name="advance_amount" step="0.01" value="${contract?.advance_amount || ''}">
                </div>
            </form>
        `;

        const footer = `
            <button type="button" class="btn btn-secondary" onclick="app.hideModal()">Отмена</button>
            <button type="button" class="btn btn-primary" onclick="app.saveContract(${isEdit ? `'${contract.id}'` : 'null'})">Сохранить</button>
        `;

        this.showModal(title, content, footer);
    }

    async saveContract(contractId) {
        const form = document.getElementById('contract-form');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            if (contractId) {
                // Редактирование существующего контракта
                await this.apiCall(`/contracts/${contractId}`, 'PUT', data);
            } else {
                // Создание нового контракта
                await this.apiCall('/contracts', 'POST', data);
            }
            
            this.hideModal();
            this.loadContracts();
        } catch (error) {
            console.error('Ошибка сохранения контракта:', error);
            alert('Ошибка сохранения контракта');
        }
    }

    // Уведомления
    toggleNotificationsPanel() {
        const panel = document.getElementById('notifications-panel');
        panel.classList.toggle('hidden');
        
        if (!panel.classList.contains('hidden')) {
            this.loadNotifications();
        }
    }

    hideNotificationsPanel() {
        document.getElementById('notifications-panel').classList.add('hidden');
    }

    async loadNotifications() {
        try {
            const notifications = await this.apiCall('/notifications');
            this.renderNotifications(notifications);
        } catch (error) {
            console.error('Ошибка загрузки уведомлений:', error);
        }
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notifications-list');
        container.innerHTML = '';

        if (notifications.length === 0) {
            container.innerHTML = '<p>Уведомлений нет</p>';
            return;
        }

        notifications.forEach(notification => {
            const item = document.createElement('div');
            item.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
            item.innerHTML = `
                <h4>${notification.title}</h4>
                <p>${notification.message}</p>
                <small>${this.formatDate(notification.created_at)}</small>
            `;
            
            if (!notification.is_read) {
                item.addEventListener('click', () => {
                    this.markNotificationAsRead(notification.id);
                });
            }
            
            container.appendChild(item);
        });
    }

    async markNotificationAsRead(notificationId) {
        try {
            await this.apiCall(`/notifications/${notificationId}/read`, 'PUT');
            this.loadNotifications();
        } catch (error) {
            console.error('Ошибка обновления уведомления:', error);
        }
    }

    // API вызовы
    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.apiBase}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                this.handleLogout();
                throw new Error('Не авторизован');
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    // Утилиты
    formatDate(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toLocaleDateString('ru-RU');
    }

    formatCurrency(amount) {
        if (!amount) return '0 ₽';
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB'
        }).format(amount);
    }

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Заглушки для методов, которые будут реализованы позже
    editContract(id) { console.log('Редактировать контракт:', id); }
    deleteContract(id) { console.log('Удалить контракт:', id); }
    editOrder(id) { console.log('Редактировать заказ:', id); }
    deleteOrder(id) { console.log('Удалить заказ:', id); }
    editMaterial(id) { console.log('Редактировать материал:', id); }
    deleteMaterial(id) { console.log('Удалить материал:', id); }
    editTrip(id) { console.log('Редактировать командировку:', id); }
    deleteTrip(id) { console.log('Удалить командировку:', id); }
    editFinancialOperation(id) { console.log('Редактировать финансовую операцию:', id); }
    deleteFinancialOperation(id) { console.log('Удалить финансовую операцию:', id); }
    downloadDocument(id) { console.log('Скачать документ:', id); }
    deleteDocument(id) { console.log('Удалить документ:', id); }
    showOrderModal() { console.log('Показать модальное окно заказа'); }
    showMaterialModal() { console.log('Показать модальное окно материала'); }
    showTripModal() { console.log('Показать модальное окно командировки'); }
    showFinanceOperationModal() { console.log('Показать модальное окно финансовой операции'); }
    showDocumentUploadModal() { console.log('Показать модальное окно загрузки документа'); }
    generateReport() { console.log('Генерировать отчет'); }
}

// Инициализация приложения
const app = new ServiceContractsApp();