@echo off
chcp 65001 >nul
echo ============================================
echo   Система управления сервисными контрактами
echo ============================================
echo.
echo Запуск сервера...
echo.

REM Проверка установки Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не установлен!
    echo Пожалуйста, установите Python с https://python.org
    pause
    exit /b 1
)

REM Проверка зависимостей
echo Проверка зависимостей...
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo Установка зависимостей...
    python -m pip install -r requirements.txt
)

REM Запуск backend сервера
echo.
echo Запуск API сервера...
echo.
echo Сервер будет доступен по адресу: http://localhost:8000
echo Интерфейс откроется автоматически в браузере
echo.
echo Для остановки нажмите Ctrl+C
echo.

REM Открыть браузер через 2 секунды
timeout /t 2 /nobreak >nul
start http://localhost:8000

REM Запустить сервер
python -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload

pause
