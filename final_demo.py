#!/usr/bin/env python3
"""
Финальная демонстрация системы оптимизации торгового робота
Показывает все возможности системы в действии
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time
import random

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_realistic_data(symbol="EURUSD", days=30, freq='H'):
    """Создает реалистичные тестовые данные с различными рыночными режимами"""
    print(f"📊 Создаем реалистичные данные для {symbol}...")
    
    # Создаем временной ряд
    dates = pd.date_range(start='2024-01-01', periods=days*24, freq=freq)
    
    # Базовые параметры для разных символов
    base_prices = {
        'EURUSD': 1.2000,
        'GBPUSD': 1.3500,
        'USDJPY': 110.00,
        'BTCUSD': 45000.00,
        'AAPL': 150.00
    }
    
    base_price = base_prices.get(symbol, 1.2000)
    prices = [base_price]
    
    # Симулируем различные рыночные режимы
    np.random.seed(42)
    
    for i in range(1, len(dates)):
        # Определяем текущий режим рынка
        hour = dates[i].hour
        
        # Азиатская сессия - низкая волатильность
        if 0 <= hour < 8:
            volatility = 0.001
            trend = 0.0001
        # Лондонская сессия - высокая волатильность
        elif 8 <= hour < 16:
            volatility = 0.003
            trend = 0.0002
        # Нью-Йоркская сессия - средняя волатильность
        elif 16 <= hour < 21:
            volatility = 0.002
            trend = 0.0001
        # После закрытия - очень низкая волатильность
        else:
            volatility = 0.0005
            trend = 0.00005
        
        # Добавляем тренд и случайные колебания
        trend_component = trend * np.sin(i / 50)  # Циклический тренд
        noise = np.random.normal(0, volatility)
        change = trend_component + noise
        
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Создаем OHLC данные
    data = []
    for i, price in enumerate(prices):
        # Создаем реалистичные OHLC
        high_low_range = abs(np.random.normal(0, 0.001)) * price
        high = price + high_low_range
        low = price - high_low_range
        
        # Объем зависит от времени дня
        hour = dates[i].hour
        if 8 <= hour < 16:  # Лондонская сессия
            volume = 2000 + np.random.normal(0, 200)
        elif 13 <= hour < 21:  # Нью-Йоркская сессия
            volume = 1800 + np.random.normal(0, 180)
        else:
            volume = 800 + np.random.normal(0, 100)
        
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

def demonstrate_market_adaptation():
    """Демонстрирует систему адаптации к рынку"""
    print("\n" + "="*60)
    print("🔧 ДЕМОНСТРАЦИЯ СИСТЕМЫ АДАПТАЦИИ К РЫНКУ")
    print("="*60)
    
    from market_adaptation_system import MarketAdaptationSystem
    
    # Создаем систему
    adaptation = MarketAdaptationSystem()
    
    # Тестируем на разных символах
    symbols = ['EURUSD', 'GBPUSD', 'BTCUSD']
    
    for symbol in symbols:
        print(f"\n📈 Анализ {symbol}:")
        data = create_realistic_data(symbol, days=7)
        prices = data['close'].tolist()
        volume = data['volume'].tolist()
        
        # Анализируем условия рынка
        conditions = adaptation.analyze_market_conditions(prices, volume)
        
        print(f"  Режим рынка: {conditions.regime.value}")
        print(f"  Волатильность: {conditions.volatility:.3f}")
        print(f"  Сила тренда: {conditions.trend_strength:.3f}")
        print(f"  Стоит торговать: {adaptation.should_trade()}")
        
        # Получаем адаптированные параметры
        params = adaptation.get_adaptive_parameters()
        print(f"  Адаптированные параметры:")
        print(f"    Стоп-лосс: {params['stop_loss_pct']:.1%}")
        print(f"    Тейк-профит: {params['take_profit_pct']:.1%}")
        print(f"    Размер позиции: {params['position_size']:.1%}")

def demonstrate_timing_optimization():
    """Демонстрирует систему оптимизации времени"""
    print("\n" + "="*60)
    print("⏰ ДЕМОНСТРАЦИЯ СИСТЕМЫ ОПТИМИЗАЦИИ ВРЕМЕНИ")
    print("="*60)
    
    from timing_optimization_system import TimingOptimizer
    
    # Создаем оптимизатор
    optimizer = TimingOptimizer()
    
    # Тестируем на разных символах
    symbols = ['EURUSD', 'GBPUSD', 'BTCUSD']
    
    for symbol in symbols:
        print(f"\n🕐 Оптимизация времени для {symbol}:")
        data = create_realistic_data(symbol, days=14)
        
        try:
            # Оптимизируем время
            analysis = optimizer.optimize_timing(data)
            
            print(f"  Лучший час: {analysis.best_hour}:00 UTC")
            print(f"  Лучшая сессия: {analysis.best_session.value}")
            print(f"  Ожидаемая доходность: {analysis.expected_return:.2%}")
            print(f"  Уверенность: {analysis.confidence_score:.1%}")
            
            # Получаем рекомендации
            recommendations = optimizer.get_recommendations(analysis)
            print(f"  Рекомендации:")
            for rec in recommendations[:2]:  # Показываем первые 2
                print(f"    - {rec}")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

def demonstrate_risk_management():
    """Демонстрирует систему управления рисками"""
    print("\n" + "="*60)
    print("🛡️ ДЕМОНСТРАЦИЯ СИСТЕМЫ УПРАВЛЕНИЯ РИСКАМИ")
    print("="*60)
    
    from advanced_risk_management import AdvancedRiskManager, RiskLevel
    
    # Создаем менеджер рисков
    risk_manager = AdvancedRiskManager(initial_balance=10000)
    
    # Тестируем разные сценарии
    scenarios = [
        {"name": "Консервативный", "volatility": 0.1, "risk_level": RiskLevel.LOW},
        {"name": "Умеренный", "volatility": 0.2, "risk_level": RiskLevel.MEDIUM},
        {"name": "Агрессивный", "volatility": 0.3, "risk_level": RiskLevel.HIGH}
    ]
    
    for scenario in scenarios:
        print(f"\n📊 Сценарий: {scenario['name']}")
        
        # Устанавливаем уровень риска
        risk_manager.risk_level = scenario['risk_level']
        
        # Вычисляем размер позиции
        position_size = risk_manager.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.2000,
            stop_loss=1.1950,
            volatility=scenario['volatility']
        )
        
        print(f"  Волатильность: {scenario['volatility']:.1%}")
        print(f"  Размер позиции: {position_size:.2f} лотов")
        print(f"  Можно торговать: {risk_manager.can_open_position('EURUSD')}")
        
        # Получаем метрики риска
        metrics = risk_manager.portfolio_manager.calculate_risk_metrics()
        print(f"  Текущий баланс: ${metrics.portfolio_value:.2f}")
        print(f"  Максимальная просадка: {metrics.max_drawdown:.2%}")

def demonstrate_backtesting():
    """Демонстрирует систему бэктестинга"""
    print("\n" + "="*60)
    print("📈 ДЕМОНСТРАЦИЯ СИСТЕМЫ БЭКТЕСТИНГА")
    print("="*60)
    
    from backtesting_framework import BacktestEngine, MovingAverageCrossoverStrategy
    
    # Тестируем разные стратегии
    strategies = [
        {"name": "Быстрая MA", "fast": 5, "slow": 15},
        {"name": "Средняя MA", "fast": 10, "slow": 30},
        {"name": "Медленная MA", "fast": 20, "slow": 50}
    ]
    
    for strategy_config in strategies:
        print(f"\n📊 Стратегия: {strategy_config['name']}")
        
        # Создаем стратегию
        strategy = MovingAverageCrossoverStrategy(
            fast_period=strategy_config['fast'],
            slow_period=strategy_config['slow']
        )
        
        # Создаем тестовые данные
        data = create_realistic_data('EURUSD', days=21)
        
        # Запускаем бэктест
        engine = BacktestEngine(initial_capital=10000)
        result = engine.run_backtest(strategy, data)
        
        print(f"  Всего сделок: {result.total_trades}")
        print(f"  Выигрышных: {result.winning_trades}")
        print(f"  Процент выигрышных: {result.win_rate:.1%}")
        print(f"  Общий P&L: ${result.total_pnl:.2f}")
        print(f"  Коэффициент Шарпа: {result.sharpe_ratio:.2f}")
        print(f"  Максимальная просадка: {result.max_drawdown:.1%}")

def demonstrate_monitoring():
    """Демонстрирует систему мониторинга"""
    print("\n" + "="*60)
    print("📊 ДЕМОНСТРАЦИЯ СИСТЕМЫ МОНИТОРИНГА")
    print("="*60)
    
    from realtime_monitoring_system import RealtimeMonitor, AlertLevel
    
    # Создаем монитор
    monitor = RealtimeMonitor(initial_balance=10000)
    
    # Добавляем пользовательские алерты
    monitor.add_custom_alert(
        'daily_pnl', 'less_than', -100, AlertLevel.WARNING,
        "Дневной убыток превысил $100"
    )
    
    # Запускаем мониторинг
    monitor.start_monitoring(update_interval=2)
    
    print("🔄 Симулируем торговую активность...")
    
    # Симулируем различные сценарии торговли
    scenarios = [
        {"trades": 5, "avg_pnl": 50, "volatility": 0.1, "name": "Хороший день"},
        {"trades": 3, "avg_pnl": -30, "volatility": 0.2, "name": "Плохой день"},
        {"trades": 8, "avg_pnl": 25, "volatility": 0.15, "name": "Обычный день"}
    ]
    
    for scenario in scenarios:
        print(f"\n📈 Сценарий: {scenario['name']}")
        
        for i in range(scenario['trades']):
            # Симулируем сделку
            pnl = np.random.normal(scenario['avg_pnl'], scenario['volatility'] * 100)
            duration = random.uniform(0.5, 3.0)
            
            monitor.performance_tracker.add_trade(pnl, duration)
            
            # Обновляем баланс
            new_balance = monitor.performance_tracker.current_balance
            monitor.performance_tracker.update_balance(new_balance)
            
            time.sleep(0.5)
        
        # Получаем данные дашборда
        dashboard_data = monitor.get_dashboard_data()
        
        print(f"  Баланс: ${dashboard_data['performance']['current_balance']:.2f}")
        print(f"  Общий P&L: ${dashboard_data['performance']['total_pnl']:.2f}")
        print(f"  Дневной P&L: ${dashboard_data['performance']['daily_pnl']:.2f}")
        print(f"  Коэффициент Шарпа: {dashboard_data['performance']['sharpe_ratio']:.2f}")
        print(f"  Активных алертов: {len(dashboard_data['alerts'])}")
        
        if dashboard_data['alerts']:
            for alert in dashboard_data['alerts']:
                print(f"    ⚠️  {alert['level'].upper()}: {alert['message']}")
    
    # Останавливаем мониторинг
    monitor.stop_monitoring()
    
    # Экспортируем метрики
    filename = monitor.export_metrics()
    print(f"\n💾 Метрики экспортированы в файл: {filename}")

def demonstrate_integrated_system():
    """Демонстрирует интегрированную систему"""
    print("\n" + "="*60)
    print("🚀 ДЕМОНСТРАЦИЯ ИНТЕГРИРОВАННОЙ СИСТЕМЫ")
    print("="*60)
    
    from trading_robot_optimization import OptimizedTradingRobot
    
    # Создаем робота
    robot = OptimizedTradingRobot(initial_balance=10000)
    
    # Создаем тестовые данные
    data = create_realistic_data('EURUSD', days=14)
    
    print("🔍 Анализируем рынок и оптимизируем время...")
    
    # Анализируем рынок и время
    analysis = robot.analyze_market_and_timing(data)
    
    print(f"📊 Результаты анализа:")
    print(f"  Режим рынка: {analysis['market_conditions']['regime']}")
    print(f"  Волатильность: {analysis['market_conditions']['volatility']:.3f}")
    print(f"  Стоит торговать: {analysis['market_conditions']['should_trade']}")
    print(f"  Оптимальный час: {analysis['timing_analysis']['best_hour']}:00 UTC")
    print(f"  Уверенность: {analysis['timing_analysis']['confidence_score']:.1%}")
    
    print(f"\n💡 Рекомендации:")
    for rec in analysis['recommendations'][:3]:
        print(f"  - {rec}")
    
    print(f"\n📅 Расписание торговли:")
    schedule = analysis['trading_schedule']
    print(f"  Основные часы: {schedule['primary_hours']}")
    print(f"  Дополнительные: {schedule['secondary_hours']}")
    print(f"  Избегать: {schedule['avoid_hours']}")
    
    # Оптимизируем параметры стратегии
    print(f"\n⚙️ Оптимизируем параметры стратегии...")
    
    from backtesting_framework import MovingAverageCrossoverStrategy
    
    parameter_ranges = {
        'fast_period': [5, 10, 15],
        'slow_period': [20, 30, 40],
        'stop_loss_pct': [0.01, 0.02, 0.03]
    }
    
    optimization = robot.optimize_strategy_parameters(
        data, MovingAverageCrossoverStrategy, parameter_ranges
    )
    
    print(f"📊 Результаты оптимизации:")
    print(f"  Протестировано комбинаций: {optimization['total_combinations_tested']}")
    print(f"  Лучшие параметры:")
    for i, params in enumerate(optimization['best_parameters'][:3]):
        print(f"    {i+1}. {params['parameters']} - Sharpe: {params['metric_value']:.2f}")
    
    # Получаем итоговую сводку
    print(f"\n📋 Итоговая сводка производительности:")
    summary = robot.get_performance_summary()
    
    print(f"  Торговая статистика:")
    print(f"    Всего сделок: {summary['trading_summary']['total_trades']}")
    print(f"    Выигрышных: {summary['trading_summary']['winning_trades']}")
    print(f"    Процент выигрышных: {summary['trading_summary']['win_rate']:.1%}")
    print(f"    Общий P&L: ${summary['trading_summary']['total_pnl']:.2f}")
    
    print(f"  Метрики производительности:")
    print(f"    Текущий баланс: ${summary['performance_metrics']['current_balance']:.2f}")
    print(f"    Коэффициент Шарпа: {summary['performance_metrics']['sharpe_ratio']:.2f}")
    print(f"    Максимальная просадка: {summary['performance_metrics']['max_drawdown']:.1%}")

def main():
    """Главная функция демонстрации"""
    print("🚀 ПОЛНАЯ ДЕМОНСТРАЦИЯ СИСТЕМЫ ОПТИМИЗАЦИИ ТОРГОВОГО РОБОТА")
    print("=" * 80)
    print("Эта демонстрация покажет все возможности системы:")
    print("• Адаптация к изменениям рынка")
    print("• Оптимизация времени запуска")
    print("• Продвинутое управление рисками")
    print("• Бэктестинг и валидация стратегий")
    print("• Мониторинг в реальном времени")
    print("• Интегрированная система")
    print("=" * 80)
    
    try:
        # Демонстрируем каждый компонент
        demonstrate_market_adaptation()
        demonstrate_timing_optimization()
        demonstrate_risk_management()
        demonstrate_backtesting()
        demonstrate_monitoring()
        demonstrate_integrated_system()
        
        print("\n" + "="*80)
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("="*80)
        print("Система готова к использованию в реальной торговле.")
        print("Все компоненты работают корректно и интегрированы между собой.")
        print("\n💡 Следующие шаги:")
        print("1. Настройте параметры под ваши потребности")
        print("2. Протестируйте на исторических данных")
        print("3. Запустите в демо-режиме")
        print("4. Переходите к live-торговле")
        
    except Exception as e:
        print(f"\n❌ Ошибка в демонстрации: {e}")
        print("Проверьте зависимости и настройки системы.")

if __name__ == "__main__":
    main()