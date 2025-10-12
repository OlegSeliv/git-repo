"""
Фреймворк для тестирования и валидации торговых стратегий
Включает историческое тестирование, валидацию, оптимизацию параметров и анализ результатов
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import warnings
import itertools
from abc import ABC, abstractmethod
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class TradeDirection(Enum):
    """Направление сделки"""
    LONG = "long"
    SHORT = "short"

class TradeStatus(Enum):
    """Статус сделки"""
    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"
    EXPIRED = "expired"

@dataclass
class Trade:
    """Торговая сделка"""
    id: str
    symbol: str
    direction: TradeDirection
    entry_time: datetime
    entry_price: float
    size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    commission: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    exit_reason: str = ""

@dataclass
class BacktestResult:
    """Результат бэктестинга"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    var_95: float
    var_99: float
    avg_trade_duration: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)

class Strategy(ABC):
    """Базовый класс для торговых стратегий"""
    
    def __init__(self, name: str, parameters: Dict[str, Any]):
        self.name = name
        self.parameters = parameters
        self.trades = []
        self.current_position = None
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Генерирует торговые сигналы"""
        pass
    
    @abstractmethod
    def should_enter(self, data: pd.DataFrame, index: int) -> Tuple[bool, TradeDirection]:
        """Определяет, нужно ли войти в позицию"""
        pass
    
    @abstractmethod
    def should_exit(self, trade: Trade, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        """Определяет, нужно ли выйти из позиции"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Возвращает параметры стратегии"""
        return self.parameters.copy()
    
    def set_parameters(self, parameters: Dict[str, Any]):
        """Устанавливает параметры стратегии"""
        self.parameters.update(parameters)

class MovingAverageCrossoverStrategy(Strategy):
    """Стратегия пересечения скользящих средних"""
    
    def __init__(self, fast_period: int = 10, slow_period: int = 20, 
                 stop_loss_pct: float = 0.02, take_profit_pct: float = 0.04):
        parameters = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct
        }
        super().__init__("MA_Crossover", parameters)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Генерирует сигналы пересечения MA"""
        df = data.copy()
        
        # Вычисляем скользящие средние
        df['MA_fast'] = df['close'].rolling(window=self.parameters['fast_period']).mean()
        df['MA_slow'] = df['close'].rolling(window=self.parameters['slow_period']).mean()
        
        # Сигналы пересечения
        df['signal'] = 0
        df.loc[df['MA_fast'] > df['MA_slow'], 'signal'] = 1  # Покупка
        df.loc[df['MA_fast'] < df['MA_slow'], 'signal'] = -1  # Продажа
        
        # Сигналы входа
        df['entry_signal'] = df['signal'].diff()
        
        return df
    
    def should_enter(self, data: pd.DataFrame, index: int) -> Tuple[bool, TradeDirection]:
        """Определяет вход в позицию"""
        if index < self.parameters['slow_period']:
            return False, None
        
        entry_signal = data.iloc[index]['entry_signal']
        
        if entry_signal == 1:
            return True, TradeDirection.LONG
        elif entry_signal == -1:
            return True, TradeDirection.SHORT
        
        return False, None
    
    def should_exit(self, trade: Trade, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        """Определяет выход из позиции"""
        current_price = data.iloc[index]['close']
        
        # Проверяем стоп-лосс
        if trade.direction == TradeDirection.LONG:
            if trade.stop_loss and current_price <= trade.stop_loss:
                return True, "Stop loss"
            if trade.take_profit and current_price >= trade.take_profit:
                return True, "Take profit"
        else:
            if trade.stop_loss and current_price >= trade.stop_loss:
                return True, "Stop loss"
            if trade.take_profit and current_price <= trade.take_profit:
                return True, "Take profit"
        
        # Проверяем изменение сигнала
        if index < len(data) - 1:
            current_signal = data.iloc[index]['signal']
            next_signal = data.iloc[index + 1]['signal']
            
            if (trade.direction == TradeDirection.LONG and current_signal < 0) or \
               (trade.direction == TradeDirection.SHORT and current_signal > 0):
                return True, "Signal change"
        
        return False, ""

class BacktestEngine:
    """Движок бэктестинга"""
    
    def __init__(self, initial_capital: float = 10000, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        self.current_capital = initial_capital
        self.equity_curve = [initial_capital]
        self.trades = []
        self.current_trade_id = 0
    
    def run_backtest(self, strategy: Strategy, data: pd.DataFrame, 
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> BacktestResult:
        """Запускает бэктест стратегии"""
        
        # Фильтруем данные по датам
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        # Генерируем сигналы
        data_with_signals = strategy.generate_signals(data)
        
        # Сбрасываем состояние
        self.current_capital = self.initial_capital
        self.equity_curve = [self.initial_capital]
        self.trades = []
        self.current_trade_id = 0
        
        # Проходим по данным
        for i in range(len(data_with_signals)):
            current_data = data_with_signals.iloc[:i+1]
            current_row = data_with_signals.iloc[i]
            
            # Проверяем выход из текущей позиции
            if strategy.current_position:
                should_exit, exit_reason = strategy.should_exit(
                    strategy.current_position, current_data, i
                )
                
                if should_exit:
                    self._close_trade(strategy.current_position, current_row, exit_reason)
                    strategy.current_position = None
            
            # Проверяем вход в новую позицию
            if not strategy.current_position:
                should_enter, direction = strategy.should_enter(current_data, i)
                
                if should_enter:
                    self._open_trade(strategy, current_row, direction)
            
            # Обновляем кривую капитала
            self._update_equity_curve()
        
        # Закрываем оставшиеся позиции
        if strategy.current_position:
            last_row = data_with_signals.iloc[-1]
            self._close_trade(strategy.current_position, last_row, "End of data")
        
        # Вычисляем результаты
        return self._calculate_results()
    
    def _open_trade(self, strategy: Strategy, row: pd.Series, direction: TradeDirection):
        """Открывает новую сделку"""
        trade_id = f"trade_{self.current_trade_id}"
        self.current_trade_id += 1
        
        # Вычисляем размер позиции (упрощенно - 10% от капитала)
        position_size = self.current_capital * 0.1 / row['close']
        
        # Вычисляем стоп-лосс и тейк-профит
        stop_loss = None
        take_profit = None
        
        if direction == TradeDirection.LONG:
            stop_loss = row['close'] * (1 - strategy.parameters['stop_loss_pct'])
            take_profit = row['close'] * (1 + strategy.parameters['take_profit_pct'])
        else:
            stop_loss = row['close'] * (1 + strategy.parameters['stop_loss_pct'])
            take_profit = row['close'] * (1 - strategy.parameters['take_profit_pct'])
        
        trade = Trade(
            id=trade_id,
            symbol="SYMBOL",
            direction=direction,
            entry_time=row.name,
            entry_price=row['close'],
            size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        strategy.current_position = trade
        self.trades.append(trade)
    
    def _close_trade(self, trade: Trade, row: pd.Series, exit_reason: str):
        """Закрывает сделку"""
        trade.exit_time = row.name
        trade.exit_price = row['close']
        trade.status = TradeStatus.CLOSED
        trade.exit_reason = exit_reason
        
        # Вычисляем P&L
        if trade.direction == TradeDirection.LONG:
            trade.pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.pnl = (trade.entry_price - trade.exit_price) * trade.size
        
        # Вычисляем комиссию
        trade.commission = (trade.entry_price + trade.exit_price) * trade.size * self.commission
        trade.pnl -= trade.commission
        
        # Обновляем капитал
        self.current_capital += trade.pnl
    
    def _update_equity_curve(self):
        """Обновляет кривую капитала"""
        self.equity_curve.append(self.current_capital)
    
    def _calculate_results(self) -> BacktestResult:
        """Вычисляет результаты бэктестинга"""
        if not self.trades:
            return self._empty_results()
        
        # Базовые метрики
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # P&L метрики
        total_pnl = sum(t.pnl for t in self.trades)
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Просадка
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        # Длительность максимальной просадки
        max_dd_duration = self._calculate_max_drawdown_duration(drawdown)
        
        # Коэффициенты
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Sortino ratio
        negative_returns = returns[returns < 0]
        sortino_ratio = returns.mean() / negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 and negative_returns.std() > 0 else 0
        
        # Calmar ratio
        annual_return = (self.current_capital / self.initial_capital) ** (252 / len(equity_series)) - 1
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        # VaR
        var_95 = np.percentile(returns, 5) if len(returns) > 20 else 0
        var_99 = np.percentile(returns, 1) if len(returns) > 20 else 0
        
        # Длительность сделок
        trade_durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in self.trades if t.exit_time]
        avg_trade_duration = np.mean(trade_durations) if trade_durations else 0
        
        # Лучшая и худшая сделки
        best_trade = max(t.pnl for t in self.trades) if self.trades else 0
        worst_trade = min(t.pnl for t in self.trades) if self.trades else 0
        
        # Последовательные выигрыши/проигрыши
        consecutive_wins, consecutive_losses = self._calculate_consecutive_trades()
        
        return BacktestResult(
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            var_95=var_95,
            var_99=var_99,
            avg_trade_duration=avg_trade_duration,
            best_trade=best_trade,
            worst_trade=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            equity_curve=self.equity_curve,
            trades=self.trades
        )
    
    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """Вычисляет длительность максимальной просадки"""
        in_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        return max(drawdown_periods) if drawdown_periods else 0
    
    def _calculate_consecutive_trades(self) -> Tuple[int, int]:
        """Вычисляет максимальные последовательные выигрыши и проигрыши"""
        if not self.trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _empty_results(self) -> BacktestResult:
        """Возвращает пустые результаты"""
        return BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            var_95=0.0,
            var_99=0.0,
            avg_trade_duration=0.0,
            best_trade=0.0,
            worst_trade=0.0,
            consecutive_wins=0,
            consecutive_losses=0,
            equity_curve=[self.initial_capital],
            trades=[]
        )

class ParameterOptimizer:
    """Оптимизатор параметров стратегии"""
    
    def __init__(self, strategy_class, parameter_ranges: Dict[str, List]):
        self.strategy_class = strategy_class
        self.parameter_ranges = parameter_ranges
        self.optimization_results = []
    
    def optimize(self, data: pd.DataFrame, optimization_metric: str = 'sharpe_ratio',
                max_combinations: int = 1000) -> List[Dict]:
        """Оптимизирует параметры стратегии"""
        
        # Генерируем комбинации параметров
        param_names = list(self.parameter_ranges.keys())
        param_values = list(self.parameter_ranges.values())
        
        combinations = list(itertools.product(*param_values))
        
        # Ограничиваем количество комбинаций
        if len(combinations) > max_combinations:
            combinations = combinations[:max_combinations]
        
        results = []
        
        for i, combination in enumerate(combinations):
            try:
                # Создаем параметры
                parameters = dict(zip(param_names, combination))
                
                # Создаем стратегию
                strategy = self.strategy_class(**parameters)
                
                # Запускаем бэктест
                engine = BacktestEngine()
                result = engine.run_backtest(strategy, data)
                
                # Сохраняем результат
                optimization_result = {
                    'parameters': parameters,
                    'result': result,
                    'metric_value': getattr(result, optimization_metric, 0)
                }
                
                results.append(optimization_result)
                
                if i % 100 == 0:
                    logger.info(f"Обработано {i}/{len(combinations)} комбинаций")
                
            except Exception as e:
                logger.warning(f"Ошибка при тестировании комбинации {combination}: {e}")
                continue
        
        # Сортируем по метрике
        results.sort(key=lambda x: x['metric_value'], reverse=True)
        self.optimization_results = results
        
        return results
    
    def get_best_parameters(self, top_n: int = 5) -> List[Dict]:
        """Возвращает лучшие параметры"""
        return self.optimization_results[:top_n]

class WalkForwardAnalyzer:
    """Анализатор Walk-Forward для валидации стратегий"""
    
    def __init__(self, train_period: int = 252, test_period: int = 63, step: int = 21):
        self.train_period = train_period  # Дней для обучения
        self.test_period = test_period    # Дней для тестирования
        self.step = step                  # Шаг переобучения
        self.results = []
    
    def analyze(self, strategy: Strategy, data: pd.DataFrame) -> List[Dict]:
        """Проводит Walk-Forward анализ"""
        
        total_days = len(data)
        results = []
        
        start_idx = 0
        while start_idx + self.train_period + self.test_period < total_days:
            # Данные для обучения
            train_start = start_idx
            train_end = start_idx + self.train_period
            train_data = data.iloc[train_start:train_end]
            
            # Данные для тестирования
            test_start = train_end
            test_end = min(test_start + self.test_period, total_days)
            test_data = data.iloc[test_start:test_end]
            
            try:
                # Тестируем на обучающих данных
                engine = BacktestEngine()
                train_result = engine.run_backtest(strategy, train_data)
                
                # Тестируем на тестовых данных
                engine = BacktestEngine()
                test_result = engine.run_backtest(strategy, test_data)
                
                # Сохраняем результат
                result = {
                    'train_period': (train_data.index[0], train_data.index[-1]),
                    'test_period': (test_data.index[0], test_data.index[-1]),
                    'train_result': train_result,
                    'test_result': test_result,
                    'stability_ratio': test_result.sharpe_ratio / train_result.sharpe_ratio if train_result.sharpe_ratio != 0 else 0
                }
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Ошибка в периоде {start_idx}: {e}")
            
            start_idx += self.step
        
        self.results = results
        return results
    
    def get_stability_metrics(self) -> Dict[str, float]:
        """Вычисляет метрики стабильности стратегии"""
        if not self.results:
            return {}
        
        stability_ratios = [r['stability_ratio'] for r in self.results]
        test_sharpes = [r['test_result'].sharpe_ratio for r in self.results]
        
        return {
            'avg_stability_ratio': np.mean(stability_ratios),
            'stability_std': np.std(stability_ratios),
            'avg_test_sharpe': np.mean(test_sharpes),
            'test_sharpe_std': np.std(test_sharpes),
            'positive_periods': sum(1 for r in stability_ratios if r > 0.5),
            'total_periods': len(stability_ratios)
        }

# Пример использования
if __name__ == "__main__":
    # Создаем тестовые данные
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
    prices = [100 + i * 0.01 + np.random.normal(0, 1) for i in range(len(dates))]
    
    data = pd.DataFrame({
        'close': prices,
        'high': [p + abs(np.random.normal(0, 0.5)) for p in prices],
        'low': [p - abs(np.random.normal(0, 0.5)) for p in prices],
        'volume': [1000 + np.random.normal(0, 100) for _ in range(len(dates))]
    }, index=dates)
    
    # Создаем стратегию
    strategy = MovingAverageCrossoverStrategy(fast_period=10, slow_period=20)
    
    # Запускаем бэктест
    engine = BacktestEngine(initial_capital=10000)
    result = engine.run_backtest(strategy, data)
    
    print("=== РЕЗУЛЬТАТЫ БЭКТЕСТИНГА ===")
    print(f"Общее количество сделок: {result.total_trades}")
    print(f"Процент выигрышных сделок: {result.win_rate:.1%}")
    print(f"Общий P&L: {result.total_pnl:.2f}")
    print(f"Коэффициент Шарпа: {result.sharpe_ratio:.2f}")
    print(f"Максимальная просадка: {result.max_drawdown:.1%}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    
    # Оптимизация параметров
    print("\n=== ОПТИМИЗАЦИЯ ПАРАМЕТРОВ ===")
    optimizer = ParameterOptimizer(
        MovingAverageCrossoverStrategy,
        {
            'fast_period': [5, 10, 15],
            'slow_period': [20, 30, 40],
            'stop_loss_pct': [0.01, 0.02, 0.03]
        }
    )
    
    optimization_results = optimizer.optimize(data, max_combinations=50)
    best_params = optimizer.get_best_parameters(3)
    
    print("Лучшие параметры:")
    for i, params in enumerate(best_params):
        print(f"{i+1}. {params['parameters']} - Sharpe: {params['metric_value']:.2f}")