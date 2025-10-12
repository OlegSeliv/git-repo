# Создатель EXE файла для системы контрактов

import os
import sys
import subprocess
from pathlib import Path

def create_exe():
    """Создание EXE файла из Python приложения"""
    
    print("🔨 СОЗДАНИЕ EXE-ФАЙЛА")
    print("=" * 50)
    
    # Проверяем, что все файлы на месте
    required_files = [
        "app.py",
        "requirements.txt", 
        "database_schema.sql"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Отсутствуют файлы:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nСначала запустите УСТАНОВЩИК.py")
        return False
    
    print("✅ Все необходимые файлы найдены")
    
    # Устанавливаем PyInstaller
    print("\n📦 Установка PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                      check=True, capture_output=True)
        print("✅ PyInstaller установлен")
    except subprocess.CalledProcessError:
        print("❌ Ошибка установки PyInstaller")
        return False
    
    # Создаем spec файл для лучшей конфигурации
    print("\n🔧 Создание конфигурации...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('database_schema.sql', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'flask',
        'sqlite3',
        'sqlalchemy',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'markupsafe',
        'pandas',
        'numpy',
        'reportlab',
        'PIL',
        'cv2',
        'matplotlib',
        'seaborn'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Система_Управления_Контрактами',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open("contract_system.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print("✅ Конфигурация создана")
    
    # Компилируем в EXE
    print("\n⚡ Компиляция в EXE (может занять несколько минут)...")
    print("   Не закрывайте это окно!")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "contract_system.spec"
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("\n✅ EXE файл создан успешно!")
            
            # Проверяем результат
            exe_path = Path("dist/Система_Управления_Контрактами.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024*1024)
                print(f"📁 Файл: {exe_path}")
                print(f"📏 Размер: {size_mb:.1f} МБ")
                
                # Создаем bat файл для запуска EXE
                bat_content = f'''@echo off
title Система управления контрактами
cd /d "{exe_path.parent.absolute()}"
start "Система контрактов" "{exe_path.name}"
echo.
echo Система запущена!
echo Откройте браузер: http://localhost:5000
echo Логин: admin, Пароль: admin123
echo.
pause
'''
                
                bat_path = Path("Запуск EXE системы.bat")
                with open(bat_path, "w", encoding="cp1251") as f:
                    f.write(bat_content)
                
                print(f"✅ Создан файл запуска: {bat_path}")
                
                print("\n🎉 ГОТОВО!")
                print("=" * 50)
                print("Для запуска системы:")
                print(f"1. Запустите: {bat_path}")
                print("2. Или двойной щелчок по EXE файлу")
                print("3. Откройте браузер: http://localhost:5000")
                print("4. Логин: admin / admin123")
                
                return True
            else:
                print("❌ EXE файл не найден после компиляции")
                return False
        else:
            print("❌ Ошибка компиляции:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Таймаут при создании EXE (процесс слишком долгий)")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def create_portable_version():
    """Создание портативной версии"""
    
    print("\n📦 Создание портативной версии...")
    
    # Создаем папку для портативной версии
    portable_dir = Path("CONTRACT_SYSTEM_PORTABLE")
    portable_dir.mkdir(exist_ok=True)
    
    # Копируем все необходимые файлы
    import shutil
    
    files_to_copy = [
        "app.py",
        "database_schema.sql", 
        "document_generator.py",
        "document_storage.py",
        "analytics_reporting.py",
        "mobile_app.py",
        "windows_app.py",
        "requirements.txt",
        "setup.py"
    ]
    
    dirs_to_copy = ["templates", "static"]
    
    # Копируем файлы
    for file in files_to_copy:
        if Path(file).exists():
            shutil.copy2(file, portable_dir / file)
    
    # Копируем папки
    for dir_name in dirs_to_copy:
        if Path(dir_name).exists():
            shutil.copytree(dir_name, portable_dir / dir_name, dirs_exist_ok=True)
    
    # Создаем запускатель для портативной версии
    launcher_content = '''@echo off
title Система управления контрактами (Портативная)
echo.
echo ================================================
echo    ПОРТАТИВНАЯ СИСТЕМА УПРАВЛЕНИЯ КОНТРАКТАМИ
echo ================================================
echo.

REM Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен!
    echo.
    echo Для портативной версии нужен установленный Python
    echo Скачайте с https://python.org
    echo.
    pause
    exit /b 1
)

echo Устанавливаем зависимости...
pip install -q -r requirements.txt

if errorlevel 1 (
    echo Ошибка установки зависимостей
    pause
    exit /b 1
)

echo.
echo Инициализация системы...
python setup.py

echo.
echo Запуск системы...
echo Откройте браузер: http://localhost:5000
echo Логин: admin / Пароль: admin123
echo.

python app.py

pause
'''
    
    with open(portable_dir / "ЗАПУСК.bat", "w", encoding="cp1251") as f:
        f.write(launcher_content)
    
    # Создаем README для портативной версии
    readme_content = '''# ПОРТАТИВНАЯ СИСТЕМА УПРАВЛЕНИЯ КОНТРАКТАМИ

## 🚀 Быстрый запуск:
1. Дважды щелкните ЗАПУСК.bat
2. Дождитесь установки зависимостей
3. Откройте http://localhost:5000
4. Логин: admin / admin123

## 📋 Требования:
- Python 3.8+ (должен быть установлен в системе)
- Интернет для первого запуска (установка библиотек)

## 📁 Что включено:
- Полная веб-система управления
- Мобильное приложение (mobile_app.py)  
- Desktop приложение (windows_app.py)
- Генератор документов
- Система аналитики
- Все шаблоны и стили

## 🔧 Настройка:
- Все данные сохраняются в этой папке
- Можно копировать на флешку
- Не требует установки в систему
'''
    
    with open(portable_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"✅ Портативная версия создана: {portable_dir}")
    print(f"   Для запуска используйте: {portable_dir}/ЗАПУСК.bat")

def main():
    print("🏗️  СОЗДАТЕЛЬ ИСПОЛНЯЕМЫХ ФАЙЛОВ")
    print("=" * 60)
    print()
    print("Выберите вариант:")
    print("1. Создать EXE файл (не требует Python на других ПК)")
    print("2. Создать портативную версию (требует Python)")
    print("3. Создать оба варианта")
    print()
    
    choice = input("Ваш выбор (1-3): ").strip()
    
    if choice == "1":
        create_exe()
    elif choice == "2":
        create_portable_version()
    elif choice == "3":
        print("📦 Создаем EXE файл...")
        exe_success = create_exe()
        
        print("\n" + "="*50)
        print("📦 Создаем портативную версию...")
        create_portable_version()
        
        print("\n🎉 ОБА ВАРИАНТА СОЗДАНЫ!")
        if exe_success:
            print("✅ EXE: готов к использованию")
        print("✅ Портативная версия: готова к копированию")
        
    else:
        print("❌ Неверный выбор")
    
    print("\nНажмите Enter для выхода...")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Прервано пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        input("Нажмите Enter для выхода...")