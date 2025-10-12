"""
Полный пример использования всех компонентов системы
для решения проблем влияния рынка и времени запуска
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from market_neutral_strategy import MarketNeutralStrategy, PositionSizer, MarketNeutralPortfolio
from optimal_launch_time import OptimalLaunchTimeAnalyzer
from backtesting_framework import AdvancedBacktester, BacktestConfig, print_backtest_results


def create_realistic_market_data(days: int = 730) -> pd.DataFrame:
    """
    Создание реалистичных рыночных данных с разными режимами
    """
    np.random.seed(42)
    dates = pd.date_range(start='2022-01-01', periods=days, freq='D')
    
    # Базовая цена с трендом и волатильностью
    base_price = 100
    prices = [base_price]
    
    for i in range(1, days):
        # Разные режимы рынка в разные периоды
        if i < days * 0.3:  # Первые 30% - растущий тренд
            drift = 0.0003
            volatility = 0.01
        elif i < days * 0.6:  # Следующие 30% - боковик
            drift = 0
            volatility = 0.008
        else:  # Последние 40% - высокая волатильность
            drift = -0.0001
            volatility = 0.02
        
        # Добавляем недельную сезонность
        weekday_factor = 1.0 + 0.002 * np.sin(2 * np.pi * i / 7)
        
        # Генерация цены
        change = drift + volatility * np.random.randn() * weekday_factor
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    prices = np.array(prices)
    
    # OHLC данные
    data = {
        'open': prices * (1 + np.random.randn(len(prices)) * 0.002),
        'high': prices * (1 + abs(np.random.randn(len(prices))) * 0.005),
        'low': prices * (1 - abs(np.random.randn(len(prices))) * 0.005),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(prices))
    }
    
    return pd.DataFrame(data, index=dates)


def mean_reversion_strategy(prices: pd.DataFrame, lookback: int = 20, threshold: float = 1.5) -> np.ndarray:
    """
    Стратегия возврата к среднему (Mean Reversion)
    
    Args:
        lookback: Период для расчета среднего
        threshold: Порог отклонения в стандартных отклонениях
    """
    close = prices['close'].values
    signals = np.zeros(len(close))
    
    for i in range(lookback, len(close)):
        # Скользящее среднее и стандартное отклонение
        window = close[i-lookback:i]
        mean = np.mean(window)
        std = np.std(window)
        
        if std == 0:
            continue
        
        # Z-score
        z_score = (close[i] - mean) / std
        
        # Сигналы
        if z_score < -threshold:  # Цена сильно ниже среднего - покупаем
            signals[i] = 1.0
        elif z_score > threshold:  # Цена сильно выше среднего - продаем
            signals[i] = -1.0
        elif abs(z_score) < 0.5:  # Близко к среднему - закрываем позицию
            signals[i] = 0.0
        else:
            signals[i] = signals[i-1]  # Держим текущую позицию
    
    return signals


def momentum_strategy(prices: pd.DataFrame, fast_period: int = 10, slow_period: int = 50) -> np.ndarray:
    """
    Моментум стратегия на основе пересечения скользящих средних
    """
    close = prices['close'].values
    signals = np.zeros(len(close))
    
    if len(close) < slow_period:
        return signals
    
    # Скользящие средние
    fast_ma = pd.Series(close).rolling(fast_period).mean().values
    slow_ma = pd.Series(close).rolling(slow_period).mean().values
    
    for i in range(slow_period, len(close)):
        if fast_ma[i] > slow_ma[i] and fast_ma[i-1] <= slow_ma[i-1]:
            signals[i] = 1.0  # Пересечение вверх - покупаем
        elif fast_ma[i] < slow_ma[i] and fast_ma[i-1] >= slow_ma[i-1]:
            signals[i] = -1.0  # Пересечение вниз - продаем
        elif i > 0:
            signals[i] = signals[i-1]  # Держим позицию
    
    return signals


def main():
    """
    Главный пример использования всей системы
    """
    print("="*80)
    print("КОМПЛЕКСНАЯ СИСТЕМА АНАЛИЗА ТОРГОВОГО РОБОТА")
    print("="*80)
    print("\nРЕШАЕМ ДВЕ ОСНОВНЫЕ ПРОБЛЕМЫ:")
    print("1. Устранение влияния изменений рынка на результаты")
    print("2. Поиск оптимального времени запуска советника")
    print("="*80)
    
    # ===== ШАHG 1: Генерация данных =====
    print("\n\n[ШАHG 1] Генерация реалистичных рыночных данных...")
    prices = create_realistic_market_data(days=730)
    print(f"Создано {len(prices)} дней данных ({prices.index[0]} - {prices.index[-1]})")
    
    # ===== ШАHG 2: Анализ без маркет-нейтральности =====
    print("\n\n[ШАHG 2] Тестирование ОБЫЧНОЙ стратегии (БЕЗ маркет-нейтральности)...")
    print("-" * 80)
    
    config_normal = BacktestConfig(
        initial_capital=10000,
        use_market_neutral=False,
        max_position_size=0.95
    )
    
    backtester_normal = AdvancedBacktester(config_normal)
    result_normal = backtester_normal.run(prices, mean_reversion_strategy)
    
    print("\nРезультаты ОБЫЧНОЙ стратегии:")
    print_backtest_results(result_normal)
    
    # ===== ШАHG 3: Анализ с маркет-нейтральностью =====
    print("\n\n[ШАHG 3] Тестирование МАРКЕТ-НЕЙТРАЛЬНОЙ стратегии...")
    print("-" * 80)
    
    config_neutral = BacktestConfig(
        initial_capital=10000,
        use_market_neutral=True,  # ВКЛЮЧАЕМ маркет-нейтральность
        max_position_size=0.95,
        risk_per_trade=0.02
    )
    
    backtester_neutral = AdvancedBacktester(config_neutral)
    result_neutral = backtester_neutral.run(prices, mean_reversion_strategy)
    
    print("\nРезультаты МАРКЕТ-НЕЙТРАЛЬНОЙ стратегии:")
    print_backtest_results(result_neutral)
    
    # Сравнение
    print("\n\n[СРАВНЕНИЕ] Обычная vs Маркет-Нейтральная:")
    print("-" * 80)
    print(f"{'Метрика':<30} {'Обычная':<20} {'Маркет-Нейтральная':<20} {'Улучшение':<15}")
    print("-" * 80)
    
    metrics = [
        ('Общая доходность', result_normal.total_return, result_neutral.total_return, '%'),
        ('Sharpe Ratio', result_normal.sharpe_ratio, result_neutral.sharpe_ratio, ''),
        ('Макс. просадка', result_normal.max_drawdown, result_neutral.max_drawdown, '%'),
        ('Win Rate', result_normal.win_rate, result_neutral.win_rate, '%'),
    ]
    
    for name, normal_val, neutral_val, unit in metrics:
        if unit == '%':
            normal_str = f"{normal_val*100:.2f}%"
            neutral_str = f"{neutral_val*100:.2f}%"
            improvement = ((neutral_val - normal_val) / abs(normal_val) * 100) if normal_val != 0 else 0
        else:
            normal_str = f"{normal_val:.2f}"
            neutral_str = f"{neutral_val:.2f}"
            improvement = ((neutral_val - normal_val) / abs(normal_val) * 100) if normal_val != 0 else 0
        
        improvement_str = f"{improvement:+.1f}%"
        print(f"{name:<30} {normal_str:<20} {neutral_str:<20} {improvement_str:<15}")
    
    # ===== ШАHG 4: Анализ оптимального времени запуска =====
    print("\n\n[ШАHG 4] Анализ оптимального времени запуска...")
    print("-" * 80)
    
    analyzer = OptimalLaunchTimeAnalyzer(
        lookback_days=365,
        min_trading_days=90,
        step_days=7
    )
    
    print("Анализируем все возможные точки старта (это может занять время)...")
    launch_results = analyzer.analyze_all_start_times(
        prices=prices,
        strategy_func=mean_reversion_strategy,
        initial_capital=10000
    )
    
    print(f"Проанализировано {len(launch_results)} различных точек старта\n")
    
    # Топ-5 лучших времен
    top_launches = analyzer.find_optimal_launch_times(top_n=5)
    
    print("ТОП-5 ЛУЧШИХ ВРЕМЕН ЗАПУСКА:")
    print("-" * 80)
    for i, launch in enumerate(top_launches, 1):
        print(f"\n{i}. Дата запуска: {launch.start_time.strftime('%Y-%m-%d (%A)')}")
        print(f"   Доходность: {launch.total_return*100:+.2f}%")
        print(f"   Sharpe: {launch.sharpe_ratio:.2f}")
        print(f"   Просадка: {launch.max_drawdown*100:.2f}%")
        print(f"   Win Rate: {launch.win_rate*100:.2f}%")
        print(f"   Комплексная оценка: {launch.score:.4f}")
    
    # Топ-5 худших времен
    worst_launches = sorted(launch_results, key=lambda x: x.score)[:5]
    
    print("\n\nТОП-5 ХУДШИХ ВРЕМЕН ЗАПУСКА (для избегания):")
    print("-" * 80)
    for i, launch in enumerate(worst_launches, 1):
        print(f"\n{i}. Дата запуска: {launch.start_time.strftime('%Y-%m-%d (%A)')}")
        print(f"   Доходность: {launch.total_return*100:+.2f}%")
        print(f"   Sharpe: {launch.sharpe_ratio:.2f}")
        print(f"   Просадка: {launch.max_drawdown*100:.2f}%")
        print(f"   Комплексная оценка: {launch.score:.4f}")
    
    # ===== ШАHG 5: Сезонный анализ =====
    print("\n\n[ШАHG 5] Сезонный анализ - лучшие дни и месяцы для запуска...")
    print("-" * 80)
    
    seasonal = analyzer.analyze_seasonal_patterns(launch_results)
    
    if 'weekday' in seasonal:
        print("\nАНАЛИЗ ПО ДНЯМ НЕДЕЛИ:")
        weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        sorted_weekdays = sorted(seasonal['weekday'].items(), key=lambda x: x[1]['avg_score'], reverse=True)
        
        for day, stats in sorted_weekdays:
            print(f"  {weekday_names[day]:<12}: "
                  f"доходность {stats['avg_return']*100:+.2f}%, "
                  f"Sharpe {stats['avg_sharpe']:.2f}, "
                  f"оценка {stats['avg_score']:.4f}")
    
    if 'month' in seasonal:
        print("\nАНАЛИЗ ПО МЕСЯЦАМ:")
        month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                       'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        sorted_months = sorted(seasonal['month'].items(), key=lambda x: x[1]['avg_score'], reverse=True)
        
        for month, stats in sorted_months:
            print(f"  {month_names[month-1]:<12}: "
                  f"доходность {stats['avg_return']*100:+.2f}%, "
                  f"Sharpe {stats['avg_sharpe']:.2f}, "
                  f"оценка {stats['avg_score']:.4f}")
    
    # ===== ШАHG 6: Monte Carlo анализ =====
    print("\n\n[ШАHG 6] Monte Carlo анализ стабильности...")
    print("-" * 80)
    
    mc_results = analyzer.monte_carlo_timing_analysis(
        prices=prices,
        strategy_func=mean_reversion_strategy,
        n_simulations=500
    )
    
    if mc_results:
        print("\nРезультаты 500 случайных точек запуска:")
        print(f"  Средняя доходность: {mc_results['mean_return']*100:.2f}%")
        print(f"  Медианная доходность: {mc_results['median_return']*100:.2f}%")
        print(f"  Std отклонение: {mc_results['std_return']*100:.2f}%")
        print(f"  Диапазон: [{mc_results['min_return']*100:.2f}%, {mc_results['max_return']*100:.2f}%]")
        print(f"  5-й перцентиль (худшие 5%): {mc_results['percentile_5']*100:.2f}%")
        print(f"  95-й перцентиль (лучшие 5%): {mc_results['percentile_95']*100:.2f}%")
        print(f"  Вероятность прибыли: {mc_results['probability_positive']*100:.2f}%")
        
        print(f"\n  ВЫВОД: Разброс результатов от времени запуска: {(mc_results['max_return'] - mc_results['min_return'])*100:.2f}%")
        print(f"         Это показывает, насколько важно выбрать правильное время!")
    
    # ===== ШАHG 7: Рекомендации для текущего момента =====
    print("\n\n[ШАHG 7] Рекомендации для ТЕКУЩЕГО момента...")
    print("-" * 80)
    
    recommendations = analyzer.generate_launch_recommendations(
        prices=prices,
        current_date=datetime.now()
    )
    
    print(f"\nСТАТУС: {recommendations['recommendation'].upper()}")
    print(f"РЕКОМЕНДАЦИЯ: {recommendations['message']}")
    print(f"\nОценка текущего момента: {recommendations.get('composite_score', 0):.4f}")
    print(f"Текущая волатильность рынка: {recommendations.get('current_volatility', 0):.4f}")
    print(f"Текущий RSI: {recommendations.get('current_rsi', 50):.2f}")
    
    if recommendations.get('best_weekdays'):
        print("\nЛучшие дни недели:")
        for day, stats in recommendations['best_weekdays']:
            weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            print(f"  {weekday_names[day]}: оценка {stats['avg_score']:.4f}")
    
    # ===== ФИНАЛЬНЫЕ ВЫВОДЫ =====
    print("\n\n" + "="*80)
    print("ФИНАЛЬНЫЕ ВЫВОДЫ И РЕКОМЕНДАЦИИ")
    print("="*80)
    
    print("\n1. ВЛИЯНИЕ РЫНКА:")
    print(f"   - Маркет-нейтральная стратегия изменила Sharpe с {result_normal.sharpe_ratio:.2f} на {result_neutral.sharpe_ratio:.2f}")
    print(f"   - Просадка изменилась с {result_normal.max_drawdown*100:.2f}% на {result_neutral.max_drawdown*100:.2f}%")
    print("   - Маркет-нейтральность снижает зависимость от общих движений рынка")
    
    print("\n2. ВРЕМЯ ЗАПУСКА:")
    best_score = top_launches[0].score if top_launches else 0
    worst_score = worst_launches[0].score if worst_launches else 0
    print(f"   - Разница между лучшим и худшим временем: {(best_score - worst_score):.4f}")
    print(f"   - Лучшая доходность: {top_launches[0].total_return*100:.2f}% vs худшая: {worst_launches[0].total_return*100:.2f}%")
    print(f"   - Это разница в {abs(top_launches[0].total_return - worst_launches[0].total_return)*100:.2f}% только из-за времени!")
    
    print("\n3. ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ:")
    print("   ✓ Используйте маркет-нейтральные подходы (нормализация, волатильность)")
    print("   ✓ Запускайте робота в благоприятные дни (см. сезонный анализ)")
    print("   ✓ Избегайте запуска в периоды экстремальной волатильности")
    print("   ✓ Используйте динамический sizing позиций")
    print("   ✓ Регулярно мониторьте режим рынка и адаптируйте параметры")
    
    print("\n4. ИНСТРУМЕНТЫ ДЛЯ КОНТРОЛЯ:")
    print("   - market_neutral_strategy.py - для устранения влияния рынка")
    print("   - optimal_launch_time.py - для анализа времени запуска")
    print("   - backtesting_framework.py - для тестирования")
    
    print("\n" + "="*80)
    print("Анализ завершен! Все результаты сохранены.")
    print("="*80)
    
    # Экспорт результатов
    analyzer.export_results('launch_time_analysis_results.json')


if __name__ == "__main__":
    main()
