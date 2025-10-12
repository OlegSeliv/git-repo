"""
Маркет-нейтральная торговая стратегия с нормализацией волатильности.
Устраняет влияние общих рыночных изменений на результаты робота.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class MarketState:
    """Состояние рынка для нормализации сигналов"""
    volatility: float
    trend: float
    regime: str  # 'trending', 'ranging', 'volatile'
    normalized_price: float


class MarketNeutralStrategy:
    """
    Стратегия с устранением влияния рыночных изменений через:
    1. Нормализацию по волатильности (volatility-adjusted)
    2. Market regime detection (определение рыночного режима)
    3. Relative strength вместо абсолютных цен
    4. Rolling window normalization
    """
    
    def __init__(
        self,
        lookback_period: int = 20,
        volatility_window: int = 14,
        regime_threshold: float = 0.5,
        use_z_score: bool = True
    ):
        self.lookback_period = lookback_period
        self.volatility_window = volatility_window
        self.regime_threshold = regime_threshold
        self.use_z_score = use_z_score
        
        self.price_history = []
        self.returns_history = []
        
    def calculate_volatility(self, prices: np.ndarray) -> float:
        """
        Расчет волатильности (ATR-подобный индикатор)
        Используется для нормализации сигналов
        """
        if len(prices) < 2:
            return 1.0
            
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        
        return max(volatility, 0.001)  # Избегаем деления на 0
    
    def detect_market_regime(self, prices: np.ndarray) -> str:
        """
        Определение режима рынка:
        - trending: сильный тренд (up/down)
        - ranging: боковик
        - volatile: высокая волатильность без тренда
        """
        if len(prices) < self.lookback_period:
            return 'ranging'
        
        # Linear regression для определения тренда
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)
        
        # R-squared для силы тренда
        y_pred = slope * x + np.mean(prices)
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        volatility = self.calculate_volatility(prices)
        
        if r_squared > self.regime_threshold and abs(slope) > volatility * 0.1:
            return 'trending'
        elif volatility > 0.02:  # 2% daily volatility
            return 'volatile'
        else:
            return 'ranging'
    
    def normalize_price(self, prices: np.ndarray) -> np.ndarray:
        """
        Нормализация цен для устранения влияния абсолютного уровня
        Использует Z-score или min-max нормализацию
        """
        if len(prices) < 2:
            return prices
        
        if self.use_z_score:
            # Z-score нормализация (стандартизация)
            mean = np.mean(prices)
            std = np.std(prices)
            if std > 0:
                return (prices - mean) / std
            return prices - mean
        else:
            # Min-max нормализация к диапазону [0, 1]
            min_price = np.min(prices)
            max_price = np.max(prices)
            if max_price > min_price:
                return (prices - min_price) / (max_price - min_price)
            return np.zeros_like(prices)
    
    def calculate_relative_strength(
        self, 
        prices: np.ndarray, 
        benchmark: Optional[np.ndarray] = None
    ) -> float:
        """
        Относительная сила относительно бенчмарка или собственной истории
        Устраняет влияние общего движения рынка
        """
        if len(prices) < 2:
            return 0.0
        
        # Доходность актива
        asset_return = (prices[-1] - prices[0]) / prices[0]
        
        if benchmark is not None and len(benchmark) >= 2:
            # Относительная доходность vs бенчмарк
            benchmark_return = (benchmark[-1] - benchmark[0]) / benchmark[0]
            return asset_return - benchmark_return
        else:
            # Нормализованная доходность
            volatility = self.calculate_volatility(prices)
            return asset_return / volatility if volatility > 0 else 0.0
    
    def get_market_state(self, prices: np.ndarray) -> MarketState:
        """
        Получение полного состояния рынка для принятия решений
        """
        volatility = self.calculate_volatility(prices)
        regime = self.detect_market_regime(prices)
        
        # Тренд (slope линейной регрессии, нормализованный)
        if len(prices) >= 2:
            x = np.arange(len(prices))
            slope, _ = np.polyfit(x, prices, 1)
            trend = slope / np.mean(prices) if np.mean(prices) > 0 else 0
        else:
            trend = 0.0
        
        # Нормализованная цена
        normalized_prices = self.normalize_price(prices)
        normalized_price = normalized_prices[-1] if len(normalized_prices) > 0 else 0.0
        
        return MarketState(
            volatility=volatility,
            trend=trend,
            regime=regime,
            normalized_price=normalized_price
        )
    
    def adjust_signal_for_market(
        self, 
        raw_signal: float, 
        market_state: MarketState
    ) -> float:
        """
        Корректировка сигнала с учетом состояния рынка
        
        Args:
            raw_signal: Сырой сигнал от стратегии (-1 до 1)
            market_state: Текущее состояние рынка
            
        Returns:
            Скорректированный сигнал
        """
        adjusted_signal = raw_signal
        
        # 1. Нормализация по волатильности
        # В периоды высокой волатильности уменьшаем размер позиции
        volatility_adjustment = 1.0 / (1.0 + market_state.volatility * 10)
        adjusted_signal *= volatility_adjustment
        
        # 2. Корректировка по режиму рынка
        if market_state.regime == 'volatile':
            # В волатильном рынке снижаем агрессивность
            adjusted_signal *= 0.5
        elif market_state.regime == 'ranging':
            # В боковике можно быть более агрессивным
            adjusted_signal *= 1.2
        
        # 3. Корректировка по тренду (контр-трендовая для нейтральности)
        # Если сильный тренд вверх, снижаем длинные позиции
        if abs(market_state.trend) > 0.01:
            trend_adjustment = 1.0 - (market_state.trend * 50)
            adjusted_signal *= np.clip(trend_adjustment, 0.5, 1.5)
        
        return np.clip(adjusted_signal, -1.0, 1.0)


class PositionSizer:
    """
    Управление размером позиций с учетом рыночных условий
    """
    
    def __init__(
        self,
        max_position_size: float = 1.0,
        risk_per_trade: float = 0.02,  # 2% риск на сделку
        use_kelly: bool = False
    ):
        self.max_position_size = max_position_size
        self.risk_per_trade = risk_per_trade
        self.use_kelly = use_kelly
        
        self.win_rate = 0.5  # Initial assumption
        self.avg_win = 1.0
        self.avg_loss = 1.0
        
    def update_statistics(self, trades: List[Dict]):
        """
        Обновление статистики для Kelly criterion
        """
        if len(trades) < 10:
            return
        
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
        
        if len(wins) + len(losses) > 0:
            self.win_rate = len(wins) / (len(wins) + len(losses))
        
        if len(wins) > 0:
            self.avg_win = np.mean(wins)
        if len(losses) > 0:
            self.avg_loss = np.mean(losses)
    
    def calculate_position_size(
        self,
        signal_strength: float,
        market_state: MarketState,
        account_balance: float,
        current_price: float
    ) -> float:
        """
        Расчет оптимального размера позиции
        
        Returns:
            Размер позиции (в единицах актива)
        """
        if self.use_kelly and self.avg_loss > 0:
            # Kelly Criterion: f* = (p*W - (1-p)*L) / (W*L)
            # Упрощенная формула: f* = W - (1-p)/p
            win_loss_ratio = self.avg_win / self.avg_loss
            kelly_fraction = (self.win_rate * win_loss_ratio - (1 - self.win_rate)) / win_loss_ratio
            kelly_fraction = max(0, kelly_fraction) * 0.25  # Используем 1/4 Kelly для консерватизма
            
            size_fraction = kelly_fraction
        else:
            # Fixed fractional position sizing
            size_fraction = self.risk_per_trade
        
        # Корректировка на волатильность
        volatility_adjustment = 1.0 / (1.0 + market_state.volatility * 5)
        size_fraction *= volatility_adjustment
        
        # Корректировка на силу сигнала
        size_fraction *= abs(signal_strength)
        
        # Максимальный размер позиции
        size_fraction = min(size_fraction, self.max_position_size)
        
        # Конвертация в единицы актива
        dollar_size = account_balance * size_fraction
        position_size = dollar_size / current_price if current_price > 0 else 0
        
        return position_size


class MarketNeutralPortfolio:
    """
    Маркет-нейтральный портфель через хеджирование
    """
    
    def __init__(self, hedge_ratio: float = 1.0):
        self.hedge_ratio = hedge_ratio
        self.positions = {}
        
    def add_position(
        self,
        symbol: str,
        size: float,
        side: str,  # 'long' or 'short'
        hedge_symbol: Optional[str] = None
    ):
        """
        Добавление позиции с автоматическим хеджированием
        """
        self.positions[symbol] = {
            'size': size,
            'side': side,
            'hedge_symbol': hedge_symbol
        }
        
        # Автоматическое хеджирование индексом/ETF
        if hedge_symbol:
            hedge_side = 'short' if side == 'long' else 'long'
            hedge_size = size * self.hedge_ratio
            
            self.positions[f"{symbol}_hedge"] = {
                'size': hedge_size,
                'side': hedge_side,
                'hedge_symbol': hedge_symbol
            }
    
    def calculate_net_exposure(self) -> float:
        """
        Расчет чистой рыночной экспозиции (должна быть близка к 0)
        """
        net_exposure = 0.0
        
        for pos in self.positions.values():
            size = pos['size']
            if pos['side'] == 'short':
                size = -size
            net_exposure += size
        
        return net_exposure
    
    def rebalance(self, target_exposure: float = 0.0):
        """
        Ребалансировка для поддержания маркет-нейтральности
        """
        current_exposure = self.calculate_net_exposure()
        
        if abs(current_exposure - target_exposure) > 0.1:
            # Необходима корректировка
            adjustment = current_exposure - target_exposure
            # Распределяем корректировку по хедж-позициям
            return adjustment
        
        return 0.0


def example_usage():
    """
    Пример использования маркет-нейтральной стратегии
    """
    # Создаем стратегию
    strategy = MarketNeutralStrategy(
        lookback_period=20,
        volatility_window=14,
        use_z_score=True
    )
    
    # Генерируем тестовые данные
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 2)
    
    # Получаем состояние рынка
    market_state = strategy.get_market_state(prices)
    
    print("=== Анализ рыночного состояния ===")
    print(f"Волатильность: {market_state.volatility:.4f}")
    print(f"Тренд: {market_state.trend:.4f}")
    print(f"Режим рынка: {market_state.regime}")
    print(f"Нормализованная цена: {market_state.normalized_price:.4f}")
    
    # Пример корректировки сигнала
    raw_signal = 0.8  # Сильный сигнал на покупку
    adjusted_signal = strategy.adjust_signal_for_market(raw_signal, market_state)
    
    print(f"\n=== Корректировка сигнала ===")
    print(f"Сырой сигнал: {raw_signal:.4f}")
    print(f"Скорректированный сигнал: {adjusted_signal:.4f}")
    print(f"Изменение: {(adjusted_signal/raw_signal - 1)*100:.2f}%")
    
    # Расчет размера позиции
    position_sizer = PositionSizer(risk_per_trade=0.02)
    position_size = position_sizer.calculate_position_size(
        signal_strength=adjusted_signal,
        market_state=market_state,
        account_balance=10000,
        current_price=prices[-1]
    )
    
    print(f"\n=== Размер позиции ===")
    print(f"Размер (единиц): {position_size:.4f}")
    print(f"Стоимость: ${position_size * prices[-1]:.2f}")
    print(f"% от капитала: {(position_size * prices[-1] / 10000 * 100):.2f}%")


if __name__ == "__main__":
    example_usage()
