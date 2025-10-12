"""
Анализатор оптимального времени запуска торгового советника.
Находит наиболее выгодные периоды для начала торговли.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, time
from dataclasses import dataclass
import json


@dataclass
class LaunchTimeResult:
    """Результат анализа времени запуска"""
    start_time: datetime
    end_time: datetime
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    score: float  # Комплексная оценка


class OptimalLaunchTimeAnalyzer:
    """
    Анализатор оптимального времени запуска советника.
    
    Методы:
    1. Walk-Forward анализ - перебор всех возможных точек старта
    2. Сезонный анализ - поиск оптимальных дней недели/месяца
    3. Анализ рыночных условий - старт при определенных условиях
    4. Monte Carlo симуляция - оценка стабильности результатов
    """
    
    def __init__(
        self,
        lookback_days: int = 365,
        min_trading_days: int = 30,
        step_days: int = 1
    ):
        self.lookback_days = lookback_days
        self.min_trading_days = min_trading_days
        self.step_days = step_days
        
        self.results_cache = []
    
    def analyze_all_start_times(
        self,
        prices: pd.DataFrame,
        strategy_func: callable,
        initial_capital: float = 10000
    ) -> List[LaunchTimeResult]:
        """
        Перебор всех возможных времен старта и оценка результатов
        
        Args:
            prices: DataFrame с ценами (index=datetime, columns=['open','high','low','close'])
            strategy_func: Функция стратегии, возвращающая сигналы
            initial_capital: Начальный капитал
            
        Returns:
            Список результатов для каждой точки старта
        """
        results = []
        
        # Перебираем все возможные даты старта
        start_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-self.min_trading_days],
            freq=f'{self.step_days}D'
        )
        
        for start_date in start_dates:
            # Ограничиваем данные от start_date
            subset = prices[prices.index >= start_date]
            
            if len(subset) < self.min_trading_days:
                continue
            
            # Запускаем стратегию
            equity_curve, trades = self._run_strategy(
                subset, 
                strategy_func, 
                initial_capital
            )
            
            # Вычисляем метрики
            metrics = self._calculate_metrics(equity_curve, trades, initial_capital)
            
            result = LaunchTimeResult(
                start_time=start_date,
                end_time=subset.index[-1],
                total_return=metrics['total_return'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown=metrics['max_drawdown'],
                win_rate=metrics['win_rate'],
                num_trades=len(trades),
                score=metrics['score']
            )
            
            results.append(result)
        
        self.results_cache = results
        return results
    
    def find_optimal_launch_times(
        self,
        results: Optional[List[LaunchTimeResult]] = None,
        top_n: int = 10,
        metric: str = 'score'
    ) -> List[LaunchTimeResult]:
        """
        Находит топ-N оптимальных времен запуска
        
        Args:
            results: Список результатов (если None, использует кэш)
            top_n: Количество лучших результатов
            metric: Метрика для сортировки
            
        Returns:
            Топ-N лучших результатов
        """
        if results is None:
            results = self.results_cache
        
        if not results:
            return []
        
        # Сортируем по выбранной метрике
        sorted_results = sorted(
            results,
            key=lambda x: getattr(x, metric),
            reverse=True
        )
        
        return sorted_results[:top_n]
    
    def analyze_seasonal_patterns(
        self,
        results: Optional[List[LaunchTimeResult]] = None
    ) -> Dict[str, Dict]:
        """
        Анализ сезонных паттернов - какие дни недели/месяцы лучше для старта
        
        Returns:
            Словарь с анализом по дням недели, месяцам, кварталам
        """
        if results is None:
            results = self.results_cache
        
        if not results:
            return {}
        
        # Группировка по дню недели
        weekday_performance = {}
        for day in range(7):
            day_results = [r for r in results if r.start_time.weekday() == day]
            if day_results:
                weekday_performance[day] = {
                    'avg_return': np.mean([r.total_return for r in day_results]),
                    'avg_sharpe': np.mean([r.sharpe_ratio for r in day_results]),
                    'avg_score': np.mean([r.score for r in day_results]),
                    'count': len(day_results)
                }
        
        # Группировка по месяцу
        month_performance = {}
        for month in range(1, 13):
            month_results = [r for r in results if r.start_time.month == month]
            if month_results:
                month_performance[month] = {
                    'avg_return': np.mean([r.total_return for r in month_results]),
                    'avg_sharpe': np.mean([r.sharpe_ratio for r in month_results]),
                    'avg_score': np.mean([r.score for r in month_results]),
                    'count': len(month_results)
                }
        
        # Группировка по кварталу
        quarter_performance = {}
        for quarter in range(1, 5):
            quarter_results = [r for r in results if (r.start_time.month - 1) // 3 + 1 == quarter]
            if quarter_results:
                quarter_performance[quarter] = {
                    'avg_return': np.mean([r.total_return for r in quarter_results]),
                    'avg_sharpe': np.mean([r.sharpe_ratio for r in quarter_results]),
                    'avg_score': np.mean([r.score for r in quarter_results]),
                    'count': len(quarter_results)
                }
        
        return {
            'weekday': weekday_performance,
            'month': month_performance,
            'quarter': quarter_performance
        }
    
    def analyze_market_condition_timing(
        self,
        prices: pd.DataFrame,
        results: Optional[List[LaunchTimeResult]] = None
    ) -> Dict[str, any]:
        """
        Анализ оптимальных рыночных условий для запуска
        
        Определяет, при каких условиях запуск дает лучшие результаты:
        - Уровень волатильности
        - Направление тренда
        - RSI уровень
        - Moving average положение
        """
        if results is None:
            results = self.results_cache
        
        if not results or len(prices) < 50:
            return {}
        
        conditions_analysis = {
            'high_volatility_starts': [],
            'low_volatility_starts': [],
            'uptrend_starts': [],
            'downtrend_starts': [],
            'oversold_starts': [],
            'overbought_starts': []
        }
        
        for result in results:
            start_idx = prices.index.get_loc(result.start_time)
            
            if start_idx < 20:
                continue
            
            # Анализ условий на момент старта
            recent_prices = prices.iloc[start_idx-20:start_idx]['close'].values
            
            # Волатильность
            returns = np.diff(recent_prices) / recent_prices[:-1]
            volatility = np.std(returns)
            
            # Тренд (slope)
            x = np.arange(len(recent_prices))
            slope, _ = np.polyfit(x, recent_prices, 1)
            
            # RSI
            rsi = self._calculate_rsi(recent_prices, period=14)
            
            # Классификация условий
            if volatility > np.percentile([np.std(np.diff(prices['close'].values[max(0,i-20):i]) / prices['close'].values[max(0,i-20):i][:-1]) for i in range(20, len(prices))], 75):
                conditions_analysis['high_volatility_starts'].append(result)
            else:
                conditions_analysis['low_volatility_starts'].append(result)
            
            if slope > 0:
                conditions_analysis['uptrend_starts'].append(result)
            else:
                conditions_analysis['downtrend_starts'].append(result)
            
            if rsi < 30:
                conditions_analysis['oversold_starts'].append(result)
            elif rsi > 70:
                conditions_analysis['overbought_starts'].append(result)
        
        # Сравнение производительности
        performance_comparison = {}
        for condition, results_list in conditions_analysis.items():
            if results_list:
                performance_comparison[condition] = {
                    'avg_return': np.mean([r.total_return for r in results_list]),
                    'avg_sharpe': np.mean([r.sharpe_ratio for r in results_list]),
                    'avg_score': np.mean([r.score for r in results_list]),
                    'count': len(results_list)
                }
        
        return performance_comparison
    
    def monte_carlo_timing_analysis(
        self,
        prices: pd.DataFrame,
        strategy_func: callable,
        n_simulations: int = 1000,
        initial_capital: float = 10000
    ) -> Dict[str, any]:
        """
        Monte Carlo анализ для оценки стабильности результатов
        в зависимости от времени запуска
        
        Случайно выбирает даты старта и анализирует распределение результатов
        """
        simulation_results = []
        
        possible_start_dates = prices.index[:-self.min_trading_days]
        
        for _ in range(n_simulations):
            # Случайная дата старта
            start_date = np.random.choice(possible_start_dates)
            
            subset = prices[prices.index >= start_date]
            
            if len(subset) < self.min_trading_days:
                continue
            
            # Запуск стратегии
            equity_curve, trades = self._run_strategy(
                subset,
                strategy_func,
                initial_capital
            )
            
            metrics = self._calculate_metrics(equity_curve, trades, initial_capital)
            simulation_results.append(metrics['total_return'])
        
        if not simulation_results:
            return {}
        
        return {
            'mean_return': np.mean(simulation_results),
            'median_return': np.median(simulation_results),
            'std_return': np.std(simulation_results),
            'min_return': np.min(simulation_results),
            'max_return': np.max(simulation_results),
            'percentile_5': np.percentile(simulation_results, 5),
            'percentile_95': np.percentile(simulation_results, 95),
            'probability_positive': np.sum(np.array(simulation_results) > 0) / len(simulation_results)
        }
    
    def generate_launch_recommendations(
        self,
        prices: pd.DataFrame,
        current_date: datetime
    ) -> Dict[str, any]:
        """
        Генерирует рекомендации о том, стоит ли запускать советник сейчас
        или лучше подождать
        
        Args:
            prices: Исторические данные
            current_date: Текущая дата
            
        Returns:
            Рекомендации с оценкой риска
        """
        if not self.results_cache:
            return {'recommendation': 'insufficient_data'}
        
        # Анализ сезонности
        seasonal = self.analyze_seasonal_patterns()
        
        current_weekday = current_date.weekday()
        current_month = current_date.month
        
        # Оценка текущего дня недели
        weekday_score = 0
        if current_weekday in seasonal.get('weekday', {}):
            weekday_score = seasonal['weekday'][current_weekday]['avg_score']
        
        # Оценка текущего месяца
        month_score = 0
        if current_month in seasonal.get('month', {}):
            month_score = seasonal['month'][current_month]['avg_score']
        
        # Анализ текущих рыночных условий
        recent_prices = prices.iloc[-20:]['close'].values
        returns = np.diff(recent_prices) / recent_prices[:-1]
        current_volatility = np.std(returns)
        rsi = self._calculate_rsi(recent_prices, period=14)
        
        # Composite score
        composite_score = (weekday_score + month_score) / 2
        
        # Рекомендация
        if composite_score > 0.6:
            recommendation = 'highly_favorable'
            message = "Отличное время для запуска! Исторически это один из лучших периодов."
        elif composite_score > 0.4:
            recommendation = 'favorable'
            message = "Хорошее время для запуска. Умеренно благоприятные условия."
        elif composite_score > 0.2:
            recommendation = 'neutral'
            message = "Нейтральное время. Результаты могут варьироваться."
        else:
            recommendation = 'wait'
            message = "Рекомендуется подождать. Исторически это не лучший период."
        
        return {
            'recommendation': recommendation,
            'message': message,
            'composite_score': composite_score,
            'weekday_score': weekday_score,
            'month_score': month_score,
            'current_volatility': current_volatility,
            'current_rsi': rsi,
            'best_weekdays': sorted(
                seasonal.get('weekday', {}).items(),
                key=lambda x: x[1]['avg_score'],
                reverse=True
            )[:3] if 'weekday' in seasonal else [],
            'best_months': sorted(
                seasonal.get('month', {}).items(),
                key=lambda x: x[1]['avg_score'],
                reverse=True
            )[:3] if 'month' in seasonal else []
        }
    
    def _run_strategy(
        self,
        prices: pd.DataFrame,
        strategy_func: callable,
        initial_capital: float
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Запуск стратегии на данных
        
        Returns:
            equity_curve: Кривая капитала
            trades: Список сделок
        """
        # Получаем сигналы от стратегии
        signals = strategy_func(prices)
        
        equity = initial_capital
        equity_curve = [equity]
        trades = []
        position = 0
        entry_price = 0
        
        for i in range(1, len(prices)):
            current_price = prices.iloc[i]['close']
            signal = signals[i] if i < len(signals) else 0
            
            # Логика торговли
            if position == 0 and signal > 0.5:  # Открываем long
                position = equity / current_price * 0.95  # 95% капитала
                entry_price = current_price
                
            elif position > 0 and signal < -0.5:  # Закрываем long
                exit_price = current_price
                pnl = (exit_price - entry_price) * position
                equity += pnl
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return': pnl / (entry_price * position)
                })
                
                position = 0
            
            # Обновление капитала с учетом открытой позиции
            if position > 0:
                equity = (equity - entry_price * position) + current_price * position
            
            equity_curve.append(equity)
        
        return np.array(equity_curve), trades
    
    def _calculate_metrics(
        self,
        equity_curve: np.ndarray,
        trades: List[Dict],
        initial_capital: float
    ) -> Dict[str, float]:
        """
        Вычисление метрик производительности
        """
        if len(equity_curve) < 2:
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'score': 0
            }
        
        # Total return
        total_return = (equity_curve[-1] - initial_capital) / initial_capital
        
        # Sharpe ratio
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Max drawdown
        cumulative_max = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - cumulative_max) / cumulative_max
        max_drawdown = np.min(drawdowns)
        
        # Win rate
        if trades:
            wins = sum(1 for t in trades if t['pnl'] > 0)
            win_rate = wins / len(trades)
        else:
            win_rate = 0
        
        # Composite score
        score = (
            total_return * 0.3 +
            sharpe_ratio * 0.3 +
            (1 + max_drawdown) * 0.2 +  # меньше просадка = лучше
            win_rate * 0.2
        )
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'score': score
        }
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Расчет RSI индикатора"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def export_results(self, filename: str = 'launch_time_analysis.json'):
        """
        Экспорт результатов анализа в файл
        """
        if not self.results_cache:
            print("No results to export")
            return
        
        export_data = {
            'analysis_date': datetime.now().isoformat(),
            'num_simulations': len(self.results_cache),
            'results': [
                {
                    'start_time': r.start_time.isoformat(),
                    'end_time': r.end_time.isoformat(),
                    'total_return': r.total_return,
                    'sharpe_ratio': r.sharpe_ratio,
                    'max_drawdown': r.max_drawdown,
                    'win_rate': r.win_rate,
                    'num_trades': r.num_trades,
                    'score': r.score
                }
                for r in self.results_cache
            ],
            'seasonal_analysis': self.analyze_seasonal_patterns()
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"Results exported to {filename}")


def example_strategy(prices: pd.DataFrame) -> np.ndarray:
    """
    Простая стратегия для примера - Moving Average Crossover
    """
    close_prices = prices['close'].values
    signals = np.zeros(len(close_prices))
    
    if len(close_prices) < 50:
        return signals
    
    # Быстрая и медленная MA
    fast_ma = pd.Series(close_prices).rolling(10).mean().values
    slow_ma = pd.Series(close_prices).rolling(50).mean().values
    
    for i in range(50, len(close_prices)):
        if fast_ma[i] > slow_ma[i] and fast_ma[i-1] <= slow_ma[i-1]:
            signals[i] = 1  # Buy signal
        elif fast_ma[i] < slow_ma[i] and fast_ma[i-1] >= slow_ma[i-1]:
            signals[i] = -1  # Sell signal
    
    return signals


def example_usage():
    """
    Пример использования анализатора оптимального времени запуска
    """
    print("=== Анализатор оптимального времени запуска ===\n")
    
    # Генерация тестовых данных (2 года)
    dates = pd.date_range(start='2022-01-01', end='2024-01-01', freq='D')
    np.random.seed(42)
    
    prices_data = {
        'open': 100 + np.cumsum(np.random.randn(len(dates)) * 2),
        'high': 100 + np.cumsum(np.random.randn(len(dates)) * 2) + 1,
        'low': 100 + np.cumsum(np.random.randn(len(dates)) * 2) - 1,
        'close': 100 + np.cumsum(np.random.randn(len(dates)) * 2)
    }
    prices = pd.DataFrame(prices_data, index=dates)
    
    # Создаем анализатор
    analyzer = OptimalLaunchTimeAnalyzer(
        lookback_days=365,
        min_trading_days=90,
        step_days=7  # Анализируем каждую неделю
    )
    
    # Анализ всех возможных времен старта
    print("Запуск анализа всех возможных времен старта...")
    results = analyzer.analyze_all_start_times(
        prices=prices,
        strategy_func=example_strategy,
        initial_capital=10000
    )
    
    print(f"Проанализировано {len(results)} различных точек старта\n")
    
    # Топ-10 лучших времен запуска
    top_launches = analyzer.find_optimal_launch_times(top_n=10)
    
    print("=== ТОП-10 лучших времен запуска ===")
    for i, result in enumerate(top_launches, 1):
        print(f"\n{i}. Старт: {result.start_time.strftime('%Y-%m-%d')}")
        print(f"   Доходность: {result.total_return*100:.2f}%")
        print(f"   Sharpe: {result.sharpe_ratio:.2f}")
        print(f"   Макс. просадка: {result.max_drawdown*100:.2f}%")
        print(f"   Win Rate: {result.win_rate*100:.2f}%")
        print(f"   Оценка: {result.score:.4f}")
    
    # Сезонный анализ
    print("\n\n=== Сезонный анализ ===")
    seasonal = analyzer.analyze_seasonal_patterns()
    
    if 'weekday' in seasonal:
        print("\nЛучшие дни недели для запуска:")
        weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        sorted_weekdays = sorted(
            seasonal['weekday'].items(),
            key=lambda x: x[1]['avg_score'],
            reverse=True
        )
        for day, stats in sorted_weekdays[:3]:
            print(f"  {weekday_names[day]}: средняя доходность {stats['avg_return']*100:.2f}%, "
                  f"Sharpe {stats['avg_sharpe']:.2f}")
    
    if 'month' in seasonal:
        print("\nЛучшие месяцы для запуска:")
        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                       'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        sorted_months = sorted(
            seasonal['month'].items(),
            key=lambda x: x[1]['avg_score'],
            reverse=True
        )
        for month, stats in sorted_months[:3]:
            print(f"  {month_names[month-1]}: средняя доходность {stats['avg_return']*100:.2f}%, "
                  f"Sharpe {stats['avg_sharpe']:.2f}")
    
    # Monte Carlo анализ
    print("\n\n=== Monte Carlo анализ (1000 симуляций) ===")
    mc_results = analyzer.monte_carlo_timing_analysis(
        prices=prices,
        strategy_func=example_strategy,
        n_simulations=1000
    )
    
    if mc_results:
        print(f"Средняя доходность: {mc_results['mean_return']*100:.2f}%")
        print(f"Медианная доходность: {mc_results['median_return']*100:.2f}%")
        print(f"Std доходности: {mc_results['std_return']*100:.2f}%")
        print(f"Диапазон: [{mc_results['min_return']*100:.2f}%, {mc_results['max_return']*100:.2f}%]")
        print(f"5-й перцентиль: {mc_results['percentile_5']*100:.2f}%")
        print(f"95-й перцентиль: {mc_results['percentile_95']*100:.2f}%")
        print(f"Вероятность прибыли: {mc_results['probability_positive']*100:.2f}%")
    
    # Рекомендации для текущего момента
    print("\n\n=== Рекомендации для запуска СЕЙЧАС ===")
    recommendations = analyzer.generate_launch_recommendations(
        prices=prices,
        current_date=datetime.now()
    )
    
    print(f"\nСтатус: {recommendations['recommendation'].upper()}")
    print(f"Сообщение: {recommendations['message']}")
    print(f"Composite Score: {recommendations.get('composite_score', 0):.4f}")
    print(f"Текущая волатильность: {recommendations.get('current_volatility', 0):.4f}")
    print(f"Текущий RSI: {recommendations.get('current_rsi', 50):.2f}")
    
    # Экспорт результатов
    analyzer.export_results('launch_time_analysis.json')
    print("\n\nРезультаты экспортированы в launch_time_analysis.json")


if __name__ == "__main__":
    example_usage()
