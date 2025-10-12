"""
Модуль адаптации к изменяющимся рыночным условиям.
Устраняет влияние рыночных изменений на результаты торгового робота.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


@dataclass
class MarketConditions:
    """Описание текущих рыночных условий"""
    volatility: float
    trend_strength: float
    liquidity: float
    correlation_matrix: Optional[np.ndarray] = None
    regime: str = "unknown"
    confidence: float = 0.0


class MarketAdaptation:
    """
    Класс для адаптации торгового робота к изменяющимся рыночным условиям.
    
    Основные методы адаптации:
    1. Динамическое изменение размера позиций
    2. Адаптивные стоп-лоссы и тейк-профиты
    3. Корректировка частоты торговли
    4. Фильтрация сигналов по рыночным условиям
    """
    
    def __init__(self, lookback_period: int = 100, adapt_speed: float = 0.1):
        """
        Args:
            lookback_period: Период для анализа исторических данных
            adapt_speed: Скорость адаптации (0.0 - 1.0)
        """
        self.lookback_period = lookback_period
        self.adapt_speed = adapt_speed
        self.current_conditions = None
        self.historical_conditions = []
        self.adaptation_params = self._initialize_params()
        
    def _initialize_params(self) -> Dict:
        """Инициализация параметров адаптации"""
        return {
            'position_size_multiplier': 1.0,
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0,
            'signal_threshold': 0.5,
            'max_exposure': 0.1,
            'trade_frequency': 1.0,
            'risk_adjustment': 1.0
        }
    
    def analyze_market_conditions(self, price_data: pd.DataFrame) -> MarketConditions:
        """
        Анализ текущих рыночных условий.
        
        Args:
            price_data: DataFrame с ценовыми данными (OHLCV)
            
        Returns:
            MarketConditions: Объект с описанием рыночных условий
        """
        # Расчет волатильности
        returns = price_data['close'].pct_change().dropna()
        volatility = self._calculate_adaptive_volatility(returns)
        
        # Определение силы тренда
        trend_strength = self._calculate_trend_strength(price_data['close'])
        
        # Оценка ликвидности
        liquidity = self._estimate_liquidity(price_data)
        
        # Определение рыночного режима
        regime, confidence = self._detect_market_regime(
            volatility, trend_strength, liquidity
        )
        
        conditions = MarketConditions(
            volatility=volatility,
            trend_strength=trend_strength,
            liquidity=liquidity,
            regime=regime,
            confidence=confidence
        )
        
        self.current_conditions = conditions
        self.historical_conditions.append(conditions)
        
        return conditions
    
    def _calculate_adaptive_volatility(self, returns: pd.Series) -> float:
        """
        Расчет адаптивной волатильности с использованием GARCH-подобного подхода.
        """
        # Стандартное отклонение
        std_dev = returns.std()
        
        # Экспоненциально взвешенная волатильность
        ewm_vol = returns.ewm(span=20).std().iloc[-1]
        
        # Парkinson volatility (использует high-low)
        if len(returns) > 0:
            realized_vol = np.sqrt(252 * returns.rolling(20).var().iloc[-1])
        else:
            realized_vol = std_dev * np.sqrt(252)
        
        # Комбинированная оценка
        volatility = 0.3 * std_dev + 0.4 * ewm_vol + 0.3 * realized_vol
        
        return volatility
    
    def _calculate_trend_strength(self, prices: pd.Series) -> float:
        """
        Оценка силы тренда используя множественные индикаторы.
        """
        if len(prices) < 20:
            return 0.0
            
        # ADX-подобный индикатор
        sma_20 = prices.rolling(20).mean()
        sma_50 = prices.rolling(50).mean() if len(prices) >= 50 else sma_20
        
        # Направление тренда
        trend_direction = np.sign(sma_20.iloc[-1] - sma_50.iloc[-1])
        
        # Сила тренда (0-1)
        price_above_sma = (prices.iloc[-20:] > sma_20.iloc[-20:]).mean()
        
        # Линейная регрессия для оценки наклона
        x = np.arange(min(20, len(prices)))
        y = prices.iloc[-len(x):].values
        slope, _, r_value, _, _ = stats.linregress(x, y)
        
        # Нормализация силы тренда
        trend_strength = abs(r_value) * price_above_sma
        
        return min(1.0, trend_strength)
    
    def _estimate_liquidity(self, price_data: pd.DataFrame) -> float:
        """
        Оценка ликвидности рынка на основе объемов и спредов.
        """
        if 'volume' not in price_data.columns:
            return 0.5  # Среднее значение при отсутствии данных
            
        # Средний объем
        avg_volume = price_data['volume'].rolling(20).mean().iloc[-1]
        
        # Волатильность объема
        volume_volatility = price_data['volume'].rolling(20).std().iloc[-1]
        
        # Оценка спреда (high-low как proxy)
        if 'high' in price_data.columns and 'low' in price_data.columns:
            spread_proxy = (
                (price_data['high'] - price_data['low']) / 
                price_data['close']
            ).rolling(20).mean().iloc[-1]
        else:
            spread_proxy = 0.001
        
        # Нормализованная ликвидность (больше объем и меньше спред = выше ликвидность)
        liquidity_score = avg_volume / (1 + volume_volatility) / (1 + spread_proxy * 100)
        
        # Нормализация к диапазону 0-1
        return min(1.0, liquidity_score / price_data['volume'].quantile(0.9))
    
    def _detect_market_regime(
        self, 
        volatility: float, 
        trend_strength: float, 
        liquidity: float
    ) -> Tuple[str, float]:
        """
        Определение рыночного режима на основе условий.
        
        Returns:
            Tuple[str, float]: (режим, уверенность)
        """
        regimes = {
            'trending': 0,
            'ranging': 0,
            'volatile': 0,
            'quiet': 0
        }
        
        # Логика определения режима
        if trend_strength > 0.6:
            regimes['trending'] = trend_strength
        else:
            regimes['ranging'] = 1 - trend_strength
            
        if volatility > 0.02:  # 2% дневная волатильность
            regimes['volatile'] = volatility * 10
        else:
            regimes['quiet'] = (1 - volatility * 10)
            
        # Корректировка на основе ликвидности
        for regime in regimes:
            regimes[regime] *= (0.5 + liquidity * 0.5)
            
        # Выбор доминирующего режима
        max_regime = max(regimes, key=regimes.get)
        confidence = regimes[max_regime] / sum(regimes.values())
        
        return max_regime, confidence
    
    def adapt_parameters(self, base_params: Dict) -> Dict:
        """
        Адаптация параметров торговой стратегии к текущим рыночным условиям.
        
        Args:
            base_params: Базовые параметры стратегии
            
        Returns:
            Dict: Адаптированные параметры
        """
        if self.current_conditions is None:
            return base_params
            
        adapted_params = base_params.copy()
        conditions = self.current_conditions
        
        # Адаптация размера позиции
        position_multiplier = self._adapt_position_size(conditions)
        adapted_params['position_size'] = (
            base_params.get('position_size', 1.0) * position_multiplier
        )
        
        # Адаптация стоп-лосса
        sl_multiplier = self._adapt_stop_loss(conditions)
        adapted_params['stop_loss'] = (
            base_params.get('stop_loss', 0.02) * sl_multiplier
        )
        
        # Адаптация тейк-профита
        tp_multiplier = self._adapt_take_profit(conditions)
        adapted_params['take_profit'] = (
            base_params.get('take_profit', 0.04) * tp_multiplier
        )
        
        # Адаптация порога сигналов
        adapted_params['signal_threshold'] = self._adapt_signal_threshold(conditions)
        
        # Обновление внутренних параметров с использованием EMA
        self._update_adaptation_params(
            position_multiplier, sl_multiplier, tp_multiplier
        )
        
        return adapted_params
    
    def _adapt_position_size(self, conditions: MarketConditions) -> float:
        """
        Адаптация размера позиции на основе рыночных условий.
        
        Уменьшаем позицию при:
        - Высокой волатильности
        - Низкой ликвидности
        - Неопределенном режиме
        """
        # Базовый множитель
        multiplier = 1.0
        
        # Корректировка на волатильность (обратная зависимость)
        vol_adjustment = 1.0 / (1.0 + conditions.volatility * 10)
        multiplier *= vol_adjustment
        
        # Корректировка на ликвидность (прямая зависимость)
        liquidity_adjustment = 0.5 + conditions.liquidity * 0.5
        multiplier *= liquidity_adjustment
        
        # Корректировка на уверенность в режиме
        confidence_adjustment = 0.6 + conditions.confidence * 0.4
        multiplier *= confidence_adjustment
        
        # Специальные корректировки для режимов
        regime_adjustments = {
            'trending': 1.2,    # Увеличиваем в тренде
            'ranging': 0.8,      # Уменьшаем в боковике
            'volatile': 0.6,     # Сильно уменьшаем при высокой волатильности
            'quiet': 1.0         # Нормальный размер в спокойном рынке
        }
        
        multiplier *= regime_adjustments.get(conditions.regime, 1.0)
        
        # Ограничения
        return np.clip(multiplier, 0.1, 2.0)
    
    def _adapt_stop_loss(self, conditions: MarketConditions) -> float:
        """
        Адаптация стоп-лосса к рыночным условиям.
        
        Увеличиваем стоп-лосс при:
        - Высокой волатильности
        - Сильном тренде
        """
        # Базовый множитель
        multiplier = 1.0
        
        # Расширение при высокой волатильности
        vol_adjustment = 1.0 + conditions.volatility * 5
        multiplier *= vol_adjustment
        
        # Корректировка на силу тренда
        if conditions.regime == 'trending':
            # В тренде можем позволить больший стоп
            multiplier *= (1.0 + conditions.trend_strength * 0.3)
        elif conditions.regime == 'ranging':
            # В боковике - более узкий стоп
            multiplier *= 0.8
            
        # Ограничения
        return np.clip(multiplier, 0.5, 3.0)
    
    def _adapt_take_profit(self, conditions: MarketConditions) -> float:
        """
        Адаптация тейк-профита к рыночным условиям.
        """
        # Базовый множитель
        multiplier = 1.0
        
        # Корректировка на волатильность
        vol_adjustment = 1.0 + conditions.volatility * 3
        multiplier *= vol_adjustment
        
        # Режим-специфичные корректировки
        if conditions.regime == 'trending':
            # В тренде - больший потенциал профита
            multiplier *= (1.2 + conditions.trend_strength * 0.5)
        elif conditions.regime == 'ranging':
            # В боковике - меньшие цели
            multiplier *= 0.7
        elif conditions.regime == 'volatile':
            # При высокой волатильности - больше возможностей
            multiplier *= 1.5
            
        # Соотношение риск/прибыль должно быть разумным
        return np.clip(multiplier, 0.5, 5.0)
    
    def _adapt_signal_threshold(self, conditions: MarketConditions) -> float:
        """
        Адаптация порога для торговых сигналов.
        
        Повышаем порог (более строгие условия) при:
        - Низкой уверенности в режиме
        - Высокой волатильности без тренда
        """
        # Базовый порог
        threshold = 0.5
        
        # Повышаем порог при низкой уверенности
        confidence_adjustment = 0.3 + conditions.confidence * 0.7
        threshold *= (2 - confidence_adjustment)
        
        # Корректировка для режимов
        if conditions.regime == 'volatile' and conditions.trend_strength < 0.3:
            # Опасные условия - повышаем порог
            threshold *= 1.3
        elif conditions.regime == 'trending' and conditions.confidence > 0.7:
            # Хорошие условия - можем снизить порог
            threshold *= 0.8
            
        return np.clip(threshold, 0.3, 0.9)
    
    def _update_adaptation_params(
        self, 
        pos_mult: float, 
        sl_mult: float, 
        tp_mult: float
    ):
        """
        Обновление внутренних параметров адаптации с использованием EMA.
        """
        alpha = self.adapt_speed
        
        self.adaptation_params['position_size_multiplier'] = (
            alpha * pos_mult + 
            (1 - alpha) * self.adaptation_params['position_size_multiplier']
        )
        
        self.adaptation_params['stop_loss_multiplier'] = (
            alpha * sl_mult + 
            (1 - alpha) * self.adaptation_params['stop_loss_multiplier']
        )
        
        self.adaptation_params['take_profit_multiplier'] = (
            alpha * tp_mult + 
            (1 - alpha) * self.adaptation_params['take_profit_multiplier']
        )
    
    def get_risk_adjustment(self) -> float:
        """
        Получение общего коэффициента корректировки риска.
        """
        if self.current_conditions is None:
            return 1.0
            
        # Комбинированная оценка риска
        risk_score = (
            self.current_conditions.volatility * 2 +
            (1 - self.current_conditions.liquidity) +
            (1 - self.current_conditions.confidence)
        ) / 4
        
        # Инвертируем для получения множителя (высокий риск = низкий множитель)
        risk_adjustment = 1.0 - risk_score
        
        return np.clip(risk_adjustment, 0.2, 1.0)
    
    def should_trade(self, signal_strength: float) -> bool:
        """
        Определение, следует ли торговать в текущих условиях.
        
        Args:
            signal_strength: Сила торгового сигнала (0-1)
            
        Returns:
            bool: True если условия подходящие для торговли
        """
        if self.current_conditions is None:
            return signal_strength > 0.5
            
        # Проверка порога сигнала
        threshold = self._adapt_signal_threshold(self.current_conditions)
        if signal_strength < threshold:
            return False
            
        # Дополнительные фильтры
        # Не торгуем при очень низкой ликвидности
        if self.current_conditions.liquidity < 0.2:
            return False
            
        # Не торгуем при экстремальной волатильности без тренда
        if (self.current_conditions.volatility > 0.05 and 
            self.current_conditions.trend_strength < 0.3):
            return False
            
        # Не торгуем при очень низкой уверенности в режиме
        if self.current_conditions.confidence < 0.3:
            return False
            
        return True
    
    def get_adaptation_report(self) -> Dict:
        """
        Получение отчета о текущих параметрах адаптации.
        """
        report = {
            'current_conditions': None,
            'adaptation_parameters': self.adaptation_params.copy(),
            'trading_allowed': False,
            'risk_level': 'unknown'
        }
        
        if self.current_conditions:
            report['current_conditions'] = {
                'volatility': round(self.current_conditions.volatility, 4),
                'trend_strength': round(self.current_conditions.trend_strength, 2),
                'liquidity': round(self.current_conditions.liquidity, 2),
                'regime': self.current_conditions.regime,
                'confidence': round(self.current_conditions.confidence, 2)
            }
            
            # Оценка уровня риска
            risk_adjustment = self.get_risk_adjustment()
            if risk_adjustment > 0.8:
                report['risk_level'] = 'low'
            elif risk_adjustment > 0.5:
                report['risk_level'] = 'medium'
            else:
                report['risk_level'] = 'high'
                
            report['trading_allowed'] = self.should_trade(0.6)  # Тестовый сигнал
            
        return report