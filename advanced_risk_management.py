"""
Продвинутая система управления рисками для торгового робота
Включает адаптивное управление позициями, динамические стоп-лоссы и портфельное управление
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Уровни риска"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class PositionStatus(Enum):
    """Статус позиции"""
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"
    STOPPED_OUT = "stopped_out"
    TAKE_PROFIT = "take_profit"

@dataclass
class Position:
    """Торговая позиция"""
    id: str
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    status: PositionStatus
    entry_time: datetime
    unrealized_pnl: float
    max_favorable: float
    max_adverse: float

@dataclass
class RiskMetrics:
    """Метрики риска"""
    portfolio_value: float
    total_exposure: float
    max_drawdown: float
    current_drawdown: float
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_consecutive_losses: int
    win_rate: float
    profit_factor: float

class PositionSizingCalculator:
    """Калькулятор размера позиций"""
    
    def __init__(self, account_balance: float, max_risk_per_trade: float = 0.02):
        self.account_balance = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = 0.1  # 10% от депозита
        self.current_exposure = 0.0
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                              risk_per_trade: Optional[float] = None,
                              volatility: Optional[float] = None) -> float:
        """Вычисляет размер позиции на основе риска"""
        if risk_per_trade is None:
            risk_per_trade = self.max_risk_per_trade
        
        # Базовый расчет размера позиции
        risk_amount = self.account_balance * risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return 0.0
        
        base_size = risk_amount / price_risk
        
        # Корректировка на волатильность
        if volatility is not None:
            volatility_adjustment = self._calculate_volatility_adjustment(volatility)
            base_size *= volatility_adjustment
        
        # Корректировка на текущую экспозицию
        exposure_adjustment = self._calculate_exposure_adjustment()
        base_size *= exposure_adjustment
        
        # Ограничения
        max_size = self.account_balance * 0.1 / entry_price  # Максимум 10% от депозита
        base_size = min(base_size, max_size)
        
        return max(0.0, base_size)
    
    def _calculate_volatility_adjustment(self, volatility: float) -> float:
        """Корректировка размера позиции на основе волатильности"""
        if volatility < 0.1:
            return 1.2  # Увеличиваем размер при низкой волатильности
        elif volatility > 0.3:
            return 0.7  # Уменьшаем размер при высокой волатильности
        else:
            return 1.0
    
    def _calculate_exposure_adjustment(self) -> float:
        """Корректировка на основе текущей экспозиции портфеля"""
        if self.current_exposure < 0.05:  # Менее 5%
            return 1.0
        elif self.current_exposure > 0.15:  # Более 15%
            return 0.5
        else:
            return 0.8
    
    def update_exposure(self, new_exposure: float):
        """Обновляет текущую экспозицию"""
        self.current_exposure = new_exposure

class DynamicStopLossManager:
    """Менеджер динамических стоп-лоссов"""
    
    def __init__(self):
        self.trailing_stops = {}
        self.break_even_stops = {}
        self.time_based_stops = {}
    
    def calculate_initial_stop_loss(self, entry_price: float, side: str, 
                                  volatility: float, atr: float) -> float:
        """Вычисляет начальный стоп-лосс"""
        # Базовый стоп на основе ATR
        atr_multiplier = 2.0
        base_stop_distance = atr * atr_multiplier
        
        # Корректировка на волатильность
        if volatility > 0.3:
            atr_multiplier = 3.0
        elif volatility < 0.1:
            atr_multiplier = 1.5
        
        stop_distance = atr * atr_multiplier
        
        if side == 'long':
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def update_trailing_stop(self, position: Position, current_price: float, 
                           atr: float, volatility: float) -> float:
        """Обновляет трейлинг стоп-лосс"""
        if position.side == 'long':
            # Для длинной позиции
            if current_price > position.entry_price:
                # Позиция в прибыли - активируем трейлинг
                new_stop = current_price - (atr * 1.5)
                return max(new_stop, position.stop_loss)
            else:
                # Позиция в убытке - оставляем стоп как есть
                return position.stop_loss
        else:
            # Для короткой позиции
            if current_price < position.entry_price:
                # Позиция в прибыли - активируем трейлинг
                new_stop = current_price + (atr * 1.5)
                return min(new_stop, position.stop_loss)
            else:
                # Позиция в убытке - оставляем стоп как есть
                return position.stop_loss
    
    def should_move_to_break_even(self, position: Position, current_price: float) -> bool:
        """Определяет, нужно ли переводить стоп в безубыток"""
        if position.side == 'long':
            profit_threshold = position.entry_price * 1.02  # 2% прибыли
            return current_price >= profit_threshold
        else:
            profit_threshold = position.entry_price * 0.98  # 2% прибыли
            return current_price <= profit_threshold
    
    def move_to_break_even(self, position: Position) -> float:
        """Переводит стоп-лосс в безубыток"""
        return position.entry_price

class PortfolioRiskManager:
    """Менеджер рисков портфеля"""
    
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions = {}
        self.trade_history = []
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
    
    def add_position(self, position: Position):
        """Добавляет позицию в портфель"""
        self.positions[position.id] = position
        self._update_exposure()
    
    def remove_position(self, position_id: str, exit_price: float, exit_time: datetime):
        """Удаляет позицию из портфеля"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Вычисляем P&L
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size
        
        # Обновляем баланс
        self.current_balance += pnl
        
        # Записываем сделку в историю
        trade_record = {
            'position_id': position_id,
            'symbol': position.symbol,
            'side': position.side,
            'size': position.size,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'entry_time': position.entry_time,
            'exit_time': exit_time,
            'duration': (exit_time - position.entry_time).total_seconds() / 3600  # в часах
        }
        
        self.trade_history.append(trade_record)
        
        # Обновляем метрики
        self._update_metrics(pnl)
        
        # Удаляем позицию
        del self.positions[position_id]
        self._update_exposure()
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Вычисляет метрики риска портфеля"""
        if not self.trade_history:
            return self._empty_risk_metrics()
        
        # Базовые метрики
        total_pnl = sum(trade['pnl'] for trade in self.trade_history)
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(self.trade_history) if self.trade_history else 0
        
        # Profit Factor
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Доходность и волатильность
        returns = [t['pnl'] / self.initial_balance for t in self.trade_history]
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        
        # Sharpe Ratio
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0
        
        # Sortino Ratio (учитывает только отрицательную волатильность)
        negative_returns = [r for r in returns if r < 0]
        downside_volatility = np.std(negative_returns) if negative_returns else 0
        sortino_ratio = avg_return / downside_volatility if downside_volatility > 0 else 0
        
        # Calmar Ratio
        annual_return = avg_return * 252  # Предполагаем 252 торговых дня
        calmar_ratio = annual_return / self.max_drawdown if self.max_drawdown > 0 else 0
        
        # Value at Risk
        var_95 = np.percentile(returns, 5) if len(returns) > 20 else 0
        var_99 = np.percentile(returns, 1) if len(returns) > 20 else 0
        
        return RiskMetrics(
            portfolio_value=self.current_balance,
            total_exposure=self._calculate_total_exposure(),
            max_drawdown=self.max_drawdown,
            current_drawdown=self._calculate_current_drawdown(),
            var_95=var_95,
            var_99=var_99,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_consecutive_losses=self.max_consecutive_losses,
            win_rate=win_rate,
            profit_factor=profit_factor
        )
    
    def should_reduce_risk(self) -> bool:
        """Определяет, нужно ли снижать риски"""
        metrics = self.calculate_risk_metrics()
        
        # Снижаем риски при:
        # 1. Большой просадке
        if metrics.current_drawdown > 0.1:  # 10%
            return True
        
        # 2. Много подряд идущих убытков
        if self.consecutive_losses >= 5:
            return True
        
        # 3. Низком коэффициенте Шарпа
        if metrics.sharpe_ratio < 0.5:
            return True
        
        # 4. Высоком VaR
        if metrics.var_95 < -0.05:  # 5% VaR
            return True
        
        return False
    
    def get_risk_adjustment_factor(self) -> float:
        """Возвращает коэффициент корректировки риска"""
        if not self.should_reduce_risk():
            return 1.0
        
        metrics = self.calculate_risk_metrics()
        
        # Базовый коэффициент
        factor = 1.0
        
        # Корректировка на просадку
        if metrics.current_drawdown > 0.05:
            factor *= 0.5
        
        # Корректировка на последовательные убытки
        if self.consecutive_losses >= 3:
            factor *= 0.7
        
        # Корректировка на Sharpe ratio
        if metrics.sharpe_ratio < 0:
            factor *= 0.3
        
        return max(0.1, factor)  # Минимум 10% от обычного размера
    
    def _update_exposure(self):
        """Обновляет общую экспозицию портфеля"""
        total_exposure = 0
        for position in self.positions.values():
            total_exposure += position.size * position.current_price
        self.current_exposure = total_exposure / self.current_balance
    
    def _calculate_total_exposure(self) -> float:
        """Вычисляет общую экспозицию"""
        return self.current_exposure
    
    def _calculate_current_drawdown(self) -> float:
        """Вычисляет текущую просадку"""
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
            return 0.0
        
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        return drawdown
    
    def _update_metrics(self, pnl: float):
        """Обновляет метрики после закрытия позиции"""
        # Обновляем пиковый баланс
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Обновляем максимальную просадку
        current_dd = self._calculate_current_drawdown()
        if current_dd > self.max_drawdown:
            self.max_drawdown = current_dd
        
        # Обновляем последовательные убытки
        if pnl < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        else:
            self.consecutive_losses = 0
    
    def _empty_risk_metrics(self) -> RiskMetrics:
        """Возвращает пустые метрики риска"""
        return RiskMetrics(
            portfolio_value=self.current_balance,
            total_exposure=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
            var_95=0.0,
            var_99=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_consecutive_losses=0,
            win_rate=0.0,
            profit_factor=0.0
        )

class AdvancedRiskManager:
    """Основной класс продвинутого управления рисками"""
    
    def __init__(self, initial_balance: float):
        self.portfolio_manager = PortfolioRiskManager(initial_balance)
        self.position_sizing = PositionSizingCalculator(initial_balance)
        self.stop_loss_manager = DynamicStopLossManager()
        self.risk_level = RiskLevel.MEDIUM
        self.max_positions = 5
        self.daily_loss_limit = 0.05  # 5% от депозита
        self.daily_loss = 0.0
        self.last_reset_date = datetime.now().date()
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss: float, volatility: float = None) -> float:
        """Вычисляет размер позиции с учетом всех факторов риска"""
        # Базовый размер позиции
        base_size = self.position_sizing.calculate_position_size(
            entry_price, stop_loss, volatility=volatility
        )
        
        # Корректировка на уровень риска
        risk_adjustment = self._get_risk_level_adjustment()
        base_size *= risk_adjustment
        
        # Корректировка на состояние портфеля
        portfolio_adjustment = self.portfolio_manager.get_risk_adjustment_factor()
        base_size *= portfolio_adjustment
        
        # Корректировка на количество позиций
        position_count_adjustment = self._get_position_count_adjustment()
        base_size *= position_count_adjustment
        
        # Корректировка на дневные убытки
        daily_loss_adjustment = self._get_daily_loss_adjustment()
        base_size *= daily_loss_adjustment
        
        return max(0.0, base_size)
    
    def can_open_position(self, symbol: str) -> bool:
        """Проверяет, можно ли открыть новую позицию"""
        # Проверяем лимит позиций
        if len(self.portfolio_manager.positions) >= self.max_positions:
            return False
        
        # Проверяем дневной лимит убытков
        if self.daily_loss >= self.daily_loss_limit:
            return False
        
        # Проверяем общее состояние портфеля
        if self.portfolio_manager.should_reduce_risk():
            return False
        
        return True
    
    def update_position(self, position_id: str, current_price: float, atr: float):
        """Обновляет позицию (цена, стоп-лосс)"""
        if position_id not in self.portfolio_manager.positions:
            return
        
        position = self.portfolio_manager.positions[position_id]
        position.current_price = current_price
        position.unrealized_pnl = self._calculate_unrealized_pnl(position)
        
        # Обновляем стоп-лосс
        new_stop_loss = self.stop_loss_manager.update_trailing_stop(
            position, current_price, atr, 0.2  # Предполагаем волатильность 20%
        )
        position.stop_loss = new_stop_loss
        
        # Проверяем перевод в безубыток
        if self.stop_loss_manager.should_move_to_break_even(position, current_price):
            position.stop_loss = self.stop_loss_manager.move_to_break_even(position)
    
    def should_close_position(self, position_id: str) -> Tuple[bool, str]:
        """Определяет, нужно ли закрыть позицию"""
        if position_id not in self.portfolio_manager.positions:
            return False, "Position not found"
        
        position = self.portfolio_manager.positions[position_id]
        
        # Проверяем стоп-лосс
        if position.side == 'long' and position.current_price <= position.stop_loss:
            return True, "Stop loss hit"
        
        if position.side == 'short' and position.current_price >= position.stop_loss:
            return True, "Stop loss hit"
        
        # Проверяем тейк-профит
        if position.side == 'long' and position.current_price >= position.take_profit:
            return True, "Take profit hit"
        
        if position.side == 'short' and position.current_price <= position.take_profit:
            return True, "Take profit hit"
        
        # Проверяем общие условия риска
        if self.portfolio_manager.should_reduce_risk():
            return True, "Risk reduction required"
        
        return False, "Position OK"
    
    def reset_daily_metrics(self):
        """Сбрасывает дневные метрики"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_loss = 0.0
            self.last_reset_date = current_date
    
    def _get_risk_level_adjustment(self) -> float:
        """Возвращает корректировку на уровень риска"""
        adjustments = {
            RiskLevel.VERY_LOW: 0.5,
            RiskLevel.LOW: 0.7,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 1.3,
            RiskLevel.VERY_HIGH: 1.5
        }
        return adjustments.get(self.risk_level, 1.0)
    
    def _get_position_count_adjustment(self) -> float:
        """Корректировка на количество открытых позиций"""
        position_count = len(self.portfolio_manager.positions)
        if position_count == 0:
            return 1.0
        elif position_count >= self.max_positions:
            return 0.0
        else:
            return 1.0 - (position_count / self.max_positions) * 0.3
    
    def _get_daily_loss_adjustment(self) -> float:
        """Корректировка на дневные убытки"""
        if self.daily_loss >= self.daily_loss_limit * 0.8:  # 80% от лимита
            return 0.5
        elif self.daily_loss >= self.daily_loss_limit * 0.5:  # 50% от лимита
            return 0.7
        else:
            return 1.0
    
    def _calculate_unrealized_pnl(self, position: Position) -> float:
        """Вычисляет нереализованную прибыль/убыток"""
        if position.side == 'long':
            return (position.current_price - position.entry_price) * position.size
        else:
            return (position.entry_price - position.current_price) * position.size

# Пример использования
if __name__ == "__main__":
    # Создаем менеджер рисков
    risk_manager = AdvancedRiskManager(initial_balance=10000)
    
    # Пример расчета размера позиции
    entry_price = 1.2000
    stop_loss = 1.1950
    volatility = 0.15
    
    position_size = risk_manager.calculate_position_size(
        symbol="EURUSD",
        entry_price=entry_price,
        stop_loss=stop_loss,
        volatility=volatility
    )
    
    print(f"Размер позиции: {position_size:.2f} лотов")
    print(f"Можно открыть позицию: {risk_manager.can_open_position('EURUSD')}")
    
    # Получаем метрики риска
    metrics = risk_manager.portfolio_manager.calculate_risk_metrics()
    print(f"Текущий баланс: {metrics.portfolio_value:.2f}")
    print(f"Максимальная просадка: {metrics.max_drawdown:.2%}")
    print(f"Коэффициент Шарпа: {metrics.sharpe_ratio:.2f}")