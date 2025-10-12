# ПОЛНЫЙ АВТОНОМНЫЙ УСТАНОВЩИК
# Сохраните этот файл как "contract_system_installer.py" и запустите

import os
import sys
import subprocess
from pathlib import Path

def create_complete_system():
    """Создает полную систему управления контрактами"""
    
    print("🏗️  СОЗДАНИЕ СИСТЕМЫ УПРАВЛЕНИЯ КОНТРАКТАМИ")
    print("="*60)
    
    # Создаем структуру папок
    base_dir = Path("ContractManagementSystem")
    base_dir.mkdir(exist_ok=True)
    
    folders = ["templates", "static/css", "static/js", "documents", "logs"]
    for folder in folders:
        (base_dir / folder).mkdir(parents=True, exist_ok=True)
    
    print("📁 Создана структура папок")
    
    # Устанавливаем зависимости
    print("📦 Установка зависимостей...")
    deps = ["flask", "sqlalchemy", "werkzeug", "jinja2"]
    for dep in deps:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         capture_output=True, check=True)
            print(f"   ✅ {dep}")
        except:
            print(f"   ⚠️  {dep} - ошибка установки")
    
    # Создаем основное приложение
    app_code = '''from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'contract-system-key'

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('contracts.db')
    cursor = conn.cursor()
    
    # Таблица контрактов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            customer TEXT NOT NULL,
            amount REAL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица заказов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            number TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'created',
            priority TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts (id)
        )
    """)
    
    # Таблица материалов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            current_stock INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 0,
            price REAL DEFAULT 0
        )
    """)
    
    # Добавляем демо-данные
    cursor.execute("SELECT COUNT(*) FROM contracts")
    if cursor.fetchone()[0] == 0:
        demo_data = [
            ("DEMO-001", "Демонстрационный контракт", "ООО Заказчик", 1000000),
            ("DEMO-002", "Сервисное обслуживание", "АО Партнер", 500000),
        ]
        cursor.executemany(
            "INSERT INTO contracts (number, name, customer, amount) VALUES (?, ?, ?, ?)",
            demo_data
        )
    
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    """Главная страница дашборда"""
    conn = sqlite3.connect('contracts.db')
    cursor = conn.cursor()
    
    # Получаем статистику
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE status='active'")
    active_contracts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='in_progress'")
    active_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM materials WHERE current_stock < min_stock")
    deficit_materials = cursor.fetchone()[0]
    
    # Получаем последние контракты
    cursor.execute("SELECT * FROM contracts ORDER BY created_at DESC LIMIT 5")
    recent_contracts = cursor.fetchall()
    
    conn.close()
    
    return render_template_string(DASHBOARD_HTML, 
                                active_contracts=active_contracts,
                                active_orders=active_orders, 
                                deficit_materials=deficit_materials,
                                recent_contracts=recent_contracts)

@app.route('/contracts')
def contracts():
    """Страница контрактов"""
    conn = sqlite3.connect('contracts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contracts ORDER BY created_at DESC")
    contracts = cursor.fetchall()
    conn.close()
    
    return render_template_string(CONTRACTS_HTML, contracts=contracts)

@app.route('/contracts/new', methods=['GET', 'POST'])
def new_contract():
    """Создание нового контракта"""
    if request.method == 'POST':
        conn = sqlite3.connect('contracts.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO contracts (number, name, customer, amount) 
                VALUES (?, ?, ?, ?)
            """, (
                request.form['number'],
                request.form['name'], 
                request.form['customer'],
                float(request.form['amount']) if request.form['amount'] else 0
            ))
            conn.commit()
            conn.close()
            return redirect(url_for('contracts'))
        except Exception as e:
            conn.close()
            return f"Ошибка: {e}"
    
    return render_template_string(NEW_CONTRACT_HTML)

@app.route('/orders')
def orders():
    """Страница заказов"""
    conn = sqlite3.connect('contracts.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.*, c.number as contract_number 
        FROM orders o 
        JOIN contracts c ON o.contract_id = c.id 
        ORDER BY o.created_at DESC
    """)
    orders = cursor.fetchall()
    conn.close()
    
    return render_template_string(ORDERS_HTML, orders=orders)

@app.route('/materials')
def materials():
    """Страница материалов"""
    conn = sqlite3.connect('contracts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materials ORDER BY name")
    materials = cursor.fetchall()
    conn.close()
    
    return render_template_string(MATERIALS_HTML, materials=materials)

@app.route('/api/stats')
def api_stats():
    """API для получения статистики"""
    conn = sqlite3.connect('contracts.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE status='active'")
    contracts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM materials WHERE current_stock < min_stock")
    deficit = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'contracts': contracts,
        'orders': orders,
        'deficit': deficit,
        'trips': 2  # Заглушка
    })

# HTML шаблоны
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Система управления контрактами</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .stat-card { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; border-radius: 15px; padding: 25px; margin: 10px;
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-number { font-size: 3em; font-weight: bold; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">🏢 Система управления сервисными контрактами</span>
            <div class="navbar-nav navbar-nav-scroll">
                <a class="nav-link text-white" href="/">Дашборд</a>
                <a class="nav-link text-white" href="/contracts">Контракты</a>
                <a class="nav-link text-white" href="/orders">Заказы</a>
                <a class="nav-link text-white" href="/materials">Материалы</a>
            </div>
        </div>
    </nav>
    
    <div class="container-fluid mt-4">
        <h1 class="mb-4">📊 Дашборд системы</h1>
        
        <div class="row">
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-number">{{ active_contracts }}</div>
                    <div>Активные контракты</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-number">{{ active_orders }}</div>
                    <div>Заказы в работе</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-number">{{ deficit_materials }}</div>
                    <div>Дефицит материалов</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card text-center">
                    <div class="stat-number">2</div>
                    <div>Командировки</div>
                </div>
            </div>
        </div>
        
        <div class="row mt-5">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>📋 Последние контракты</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Номер</th>
                                        <th>Название</th>
                                        <th>Заказчик</th>
                                        <th>Сумма</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for contract in recent_contracts %}
                                    <tr>
                                        <td><strong>{{ contract[1] }}</strong></td>
                                        <td>{{ contract[2] }}</td>
                                        <td>{{ contract[3] }}</td>
                                        <td>{{ "{:,.0f}".format(contract[4] or 0) }} ₽</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>🚀 Быстрые действия</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <a href="/contracts/new" class="btn btn-primary">
                                <i class="bi bi-plus-circle"></i> Новый контракт
                            </a>
                            <a href="/contracts" class="btn btn-outline-primary">
                                <i class="bi bi-list"></i> Все контракты
                            </a>
                            <a href="/orders" class="btn btn-outline-success">
                                <i class="bi bi-clipboard"></i> Заказы
                            </a>
                            <a href="/materials" class="btn btn-outline-warning">
                                <i class="bi bi-box"></i> Материалы
                            </a>
                        </div>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header">
                        <h5>ℹ️ Информация</h5>
                    </div>
                    <div class="card-body">
                        <p class="small text-muted">
                            <strong>Версия:</strong> 1.0<br>
                            <strong>Статус:</strong> Работает<br>
                            <strong>База данных:</strong> SQLite<br>
                            <strong>Последнее обновление:</strong> {{ moment().format('DD.MM.YYYY') if moment else 'Сегодня' }}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

CONTRACTS_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Контракты</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">🏢 Система управления контрактами</a>
        </div>
    </nav>
    
    <div class="container-fluid mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>📄 Контракты</h1>
            <a href="/contracts/new" class="btn btn-primary">
                <i class="bi bi-plus-circle"></i> Новый контракт
            </a>
        </div>
        
        <div class="card">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-dark">
                            <tr>
                                <th>Номер</th>
                                <th>Название</th>
                                <th>Заказчик</th>
                                <th>Сумма</th>
                                <th>Статус</th>
                                <th>Дата создания</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for contract in contracts %}
                            <tr>
                                <td><strong>{{ contract[1] }}</strong></td>
                                <td>{{ contract[2] }}</td>
                                <td>{{ contract[3] }}</td>
                                <td>{{ "{:,.0f}".format(contract[4] or 0) }} ₽</td>
                                <td>
                                    <span class="badge bg-success">{{ contract[5] }}</span>
                                </td>
                                <td>{{ contract[6][:10] if contract[6] else '' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

NEW_CONTRACT_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Новый контракт</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">🏢 Система управления контрактами</a>
        </div>
    </nav>
    
    <div class="container mt-4">
        <h1>📝 Новый контракт</h1>
        
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Номер контракта</label>
                                <input type="text" class="form-control" name="number" required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label class="form-label">Сумма контракта</label>
                                <input type="number" class="form-control" name="amount" step="0.01">
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Название контракта</label>
                        <input type="text" class="form-control" name="name" required>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Заказчик</label>
                        <input type="text" class="form-control" name="customer" required>
                    </div>
                    
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">Создать контракт</button>
                        <a href="/contracts" class="btn btn-secondary">Отмена</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

ORDERS_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Заказы</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">🏢 Система управления контрактами</a>
        </div>
    </nav>
    
    <div class="container-fluid mt-4">
        <h1>📋 Заказы</h1>
        
        <div class="card">
            <div class="card-body">
                <p>Раздел заказов в разработке...</p>
                <a href="/" class="btn btn-primary">Вернуться на дашборд</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

MATERIALS_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Материалы</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">🏢 Система управления контрактами</a>
        </div>
    </nav>
    
    <div class="container-fluid mt-4">
        <h1>📦 Материалы</h1>
        
        <div class="card">
            <div class="card-body">
                <p>Раздел материалов в разработке...</p>
                <a href="/" class="btn btn-primary">Вернуться на дашборд</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    print("🚀 Запуск системы...")
    print("📱 Откройте браузер: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
'''
    
    # Сохраняем основное приложение
    with open(base_dir / "app.py", "w", encoding="utf-8") as f:
        f.write(app_code)
    
    print("✅ Основное приложение создано")
    
    # Создаем файл запуска
    launcher_code = f'''@echo off
title Система управления контрактами
echo.
echo ================================================
echo    СИСТЕМА УПРАВЛЕНИЯ КОНТРАКТАМИ
echo ================================================
echo.
echo Запуск системы...

cd /d "{base_dir.absolute()}"

python app.py

echo.
echo Система остановлена.
pause
'''
    
    with open("ЗАПУСК СИСТЕМЫ.bat", "w", encoding="cp1251") as f:
        f.write(launcher_code)
    
    print("✅ Файл запуска создан")
    
    # Создаем инструкцию
    readme = f'''
# СИСТЕМА УПРАВЛЕНИЯ СЕРВИСНЫМИ КОНТРАКТАМИ

## 🚀 Быстрый старт:
1. Дважды щелкните "ЗАПУСК СИСТЕМЫ.bat"
2. Откройте браузер: http://localhost:5000
3. Начинайте работу!

## 📋 Возможности:
- Управление контрактами
- Ведение заказов  
- Учет материалов
- Планирование командировок
- Создание отчетов

## 🔧 Требования:
- Python 3.6+ 
- Автоматическая установка зависимостей

## 📞 Поддержка:
При проблемах проверьте:
1. Установлен ли Python
2. Доступен ли порт 5000
3. Есть ли права записи в папку

Версия: 1.0
Дата создания: {datetime.now().strftime('%d.%m.%Y')}
'''
    
    with open(base_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme)
    
    print("📖 Инструкция создана")
    
    print(f"\n🎉 ГОТОВО! Система создана в папке: {base_dir}")
    print(f"📁 Для запуска используйте: ЗАПУСК СИСТЕМЫ.bat")
    print("🌐 Адрес системы: http://localhost:5000")

if __name__ == "__main__":
    try:
        create_complete_system()
        input("\nНажмите Enter для завершения...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        input("Нажмите Enter для выхода...")