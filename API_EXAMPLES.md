# Примеры использования API системы управления сервисными контрактами

## Аутентификация

### Получение токена доступа

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
  }'
```

**Ответ:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### Использование токена в запросах

```bash
curl -X GET http://localhost:3000/api/contracts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Управление контрактами

### Получение списка контрактов

```bash
curl -X GET http://localhost:3000/api/contracts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Ответ:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "contract_number": "К-2024-001",
    "customer_name": "ООО Заказчик",
    "customer_contact": "Иванов И.И.",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_amount": 1000000.00,
    "advance_amount": 500000.00,
    "status": "active",
    "orders_count": 5,
    "total_orders_cost": 750000.00
  }
]
```

### Создание нового контракта

```bash
curl -X POST http://localhost:3000/api/contracts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_number": "К-2024-002",
    "customer_name": "ООО Новый заказчик",
    "customer_contact": "Петров П.П.",
    "start_date": "2024-02-01",
    "end_date": "2024-11-30",
    "total_amount": 2000000.00,
    "advance_amount": 1000000.00
  }'
```

### Обновление контракта

```bash
curl -X PUT http://localhost:3000/api/contracts/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "end_date": "2024-01-31"
  }'
```

## Управление заказами

### Получение списка заказов

```bash
# Все заказы
curl -X GET http://localhost:3000/api/orders \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Заказы по контракту
curl -X GET "http://localhost:3000/api/orders?contract_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Заказы по статусу
curl -X GET "http://localhost:3000/api/orders?status=in_progress" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Создание нового заказа

```bash
curl -X POST http://localhost:3000/api/orders \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "123e4567-e89b-12d3-a456-426614174000",
    "order_number": "З-2024-001",
    "order_date": "2024-01-15",
    "description": "Ремонт оборудования на объекте",
    "location": "г. Москва, ул. Примерная, д. 1",
    "priority": "high",
    "estimated_cost": 150000.00
  }'
```

## Управление материалами

### Получение списка материалов

```bash
# Все материалы
curl -X GET http://localhost:3000/api/materials \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Поиск материалов
curl -X GET "http://localhost:3000/api/materials?search=болт" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Получение дефицита материалов

```bash
curl -X GET http://localhost:3000/api/analytics/materials-deficit \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Ответ:**
```json
[
  {
    "material_code": "БОЛТ-М8-20",
    "name": "Болт М8х20",
    "unit": "шт",
    "available_quantity": 5,
    "total_required": 25,
    "deficit": 20
  }
]
```

## Управление командировками

### Получение списка командировок

```bash
curl -X GET http://localhost:3000/api/business-trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Создание новой командировки

```bash
curl -X POST http://localhost:3000/api/business-trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "456e7890-e89b-12d3-a456-426614174001",
    "order_id": "789e0123-e89b-12d3-a456-426614174002",
    "destination": "г. Санкт-Петербург",
    "start_date": "2024-02-01",
    "end_date": "2024-02-05",
    "purpose": "Выполнение сервисных работ",
    "estimated_cost": 50000.00
  }'
```

## Финансовые операции

### Получение финансовых операций

```bash
# Все операции
curl -X GET http://localhost:3000/api/financial-operations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Операции по контракту
curl -X GET "http://localhost:3000/api/financial-operations?contract_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Создание финансовой операции

```bash
curl -X POST http://localhost:3000/api/financial-operations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "123e4567-e89b-12d3-a456-426614174000",
    "operation_type": "advance",
    "amount": 500000.00,
    "operation_date": "2024-01-01",
    "description": "Аванс по контракту",
    "document_number": "ПП-001"
  }'
```

## Управление документами

### Получение списка документов

```bash
# Все документы
curl -X GET http://localhost:3000/api/documents \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Документы по типу
curl -X GET "http://localhost:3000/api/documents?document_type=contract" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Документы по контракту
curl -X GET "http://localhost:3000/api/documents?related_contract_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Загрузка документа

```bash
curl -X POST http://localhost:3000/api/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "document_type=contract" \
  -F "title=Договор на сервисное обслуживание" \
  -F "description=Основной договор с заказчиком" \
  -F "related_contract_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "physical_location=Шкаф А, полка 1"
```

### Скачивание документа

```bash
curl -X GET http://localhost:3000/api/documents/456e7890-e89b-12d3-a456-426614174001/download \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o downloaded_document.pdf
```

## Аналитика и отчеты

### Получение сводки по контрактам

```bash
curl -X GET http://localhost:3000/api/analytics/contracts-summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Ответ:**
```json
{
  "total_contracts": 15,
  "active_contracts": 12,
  "total_contracts_value": 15000000.00,
  "total_advances": 7500000.00,
  "remaining_amount": 7500000.00
}
```

### Генерация отчета

```bash
# Отчет по контрактам
curl -X POST http://localhost:3000/api/reports/contracts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "status": "active"
  }'

# Отчет по материалам
curl -X POST http://localhost:3000/api/reports/materials \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "include_deficit": true,
    "category": "hardware"
  }'
```

## Уведомления

### Получение уведомлений

```bash
curl -X GET http://localhost:3000/api/notifications \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Отметка уведомления как прочитанного

```bash
curl -X PUT http://localhost:3000/api/notifications/789e0123-e89b-12d3-a456-426614174003/read \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Примеры использования в JavaScript

### Создание клиента API

```javascript
class ServiceContractsAPI {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  }

  // Контракты
  async getContracts() {
    return this.request('/contracts');
  }

  async createContract(contractData) {
    return this.request('/contracts', {
      method: 'POST',
      body: JSON.stringify(contractData)
    });
  }

  async updateContract(id, contractData) {
    return this.request(`/contracts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(contractData)
    });
  }

  // Заказы
  async getOrders(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.request(`/orders?${params}`);
  }

  async createOrder(orderData) {
    return this.request('/orders', {
      method: 'POST',
      body: JSON.stringify(orderData)
    });
  }

  // Материалы
  async getMaterials(search = '') {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request(`/materials${params}`);
  }

  async getMaterialsDeficit() {
    return this.request('/analytics/materials-deficit');
  }

  // Документы
  async uploadDocument(file, metadata) {
    const formData = new FormData();
    formData.append('file', file);
    Object.keys(metadata).forEach(key => {
      formData.append(key, metadata[key]);
    });

    return this.request('/documents/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`
      },
      body: formData
    });
  }

  async downloadDocument(id) {
    const response = await fetch(`${this.baseURL}/documents/${id}/download`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.blob();
  }
}

// Использование
const api = new ServiceContractsAPI('http://localhost:3000/api', 'YOUR_JWT_TOKEN');

// Получение контрактов
api.getContracts().then(contracts => {
  console.log('Контракты:', contracts);
});

// Создание нового контракта
api.createContract({
  contract_number: 'К-2024-003',
  customer_name: 'ООО Тест',
  start_date: '2024-03-01',
  total_amount: 1000000
}).then(contract => {
  console.log('Создан контракт:', contract);
});
```

## Примеры использования в Python

```python
import requests
import json

class ServiceContractsAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def request(self, endpoint, method='GET', data=None):
        url = f"{self.base_url}{endpoint}"
        
        if method == 'GET':
            response = requests.get(url, headers=self.headers)
        elif method == 'POST':
            response = requests.post(url, headers=self.headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=self.headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=self.headers)
        
        response.raise_for_status()
        return response.json()

    def get_contracts(self):
        return self.request('/contracts')

    def create_contract(self, contract_data):
        return self.request('/contracts', 'POST', contract_data)

    def get_orders(self, filters=None):
        params = filters or {}
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        endpoint = f"/orders?{query_string}" if query_string else "/orders"
        return self.request(endpoint)

    def get_materials_deficit(self):
        return self.request('/analytics/materials-deficit')

# Использование
api = ServiceContractsAPI('http://localhost:3000/api', 'YOUR_JWT_TOKEN')

# Получение контрактов
contracts = api.get_contracts()
print(f"Найдено контрактов: {len(contracts)}")

# Создание контракта
new_contract = api.create_contract({
    'contract_number': 'К-2024-004',
    'customer_name': 'ООО Python Test',
    'start_date': '2024-04-01',
    'total_amount': 2000000
})
print(f"Создан контракт: {new_contract['contract_number']}")
```

## Обработка ошибок

### Коды ошибок

- `400` - Неверный запрос
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Не найдено
- `500` - Внутренняя ошибка сервера

### Пример обработки ошибок

```javascript
try {
  const contracts = await api.getContracts();
  console.log('Контракты:', contracts);
} catch (error) {
  if (error.message.includes('401')) {
    console.error('Ошибка авторизации. Проверьте токен.');
  } else if (error.message.includes('404')) {
    console.error('Ресурс не найден.');
  } else {
    console.error('Ошибка:', error.message);
  }
}
```

## Пагинация

### Параметры пагинации

```bash
# Получение первой страницы (20 записей)
curl -X GET "http://localhost:3000/api/contracts?page=1&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Получение второй страницы
curl -X GET "http://localhost:3000/api/contracts?page=2&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Ответ с пагинацией

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

## Фильтрация и сортировка

### Параметры фильтрации

```bash
# Фильтр по статусу
curl -X GET "http://localhost:3000/api/contracts?status=active" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Фильтр по дате
curl -X GET "http://localhost:3000/api/contracts?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Поиск по названию
curl -X GET "http://localhost:3000/api/contracts?search=заказчик" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Сортировка

```bash
# Сортировка по дате создания (по убыванию)
curl -X GET "http://localhost:3000/api/contracts?sort=-created_at" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Сортировка по сумме контракта (по возрастанию)
curl -X GET "http://localhost:3000/api/contracts?sort=total_amount" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## WebSocket уведомления

### Подключение к WebSocket

```javascript
const ws = new WebSocket('ws://localhost:3000/ws');

ws.onopen = function() {
  console.log('WebSocket подключен');
  
  // Аутентификация
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'YOUR_JWT_TOKEN'
  }));
};

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'notification':
      console.log('Новое уведомление:', data.message);
      break;
    case 'contract_updated':
      console.log('Контракт обновлен:', data.contract);
      break;
    case 'order_created':
      console.log('Новый заказ:', data.order);
      break;
  }
};

ws.onclose = function() {
  console.log('WebSocket отключен');
};
```

Эти примеры помогут вам интегрировать систему управления сервисными контрактами в ваши приложения и автоматизировать работу с API.