#!/usr/bin/env python3
"""
Быстрый тест системы оптимизации торгового робота
Демонстрирует основные возможности без сложной настройки
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_data(days=7, freq='H'):
    """Создает тестовые данные для демонстрации"""
    print("📊 Создаем тестовые данные...")
    
    # Создаем временной ряд
    dates = pd.date_range(start='2024-01-01', periods=days*24, freq=freq)
    
    # Симулируем ценовое движение с трендом и волатильностью
    np.random.seed(42)
    base_price = 1.2000
    prices = [base_price]
    
    for i in range(1, len(dates)):
        # Добавляем тренд и случайные колебания
        trend = 0.0001 * np.sin(i / 100)  # Слабый тренд
        noise = np.random.normal(0, 0.002)  # Случайные колебания
        change = trend + noise
        
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Создаем OHLC данные
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.001)))
        low = price * (1 - abs(np.random.normal(0, 0.001)))
        volume = 1000 + np.random.normal(0, 100)
        
        data.append({
            'timestamp': dates[i],
            'open': prices[i-1] if i > 0 else price,
            'high': high,
            'low': low,
            'close': price,
            'volume': max(100, volume)
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    print(f"✅ Создано {len(df)} записей данных")
    return df

def test_market_adaptation():
    """Тестирует систему адаптации к рынку"""
    print("\n🔧 Тестируем систему адаптации к рынку...")
    
    try:
        from market_adaptation_system import MarketAdaptationSystem
        
        # Создаем систему
        adaptation = MarketAdaptationSystem()
        
        # Создаем тестовые данные
        data = create_test_data(days=3)
        prices = data['close'].tolist()
        volume = data['volume'].tolist()
        
        # Анализируем условия рынка
        conditions = adaptation.analyze_market_conditions(prices, volume)
        
        print(f"  📈 Режим рынка: {conditions.regime.value}")
        print(f"  📊 Волатильность: {conditions.volatility:.3f}")
        print(f"  📉 Сила тренда: {conditions.trend_strength:.3f}")
        print(f"  ✅ Стоит торговать: {adaptation.should_trade()}")
        
        # Получаем адаптированные параметры
        params = adaptation.get_adaptive_parameters()
        print(f"  ⚙️  Адаптированные параметры:")
        for key, value in params.items():
            print(f"      {key}: {value}")
        
        print("✅ Тест адаптации к рынку пройден")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте адаптации: {e}")
        return False

def test_timing_optimization():
    """Тестирует систему оптимизации времени"""
    print("\n⏰ Тестируем систему оптимизации времени...")
    
    try:
        from timing_optimization_system import TimingOptimizer
        
        # Создаем оптимизатор
        optimizer = TimingOptimizer()
        
        # Создаем тестовые данные
        data = create_test_data(days=14)
        
        # Оптимизируем время
        analysis = optimizer.optimize_timing(data)
        
        print(f"  🕐 Лучший час: {analysis.best_hour}:00 UTC")
        print(f"  🌍 Лучшая сессия: {analysis.best_session.value}")
        print(f"  📊 Ожидаемая доходность: {analysis.expected_return:.2%}")
        print(f"  🎯 Уверенность: {analysis.confidence_score:.1%}")
        
        # Получаем расписание
        schedule = optimizer.get_trading_schedule(analysis)
        print(f"  📅 Расписание торговли:")
        print(f"      Основные часы: {schedule['primary_hours']}")
        print(f"      Дополнительные: {schedule['secondary_hours']}")
        print(f"      Избегать: {schedule['avoid_hours']}")
        
        # Получаем рекомендации
        recommendations = optimizer.get_recommendations(analysis)
        print(f"  💡 Рекомендации:")
        for rec in recommendations[:3]:  # Показываем первые 3
            print(f"      - {rec}")
        
        print("✅ Тест оптимизации времени пройден")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте оптимизации времени: {e}")
        return False

def test_risk_management():
    """Тестирует систему управления рисками"""
    print("\n🛡️ Тестируем систему управления рисками...")
    
    try:
        from advanced_risk_management import AdvancedRiskManager, RiskLevel
        
        # Создаем менеджер рисков
        risk_manager = AdvancedRiskManager(initial_balance=10000)
        
        # Тестируем расчет размера позиции
        position_size = risk_manager.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.2000,
            stop_loss=1.1950,
            volatility=0.15
        )
        
        print(f"  💰 Размер позиции: {position_size:.2f} лотов")
        
        # Проверяем возможность торговли
        can_trade = risk_manager.can_open_position("EURUSD")
        print(f"  ✅ Можно торговать: {can_trade}")
        
        # Получаем метрики риска
        metrics = risk_manager.portfolio_manager.calculate_risk_metrics()
        print(f"  📊 Метрики риска:")
        print(f"      Текущий баланс: ${metrics.portfolio_value:.2f}")
        print(f"      Максимальная просадка: {metrics.max_drawdown:.2%}")
        print(f"      Коэффициент Шарпа: {metrics.sharpe_ratio:.2f}")
        
        print("✅ Тест управления рисками пройден")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте управления рисками: {e}")
        return False

def test_backtesting():
    """Тестирует систему бэктестинга"""
    print("\n📈 Тестируем систему бэктестинга...")
    
    try:
        from backtesting_framework import BacktestEngine, MovingAverageCrossoverStrategy
        
        # Создаем стратегию
        strategy = MovingAverageCrossoverStrategy(fast_period=5, slow_period=15)
        
        # Создаем тестовые данные
        data = create_test_data(days=10)
        
        # Запускаем бэктест
        engine = BacktestEngine(initial_capital=10000)
        result = engine.run_backtest(strategy, data)
        
        print(f"  📊 Результаты бэктестинга:")
        print(f"      Всего сделок: {result.total_trades}")
        print(f"      Выигрышных: {result.winning_trades}")
        print(f"      Процент выигрышных: {result.win_rate:.1%}")
        print(f"      Общий P&L: ${result.total_pnl:.2f}")
        print(f"      Коэффициент Шарпа: {result.sharpe_ratio:.2f}")
        print(f"      Максимальная просадка: {result.max_drawdown:.1%}")
        print(f"      Profit Factor: {result.profit_factor:.2f}")
        
        print("✅ Тест бэктестинга пройден")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте бэктестинга: {e}")
        return False

def test_monitoring():
    """Тестирует систему мониторинга"""
    print("\n📊 Тестируем систему мониторинга...")
    
    try:
        from realtime_monitoring_system import RealtimeMonitor, AlertLevel
        
        # Создаем монитор
        monitor = RealtimeMonitor(initial_balance=10000)
        
        # Запускаем мониторинг
        monitor.start_monitoring(update_interval=1)
        
        # Симулируем торговую активность
        import random
        import time
        
        print("  🔄 Симулируем торговую активность...")
        for i in range(5):
            # Симулируем сделку
            trade_pnl = random.uniform(-50, 100)
            monitor.performance_tracker.add_trade(trade_pnl, random.uniform(0.5, 2.0))
            
            # Обновляем баланс
            new_balance = monitor.performance_tracker.current_balance
            monitor.performance_tracker.update_balance(new_balance)
            
            time.sleep(0.5)
        
        # Получаем данные дашборда
        dashboard_data = monitor.get_dashboard_data()
        
        print(f"  📊 Данные дашборда:")
        print(f"      Текущий баланс: ${dashboard_data['performance']['current_balance']:.2f}")
        print(f"      Общий P&L: ${dashboard_data['performance']['total_pnl']:.2f}")
        print(f"      Дневной P&L: ${dashboard_data['performance']['daily_pnl']:.2f}")
        print(f"      Коэффициент Шарпа: {dashboard_data['performance']['sharpe_ratio']:.2f}")
        print(f"      Активных алертов: {len(dashboard_data['alerts'])}")
        
        # Останавливаем мониторинг
        monitor.stop_monitoring()
        
        print("✅ Тест мониторинга пройден")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте мониторинга: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🚀 БЫСТРЫЙ ТЕСТ СИСТЕМЫ ОПТИМИЗАЦИИ ТОРГОВОГО РОБОТА")
    print("=" * 60)
    
    # Список тестов
    tests = [
        ("Адаптация к рынку", test_market_adaptation),
        ("Оптимизация времени", test_timing_optimization),
        ("Управление рисками", test_risk_management),
        ("Бэктестинг", test_backtesting),
        ("Мониторинг", test_monitoring)
    ]
    
    # Результаты тестов
    results = []
    
    # Запускаем тесты
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name.upper()} {'='*20}")
        success = test_func()
        results.append((test_name, success))
    
    # Выводим итоги
    print(f"\n{'='*60}")
    print("📋 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n📊 Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно! Система готова к использованию.")
    else:
        print("⚠️  Некоторые тесты провалены. Проверьте зависимости и настройки.")
    
    print("\n💡 Для полной демонстрации запустите: python trading_robot_optimization.py")

if __name__ == "__main__":
    main()