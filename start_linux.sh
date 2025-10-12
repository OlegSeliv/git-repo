#!/bin/bash

echo "============================================"
echo "  Система управления сервисными контрактами"
echo "============================================"
echo ""
echo "Запуск сервера..."
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python 3 не установлен!"
    echo "Установите Python 3: sudo apt install python3 python3-pip"
    exit 1
fi

# Проверка зависимостей
echo "Проверка зависимостей..."
python3 -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Установка зависимостей..."
    python3 -m pip install -r requirements.txt
fi

# Запуск сервера
echo ""
echo "Запуск API сервера..."
echo ""
echo "Сервер будет доступен по адресу: http://localhost:8000"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

# Открыть браузер
sleep 2
xdg-open http://localhost:8000 2>/dev/null &

# Запустить сервер
python3 -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
