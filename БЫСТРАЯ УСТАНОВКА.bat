@echo off
echo ====================================================
echo    СИСТЕМА УПРАВЛЕНИЯ СЕРВИСНЫМИ КОНТРАКТАМИ
echo    Быстрый установщик
echo ====================================================
echo.

echo Проверяем Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo.
    echo Скачайте и установите Python с https://python.org
    echo При установке обязательно отметьте "Add to PATH"
    echo.
    pause
    exit /b 1
)

echo ✓ Python найден

echo.
echo Запускаем автоматический установщик...
echo.

python УСТАНОВЩИК.py

if errorlevel 1 (
    echo.
    echo ОШИБКА установки!
    echo Попробуйте запустить от имени администратора
    echo.
) else (
    echo.
    echo ✓ Установка завершена успешно!
    echo.
)

pause