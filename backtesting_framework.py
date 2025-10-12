"""
Комплексный фреймворк для бэктестинга с учетом времени запуска
и рыночных условий
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import matplotlib.pyplot as plt
from market_neutral_strategy import MarketNeutralStrategy, PositionSizer, MarketState
from optimal_launch_time import OptimalLaunchTimeAnalyzer, LaunchTimeResult


@dataclass
class BacktestConfig:
    """Конфигурация бэктеста"""
    initial_capital: float = 10000.0
    commission: float = 0.001  # 0.1% комиссия
    slippage: float = 0.0005  # 0.05% проскальзывание
    use_market_neutral: bool = True
    max_position_size: float = 1.0
    risk_per_trade: float = 0.02
    

@dataclass
class Trade:
    """Информация о сделке"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    side: str  # 'long' or 'short'
    pnl: float
    pnl_percent: float
    commission_paid: float
    slippage_cost: float


@dataclass
class BacktestResult:
    """Результаты бэктеста"""
    config: BacktestConfig
    start_date: datetime
    end_date: datetime
    
    # Основные метрики
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    
    # Торговые метрики
    num_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    
    # Временные ряды
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    trades: List[Trade]
    
    # Дополнительные метрики
    calmar_ratio: float
    recovery_factor: float
    expectancy: float


class AdvancedBacktester:
    """
    Продвинутый бэктестер с поддержкой:
    - Маркет-нейтральных стратегий
    - Анализа времени запуска
    - Комиссий и проскальзывания
    - Walk-forward анализа
    - Monte Carlo симуляций
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.market_neutral = None
        self.position_sizer = None
        
        if config.use_market_neutral:
            self.market_neutral = MarketNeutralStrategy()
            self.position_sizer = PositionSizer(
                max_position_size=config.max_position_size,
                risk_per_trade=config.risk_per_trade
            )
    
    def run(
        self,
        prices: pd.DataFrame,
        strategy_signals: Callable,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BacktestResult:
        """
        Запуск бэктеста
        
        Args:
            prices: DataFrame с OHLC данными
            strategy_signals: Функция, генерирующая торговые сигналы
            start_date: Дата начала (опционально)
            end_date: Дата конца (опционально)
            
        Returns:
            Результаты бэктеста
        """
        # Фильтрация по датам
        if start_date:
            prices = prices[prices.index >= start_date]
        if end_date:
            prices = prices[prices.index <= end_date]
        
        if len(prices) < 2:
            raise ValueError("Недостаточно данных для бэктеста")
        
        # Инициализация
        capital = self.config.initial_capital
        position = 0
        position_entry_price = 0
        position_entry_time = None
        
        equity_curve = []
        trades = []
        
        # Генерация сигналов
        signals = strategy_signals(prices)
        
        # Основной цикл бэктеста
        for i in range(len(prices)):
            current_time = prices.index[i]
            current_price = prices.iloc[i]['close']
            signal = signals[i] if i < len(signals) else 0
            
            # Маркет-нейтральная корректировка
            if self.config.use_market_neutral and i >= 20:
                recent_prices = prices.iloc[max(0, i-20):i+1]['close'].values
                market_state = self.market_neutral.get_market_state(recent_prices)
                signal = self.market_neutral.adjust_signal_for_market(signal, market_state)
            
            # Логика торговли
            if position == 0:
                # Открытие позиции
                if abs(signal) > 0.5:  # Порог для входа
                    side = 'long' if signal > 0 else 'short'
                    
                    # Расчет размера позиции
                    if self.config.use_market_neutral and self.position_sizer:
                        size = self.position_sizer.calculate_position_size(
                            signal_strength=abs(signal),
                            market_state=market_state,
                            account_balance=capital,
                            current_price=current_price
                        )
                    else:
                        # Стандартный размер
                        size = (capital * self.config.max_position_size) / current_price
                    
                    # Применяем комиссию и проскальзывание
                    entry_price = current_price * (1 + self.config.slippage if side == 'long' else 1 - self.config.slippage)
                    commission = size * entry_price * self.config.commission
                    
                    position = size
                    position_entry_price = entry_price
                    position_entry_time = current_time
                    capital -= commission
                    
            else:
                # Закрытие позиции
                should_close = False
                
                if signal < -0.5:  # Сигнал на закрытие
                    should_close = True
                
                if should_close:
                    exit_price = current_price * (1 - self.config.slippage)
                    commission = position * exit_price * self.config.commission
                    slippage_cost = position * current_price * self.config.slippage
                    
                    # Расчет P&L
                    pnl = (exit_price - position_entry_price) * position
                    pnl -= commission
                    
                    capital += pnl
                    
                    # Запись сделки
                    trade = Trade(
                        entry_time=position_entry_time,
                        exit_time=current_time,
                        entry_price=position_entry_price,
                        exit_price=exit_price,
                        size=position,
                        side='long',
                        pnl=pnl,
                        pnl_percent=(exit_price / position_entry_price - 1) * 100,
                        commission_paid=commission,
                        slippage_cost=slippage_cost
                    )
                    trades.append(trade)
                    
                    # Обновление статистики для Kelly
                    if self.position_sizer:
                        self.position_sizer.update_statistics(
                            [{'pnl': t.pnl} for t in trades]
                        )
                    
                    position = 0
            
            # Обновление капитала (mark-to-market)
            if position > 0:
                unrealized_pnl = (current_price - position_entry_price) * position
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
        
        # Создание результатов
        equity_series = pd.Series(equity_curve, index=prices.index)
        
        result = self._calculate_results(
            equity_series=equity_series,
            trades=trades,
            start_date=prices.index[0],
            end_date=prices.index[-1]
        )
        
        return result
    
    def walk_forward_analysis(
        self,
        prices: pd.DataFrame,
        strategy_signals: Callable,
        train_period_days: int = 180,
        test_period_days: int = 60,
        step_days: int = 30
    ) -> List[BacktestResult]:
        """
        Walk-Forward анализ для проверки стабильности стратегии
        
        Разбивает данные на периоды обучения и тестирования,
        симулирует реальную торговлю с регулярной переоптимизацией
        """
        results = []
        
        current_start = prices.index[0]
        
        while current_start < prices.index[-1] - timedelta(days=train_period_days + test_period_days):
            # Период обучения
            train_end = current_start + timedelta(days=train_period_days)
            train_data = prices[(prices.index >= current_start) & (prices.index < train_end)]
            
            # Период тестирования
            test_start = train_end
            test_end = test_start + timedelta(days=test_period_days)
            test_data = prices[(prices.index >= test_start) & (prices.index < test_end)]
            
            if len(test_data) < 10:
                break
            
            # Запуск бэктеста на тестовом периоде
            try:
                result = self.run(
                    prices=test_data,
                    strategy_signals=strategy_signals
                )
                results.append(result)
            except Exception as e:
                print(f"Ошибка в walk-forward периоде {test_start}: {e}")
            
            # Сдвиг вперед
            current_start += timedelta(days=step_days)
        
        return results
    
    def monte_carlo_simulation(
        self,
        trades: List[Trade],
        n_simulations: int = 1000,
        n_trades_per_sim: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Monte Carlo симуляция на основе исторических сделок
        
        Случайно пересэмплирует сделки для оценки диапазона возможных результатов
        """
        if not trades:
            return {}
        
        if n_trades_per_sim is None:
            n_trades_per_sim = len(trades)
        
        simulation_results = []
        
        for _ in range(n_simulations):
            # Случайная выборка сделок с возвратом
            sampled_trades = np.random.choice(trades, size=n_trades_per_sim, replace=True)
            
            # Расчет результата
            total_pnl = sum(t.pnl for t in sampled_trades)
            total_return = total_pnl / self.config.initial_capital
            
            simulation_results.append(total_return)
        
        simulation_results = np.array(simulation_results)
        
        return {
            'mean': np.mean(simulation_results),
            'median': np.median(simulation_results),
            'std': np.std(simulation_results),
            'min': np.min(simulation_results),
            'max': np.max(simulation_results),
            'percentile_5': np.percentile(simulation_results, 5),
            'percentile_25': np.percentile(simulation_results, 25),
            'percentile_75': np.percentile(simulation_results, 75),
            'percentile_95': np.percentile(simulation_results, 95),
            'probability_positive': np.mean(simulation_results > 0),
            'probability_above_10pct': np.mean(simulation_results > 0.1)
        }
    
    def sensitivity_analysis(
        self,
        prices: pd.DataFrame,
        strategy_signals: Callable,
        parameter_ranges: Dict[str, List[float]]
    ) -> pd.DataFrame:
        """
        Анализ чувствительности к параметрам
        
        Args:
            parameter_ranges: Словарь {имя_параметра: [значения]}
            
        Returns:
            DataFrame с результатами для каждой комбинации параметров
        """
        results = []
        
        # Перебор всех комбинаций параметров
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        from itertools import product
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            # Обновление конфигурации
            old_config = self.config
            new_config = BacktestConfig(**{**old_config.__dict__, **params})
            self.config = new_config
            
            # Запуск бэктеста
            try:
                result = self.run(prices, strategy_signals)
                
                results.append({
                    **params,
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'win_rate': result.win_rate,
                    'num_trades': result.num_trades
                })
            except Exception as e:
                print(f"Ошибка для параметров {params}: {e}")
            
            # Восстановление конфигурации
            self.config = old_config
        
        return pd.DataFrame(results)
    
    def _calculate_results(
        self,
        equity_series: pd.Series,
        trades: List[Trade],
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """
        Расчет всех метрик результатов
        """
        # Базовые метрики
        total_return = (equity_series.iloc[-1] - self.config.initial_capital) / self.config.initial_capital
        
        # Годовая доходность
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Доходности
        returns = equity_series.pct_change().dropna()
        
        # Sharpe ratio (предполагаем 0% risk-free rate)
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Sortino ratio (только отрицательная волатильность)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and negative_returns.std() > 0:
            sortino_ratio = returns.mean() / negative_returns.std() * np.sqrt(252)
        else:
            sortino_ratio = 0
        
        # Drawdown
        cummax = equity_series.expanding().max()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = drawdown.min()
        
        # Max drawdown duration
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        for dd in is_drawdown:
            if dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # Торговые метрики
        if trades:
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl < 0]
            
            win_rate = len(winning_trades) / len(trades)
            
            total_wins = sum(t.pnl for t in winning_trades)
            total_losses = abs(sum(t.pnl for t in losing_trades))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
            
            largest_win = max([t.pnl for t in winning_trades]) if winning_trades else 0
            largest_loss = min([t.pnl for t in losing_trades]) if losing_trades else 0
            
            # Expectancy (математическое ожидание на сделку)
            expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)
        else:
            win_rate = 0
            profit_factor = 0
            avg_win = 0
            avg_loss = 0
            largest_win = 0
            largest_loss = 0
            expectancy = 0
        
        # Дополнительные метрики
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return BacktestResult(
            config=self.config,
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            num_trades=len(trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            equity_curve=equity_series,
            drawdown_curve=drawdown,
            trades=trades,
            calmar_ratio=calmar_ratio,
            recovery_factor=recovery_factor,
            expectancy=expectancy
        )


def print_backtest_results(result: BacktestResult):
    """
    Красивый вывод результатов бэктеста
    """
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ БЭКТЕСТА")
    print("=" * 60)
    print(f"\nПериод: {result.start_date.strftime('%Y-%m-%d')} - {result.end_date.strftime('%Y-%m-%d')}")
    print(f"Начальный капитал: ${result.config.initial_capital:,.2f}")
    print(f"Конечный капитал: ${result.equity_curve.iloc[-1]:,.2f}")
    
    print("\n--- ДОХОДНОСТЬ ---")
    print(f"Общая доходность: {result.total_return*100:.2f}%")
    print(f"Годовая доходность: {result.annual_return*100:.2f}%")
    
    print("\n--- РИСК ---")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio: {result.sortino_ratio:.2f}")
    print(f"Максимальная просадка: {result.max_drawdown*100:.2f}%")
    print(f"Длительность макс. просадки: {result.max_drawdown_duration} дней")
    print(f"Calmar Ratio: {result.calmar_ratio:.2f}")
    print(f"Recovery Factor: {result.recovery_factor:.2f}")
    
    print("\n--- ТОРГОВЛЯ ---")
    print(f"Количество сделок: {result.num_trades}")
    print(f"Win Rate: {result.win_rate*100:.2f}%")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    print(f"Средняя прибыль: ${result.avg_win:.2f}")
    print(f"Средний убыток: ${result.avg_loss:.2f}")
    print(f"Наибольшая прибыль: ${result.largest_win:.2f}")
    print(f"Наибольший убыток: ${result.largest_loss:.2f}")
    print(f"Expectancy (на сделку): ${result.expectancy:.2f}")
    
    print("=" * 60)


def example_usage():
    """
    Пример использования фреймворка
    """
    # Генерация тестовых данных
    dates = pd.date_range(start='2022-01-01', end='2024-01-01', freq='D')
    np.random.seed(42)
    
    prices_data = {
        'open': 100 + np.cumsum(np.random.randn(len(dates)) * 2),
        'high': 100 + np.cumsum(np.random.randn(len(dates)) * 2) + 1,
        'low': 100 + np.cumsum(np.random.randn(len(dates)) * 2) - 1,
        'close': 100 + np.cumsum(np.random.randn(len(dates)) * 2)
    }
    prices = pd.DataFrame(prices_data, index=dates)
    
    # Простая стратегия (MA Crossover)
    def simple_strategy(prices_df):
        close = prices_df['close'].values
        signals = np.zeros(len(close))
        
        if len(close) < 50:
            return signals
        
        fast_ma = pd.Series(close).rolling(10).mean().values
        slow_ma = pd.Series(close).rolling(50).mean().values
        
        for i in range(50, len(close)):
            if fast_ma[i] > slow_ma[i]:
                signals[i] = 1
            elif fast_ma[i] < slow_ma[i]:
                signals[i] = -1
        
        return signals
    
    # Конфигурация бэктеста
    config = BacktestConfig(
        initial_capital=10000,
        commission=0.001,
        use_market_neutral=True,
        risk_per_trade=0.02
    )
    
    # Создание бэктестера
    backtester = AdvancedBacktester(config)
    
    # Запуск бэктеста
    print("Запуск обычного бэктеста...\n")
    result = backtester.run(prices, simple_strategy)
    print_backtest_results(result)
    
    # Walk-Forward анализ
    print("\n\nЗапуск Walk-Forward анализа...\n")
    wf_results = backtester.walk_forward_analysis(
        prices,
        simple_strategy,
        train_period_days=180,
        test_period_days=60,
        step_days=30
    )
    
    print(f"Выполнено {len(wf_results)} Walk-Forward периодов")
    print(f"Средняя доходность: {np.mean([r.total_return for r in wf_results])*100:.2f}%")
    print(f"Средний Sharpe: {np.mean([r.sharpe_ratio for r in wf_results]):.2f}")
    
    # Monte Carlo симуляция
    if result.trades:
        print("\n\nMonte Carlo симуляция (1000 итераций)...\n")
        mc_results = backtester.monte_carlo_simulation(result.trades, n_simulations=1000)
        
        print(f"Средняя доходность: {mc_results['mean']*100:.2f}%")
        print(f"Медианная доходность: {mc_results['median']*100:.2f}%")
        print(f"Std доходности: {mc_results['std']*100:.2f}%")
        print(f"5-й перцентиль: {mc_results['percentile_5']*100:.2f}%")
        print(f"95-й перцентиль: {mc_results['percentile_95']*100:.2f}%")
        print(f"Вероятность прибыли: {mc_results['probability_positive']*100:.2f}%")


if __name__ == "__main__":
    example_usage()
