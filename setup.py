# Установочный скрипт для системы управления сервисными контрактами

import os
import subprocess
import sys
from pathlib import Path
import sqlite3
from datetime import datetime

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        print("Ошибка: Требуется Python 3.8 или выше")
        print(f"Текущая версия: {sys.version}")
        return False
    return True

def install_requirements():
    """Установка зависимостей"""
    print("Установка зависимостей...")
    
    requirements = [
        "Flask==3.0.0",
        "SQLAlchemy==2.0.23",
        "Flask-SQLAlchemy==3.1.1",
        "Flask-Login==0.6.3",
        "Werkzeug==3.0.1",
        "python-dotenv==1.0.0",
        "Pillow==10.1.0",
        "reportlab==4.0.7",
        "openpyxl==3.1.2",
        "python-docx==1.1.0",
        "pandas==2.1.4",
        "matplotlib==3.8.2",
        "seaborn==0.13.0",
        "opencv-python==4.8.1.78",
        "pytesseract==0.3.10",
        "requests==2.31.0",
        "numpy==1.24.4"
    ]
    
    for requirement in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", requirement])
            print(f"✓ Установлено: {requirement}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Ошибка установки {requirement}: {e}")
            return False
    
    return True

def create_directories():
    """Создание необходимых директорий"""
    print("Создание директорий...")
    
    directories = [
        "documents",
        "scans", 
        "templates",
        "uploads",
        "reports",
        "backups",
        "logs",
        "static/css",
        "static/js",
        "static/images",
        "templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Создана директория: {directory}")

def initialize_database():
    """Инициализация базы данных"""
    print("Инициализация базы данных...")
    
    try:
        # Выполняем SQL схему
        with open("database_schema.sql", "r", encoding="utf-8") as f:
            schema = f.read()
        
        conn = sqlite3.connect("contract_management.db")
        cursor = conn.cursor()
        
        # Выполняем по частям
        statements = schema.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        conn.commit()
        
        # Добавляем тестовые данные
        add_sample_data(cursor)
        
        conn.commit()
        conn.close()
        
        print("✓ База данных инициализирована")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка инициализации БД: {e}")
        return False

def add_sample_data(cursor):
    """Добавление тестовых данных"""
    print("Добавление тестовых данных...")
    
    # Добавляем пользователя по умолчанию
    from werkzeug.security import generate_password_hash
    
    # Тестовый контракт
    cursor.execute("""
        INSERT INTO contracts (contract_number, contract_name, customer, start_date, end_date, total_amount, advance_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("DEMO-001", "Демонстрационный контракт", "ООО 'Тестовый заказчик'", 
          "2024-01-01", "2024-12-31", 1000000, 300000, "active"))
    
    contract_id = cursor.lastrowid
    
    # Субсчет для контракта
    cursor.execute("""
        INSERT INTO contract_subaccounts (contract_id, account_code, balance, available_amount)
        VALUES (?, ?, ?, ?)
    """, (contract_id, "40702810000000000001", 300000, 250000))
    
    # Тестовый заказ
    cursor.execute("""
        INSERT INTO orders (contract_id, order_number, description, location, region, status, priority, estimated_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (contract_id, "DEMO-001-001", "Демонстрационный заказ на сервисное обслуживание", 
          "Москва", "Московская область", "created", "normal", 150000))
    
    # Тестовые материалы
    materials = [
        ("DEMO-001", "Демонстрационная деталь 1", "Тестовая деталь для демонстрации", "шт", 10, 5, 1000, "ООО 'Поставщик'"),
        ("DEMO-002", "Демонстрационная деталь 2", "Еще одна тестовая деталь", "шт", 3, 10, 2500, "ООО 'Другой поставщик'")
    ]
    
    for material in materials:
        cursor.execute("""
            INSERT INTO materials (part_number, name, description, unit, current_stock, min_stock, price, supplier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, material)
    
    # Тестовый сотрудник
    cursor.execute("""
        INSERT INTO employees (employee_number, full_name, position, department, phone, email, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("EMP-001", "Иванов Иван Иванович", "Инженер", "Сервисный отдел", "+7(495)123-45-67", "ivanov@company.ru", True))
    
    print("✓ Тестовые данные добавлены")

def create_config_file():
    """Создание конфигурационного файла"""
    print("Создание конфигурационного файла...")
    
    config_content = """# Конфигурация системы управления контрактами

# Настройки базы данных
DATABASE_URL=sqlite:///contract_management.db

# Настройки Flask
SECRET_KEY=your-secret-key-change-in-production
DEBUG=False
HOST=0.0.0.0
PORT=5000

# Настройки загрузки файлов
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB

# Настройки документов
DOCUMENTS_FOLDER=documents
SCANS_FOLDER=scans
TEMPLATES_FOLDER=templates

# Настройки OCR
OCR_LANGUAGE=rus+eng
OCR_ENGINE_MODE=3
OCR_PAGE_SEGMENTATION_MODE=6

# Настройки отчетов
REPORTS_FOLDER=reports
BACKUP_FOLDER=backups

# Настройки логирования
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("✓ Конфигурационный файл создан (.env)")

def create_startup_scripts():
    """Создание скриптов запуска"""
    print("Создание скриптов запуска...")
    
    # Windows batch файл
    windows_script = """@echo off
echo Запуск системы управления контрактами...
python app.py
pause
"""
    
    with open("start_windows.bat", "w", encoding="utf-8") as f:
        f.write(windows_script)
    
    # Linux shell скрипт
    linux_script = """#!/bin/bash
echo "Запуск системы управления контрактами..."
python3 app.py
"""
    
    with open("start_linux.sh", "w", encoding="utf-8") as f:
        f.write(linux_script)
    
    # Делаем скрипт исполняемым на Linux
    try:
        os.chmod("start_linux.sh", 0o755)
    except:
        pass
    
    print("✓ Скрипты запуска созданы")

def create_desktop_shortcuts():
    """Создание ярлыков на рабочем столе"""
    print("Создание ярлыков...")
    
    try:
        if sys.platform.startswith('win'):
            # Windows ярлык
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "Система управления контрактами.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = os.path.join(os.getcwd(), "start_windows.bat")
            shortcut.WorkingDirectory = os.getcwd()
            shortcut.IconLocation = os.path.join(os.getcwd(), "static", "images", "icon.ico")
            shortcut.save()
            
            print("✓ Ярлык создан на рабочем столе")
            
    except ImportError:
        print("! Для создания ярлыков на Windows установите: pip install winshell pywin32")
    except Exception as e:
        print(f"! Не удалось создать ярлык: {e}")

def check_tesseract():
    """Проверка установки Tesseract OCR"""
    print("Проверка Tesseract OCR...")
    
    try:
        import pytesseract
        # Попытка найти Tesseract
        tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        
        if not os.path.exists(tesseract_cmd):
            # Поиск в стандартных путях
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✓ Tesseract найден: {path}")
                    return True
            
            print("! Tesseract OCR не найден. Функция сканирования может не работать.")
            print("  Скачайте Tesseract с: https://github.com/UB-Mannheim/tesseract/wiki")
            return False
        else:
            print(f"✓ Tesseract найден: {tesseract_cmd}")
            return True
            
    except ImportError:
        print("! pytesseract не установлен")
        return False

def run_tests():
    """Запуск базовых тестов"""
    print("Выполнение базовых тестов...")
    
    try:
        # Тест подключения к БД
        conn = sqlite3.connect("contract_management.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contracts")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✓ База данных работает (контрактов: {count})")
        
        # Тест импорта модулей
        import flask
        print("✓ Flask импортируется")
        
        import reportlab
        print("✓ ReportLab импортируется")
        
        import pandas
        print("✓ Pandas импортируется")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования: {e}")
        return False

def main():
    """Основная функция установки"""
    print("=" * 60)
    print("УСТАНОВКА СИСТЕМЫ УПРАВЛЕНИЯ СЕРВИСНЫМИ КОНТРАКТАМИ")
    print("=" * 60)
    
    # Проверки
    if not check_python_version():
        return False
    
    print(f"Python версия: {sys.version.split()[0]} ✓")
    
    # Установка
    steps = [
        ("Установка зависимостей", install_requirements),
        ("Создание директорий", create_directories),
        ("Инициализация базы данных", initialize_database),
        ("Создание конфигурации", create_config_file),
        ("Создание скриптов запуска", create_startup_scripts),
        ("Проверка Tesseract OCR", check_tesseract),
        ("Базовое тестирование", run_tests)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        print("-" * 40)
        
        if not step_func():
            print(f"\n✗ ОШИБКА на этапе: {step_name}")
            return False
    
    # Опциональные шаги
    print("\nДополнительные настройки...")
    print("-" * 40)
    create_desktop_shortcuts()
    
    print("\n" + "=" * 60)
    print("УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 60)
    
    print("\nДля запуска системы:")
    print("• Windows: Запустите start_windows.bat")
    print("• Linux/Mac: Запустите start_linux.sh")
    print("• Или выполните: python app.py")
    print("\nПосле запуска откройте в браузере: http://localhost:5000")
    print("Логин по умолчанию: admin / admin123")
    
    print("\nДокументация доступна в файле README.md")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nУстановка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nНепредвиденная ошибка: {e}")
        sys.exit(1)