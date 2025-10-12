"""
Система адаптации торгового робота к изменениям рынка
Включает детекцию волатильности, смены режимов рынка и динамическую настройку параметров
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Режимы рынка"""
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"

@dataclass
class MarketConditions:
    """Текущие условия рынка"""
    volatility: float
    trend_strength: float
    regime: MarketRegime
    volume_profile: float
    momentum: float
    support_resistance_strength: float
    timestamp: datetime

class VolatilityDetector:
    """Детектор волатильности рынка"""
    
    def __init__(self, lookback_period: int = 20):
        self.lookback_period = lookback_period
        self.volatility_history = []
        
    def calculate_volatility(self, prices: List[float]) -> float:
        """Вычисляет волатильность на основе стандартного отклонения доходности"""
        if len(prices) < 2:
            return 0.0
            
        returns = np.diff(np.log(prices))
        volatility = np.std(returns) * np.sqrt(252)  # Годовая волатильность
        return volatility
    
    def detect_volatility_regime(self, current_volatility: float) -> str:
        """Определяет режим волатильности"""
        if len(self.volatility_history) < self.lookback_period:
            return "insufficient_data"
            
        historical_vol = np.mean(self.volatility_history[-self.lookback_period:])
        volatility_ratio = current_volatility / historical_vol
        
        if volatility_ratio > 1.5:
            return "high_volatility"
        elif volatility_ratio < 0.7:
            return "low_volatility"
        else:
            return "normal_volatility"
    
    def update_volatility(self, prices: List[float]):
        """Обновляет историю волатильности"""
        current_vol = self.calculate_volatility(prices)
        self.volatility_history.append(current_vol)
        
        # Ограничиваем размер истории
        if len(self.volatility_history) > self.lookback_period * 2:
            self.volatility_history = self.volatility_history[-self.lookback_period:]

class TrendDetector:
    """Детектор тренда и его силы"""
    
    def __init__(self, short_period: int = 10, long_period: int = 30):
        self.short_period = short_period
        self.long_period = long_period
    
    def calculate_trend_strength(self, prices: List[float]) -> float:
        """Вычисляет силу тренда (0-1)"""
        if len(prices) < self.long_period:
            return 0.0
            
        short_ma = np.mean(prices[-self.short_period:])
        long_ma = np.mean(prices[-self.long_period:])
        
        # Нормализованная разность между скользящими средними
        price_range = max(prices[-self.long_period:]) - min(prices[-self.long_period:])
        if price_range == 0:
            return 0.0
            
        trend_strength = abs(short_ma - long_ma) / price_range
        return min(trend_strength, 1.0)
    
    def detect_trend_direction(self, prices: List[float]) -> str:
        """Определяет направление тренда"""
        if len(prices) < self.long_period:
            return "unknown"
            
        short_ma = np.mean(prices[-self.short_period:])
        long_ma = np.mean(prices[-self.long_period:])
        
        if short_ma > long_ma * 1.02:  # 2% порог
            return "uptrend"
        elif short_ma < long_ma * 0.98:
            return "downtrend"
        else:
            return "sideways"

class MarketRegimeDetector:
    """Детектор режима рынка"""
    
    def __init__(self):
        self.volatility_detector = VolatilityDetector()
        self.trend_detector = TrendDetector()
        self.regime_history = []
    
    def detect_regime(self, prices: List[float], volume: Optional[List[float]] = None) -> MarketRegime:
        """Определяет текущий режим рынка"""
        # Обновляем волатильность
        self.volatility_detector.update_volatility(prices)
        current_volatility = self.volatility_detector.volatility_history[-1]
        volatility_regime = self.volatility_detector.detect_volatility_regime(current_volatility)
        
        # Определяем силу тренда
        trend_strength = self.trend_detector.calculate_trend_strength(prices)
        trend_direction = self.trend_detector.detect_trend_direction(prices)
        
        # Логика определения режима
        if volatility_regime == "high_volatility":
            if trend_strength > 0.6:
                return MarketRegime.BREAKOUT
            else:
                return MarketRegime.HIGH_VOLATILITY
        elif volatility_regime == "low_volatility":
            if trend_strength < 0.3:
                return MarketRegime.RANGING
            else:
                return MarketRegime.TRENDING
        else:
            if trend_strength > 0.5:
                return MarketRegime.TRENDING
            else:
                return MarketRegime.RANGING

class AdaptiveParameterManager:
    """Менеджер адаптивных параметров торгового робота"""
    
    def __init__(self):
        self.base_parameters = {
            'stop_loss_pct': 0.02,  # 2%
            'take_profit_pct': 0.04,  # 4%
            'position_size': 0.1,  # 10% от депозита
            'max_positions': 3,
            'rsi_period': 14,
            'ma_period': 20
        }
        
        self.regime_parameters = {
            MarketRegime.TRENDING: {
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.06,
                'position_size': 0.15,
                'max_positions': 2
            },
            MarketRegime.RANGING: {
                'stop_loss_pct': 0.015,
                'take_profit_pct': 0.03,
                'position_size': 0.08,
                'max_positions': 4
            },
            MarketRegime.HIGH_VOLATILITY: {
                'stop_loss_pct': 0.04,
                'take_profit_pct': 0.08,
                'position_size': 0.05,
                'max_positions': 1
            },
            MarketRegime.LOW_VOLATILITY: {
                'stop_loss_pct': 0.01,
                'take_profit_pct': 0.02,
                'position_size': 0.12,
                'max_positions': 5
            },
            MarketRegime.BREAKOUT: {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.1,
                'position_size': 0.2,
                'max_positions': 1
            }
        }
    
    def get_adaptive_parameters(self, regime: MarketRegime, volatility: float) -> Dict:
        """Возвращает адаптированные параметры для текущего режима рынка"""
        base_params = self.base_parameters.copy()
        regime_params = self.regime_parameters.get(regime, {})
        
        # Применяем параметры режима
        for key, value in regime_params.items():
            base_params[key] = value
        
        # Дополнительная адаптация на основе волатильности
        if volatility > 0.3:  # Высокая волатильность
            base_params['stop_loss_pct'] *= 1.5
            base_params['position_size'] *= 0.7
        elif volatility < 0.1:  # Низкая волатильность
            base_params['stop_loss_pct'] *= 0.7
            base_params['position_size'] *= 1.2
        
        return base_params

class MarketAdaptationSystem:
    """Основная система адаптации к изменениям рынка"""
    
    def __init__(self):
        self.regime_detector = MarketRegimeDetector()
        self.parameter_manager = AdaptiveParameterManager()
        self.current_conditions = None
        self.adaptation_history = []
    
    def analyze_market_conditions(self, prices: List[float], volume: Optional[List[float]] = None) -> MarketConditions:
        """Анализирует текущие условия рынка"""
        # Определяем режим рынка
        regime = self.regime_detector.detect_regime(prices, volume)
        
        # Вычисляем метрики
        volatility = self.regime_detector.volatility_detector.calculate_volatility(prices)
        trend_strength = self.regime_detector.trend_detector.calculate_trend_strength(prices)
        
        # Упрощенные метрики (в реальной реализации нужны более сложные алгоритмы)
        volume_profile = np.mean(volume) if volume else 1.0
        momentum = self._calculate_momentum(prices)
        support_resistance = self._calculate_support_resistance_strength(prices)
        
        conditions = MarketConditions(
            volatility=volatility,
            trend_strength=trend_strength,
            regime=regime,
            volume_profile=volume_profile,
            momentum=momentum,
            support_resistance_strength=support_resistance,
            timestamp=datetime.now()
        )
        
        self.current_conditions = conditions
        return conditions
    
    def get_adaptive_parameters(self) -> Dict:
        """Возвращает адаптированные параметры для текущих условий"""
        if not self.current_conditions:
            return self.parameter_manager.base_parameters
        
        return self.parameter_manager.get_adaptive_parameters(
            self.current_conditions.regime,
            self.current_conditions.volatility
        )
    
    def should_trade(self) -> bool:
        """Определяет, стоит ли торговать в текущих условиях"""
        if not self.current_conditions:
            return False
        
        # Логика принятия решения о торговле
        conditions = self.current_conditions
        
        # Не торгуем при экстремально высокой волатильности
        if conditions.volatility > 0.5:
            return False
        
        # Не торгуем при очень слабом тренде и низкой волатильности
        if conditions.trend_strength < 0.2 and conditions.volatility < 0.05:
            return False
        
        # Торгуем в трендовых режимах
        if conditions.regime in [MarketRegime.TRENDING, MarketRegime.BREAKOUT]:
            return True
        
        # Торгуем в ranging режиме при достаточной волатильности
        if conditions.regime == MarketRegime.RANGING and conditions.volatility > 0.1:
            return True
        
        return False
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Вычисляет момент рынка"""
        if len(prices) < 10:
            return 0.0
        
        # RSI-подобный индикатор
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) == 0 or len(losses) == 0:
            return 0.0
        
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
        
        if avg_loss == 0:
            return 1.0
        
        rs = avg_gain / avg_loss
        momentum = 1 - (1 / (1 + rs))
        
        return momentum
    
    def _calculate_support_resistance_strength(self, prices: List[float]) -> float:
        """Вычисляет силу уровней поддержки/сопротивления"""
        if len(prices) < 20:
            return 0.0
        
        # Упрощенный алгоритм поиска уровней
        highs = []
        lows = []
        
        for i in range(2, len(prices) - 2):
            if (prices[i] > prices[i-1] and prices[i] > prices[i+1] and 
                prices[i] > prices[i-2] and prices[i] > prices[i+2]):
                highs.append(prices[i])
            elif (prices[i] < prices[i-1] and prices[i] < prices[i+1] and 
                  prices[i] < prices[i-2] and prices[i] < prices[i+2]):
                lows.append(prices[i])
        
        # Вычисляем плотность уровней
        price_range = max(prices) - min(prices)
        if price_range == 0:
            return 0.0
        
        level_density = (len(highs) + len(lows)) / len(prices)
        return min(level_density * 10, 1.0)  # Нормализация

# Пример использования
if __name__ == "__main__":
    # Создаем систему адаптации
    adaptation_system = MarketAdaptationSystem()
    
    # Симулируем данные цен
    np.random.seed(42)
    prices = [100 + i * 0.1 + np.random.normal(0, 0.5) for i in range(100)]
    volume = [1000 + np.random.normal(0, 100) for _ in range(100)]
    
    # Анализируем условия рынка
    conditions = adaptation_system.analyze_market_conditions(prices, volume)
    
    print(f"Режим рынка: {conditions.regime.value}")
    print(f"Волатильность: {conditions.volatility:.4f}")
    print(f"Сила тренда: {conditions.trend_strength:.4f}")
    print(f"Стоит ли торговать: {adaptation_system.should_trade()}")
    
    # Получаем адаптированные параметры
    params = adaptation_system.get_adaptive_parameters()
    print(f"Адаптированные параметры: {params}")