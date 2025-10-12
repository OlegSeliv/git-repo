"""
Главный модуль адаптивного торгового робота.
Интегрирует все компоненты для создания устойчивой к изменениям рынка системы.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json
from enum import Enum

# Импорт наших модулей
from market_adaptation import MarketAdaptation
from optimal_timing import OptimalTimingAnalyzer
from market_regime_detector import MarketRegimeDetector
from dynamic_parameters import DynamicParameterOptimizer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    """Направление сделки"""
    LONG = 1
    SHORT = -1
    NEUTRAL = 0


@dataclass
class TradeSignal:
    """Торговый сигнал"""
    timestamp: datetime
    direction: TradeDirection
    strength: float  # 0-1
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    regime: str
    timing_score: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class Position:
    """Открытая позиция"""
    id: str
    timestamp: datetime
    direction: TradeDirection
    entry_price: float
    current_price: float
    size: float
    stop_loss: float
    take_profit: float
    trailing_stop: Optional[float] = None
    profit_loss: float = 0.0
    duration: int = 0
    metadata: Dict = field(default_factory=dict)


class AdaptiveTradingRobot:
    """
    Адаптивный торговый робот, устойчивый к изменениям рынка.
    
    Основные возможности:
    1. Автоматическая адаптация к рыночным режимам
    2. Оптимальный выбор времени запуска
    3. Динамическая оптимизация параметров
    4. Комплексный риск-менеджмент
    """
    
    def __init__(self,
                 symbol: str = "EURUSD",
                 initial_capital: float = 10000,
                 max_risk_per_trade: float = 0.02,
                 strategy_type: str = 'trend_following'):
        """
        Args:
            symbol: Торговый инструмент
            initial_capital: Начальный капитал
            max_risk_per_trade: Максимальный риск на сделку
            strategy_type: Тип стратегии
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.strategy_type = strategy_type
        
        # Инициализация компонентов
        self.market_adapter = MarketAdaptation(lookback_period=100)
        self.timing_analyzer = OptimalTimingAnalyzer(symbol=symbol)
        self.regime_detector = MarketRegimeDetector()
        self.parameter_optimizer = DynamicParameterOptimizer()
        
        # Управление позициями
        self.positions: List[Position] = []
        self.closed_positions: List[Dict] = []
        self.pending_signals: List[TradeSignal] = []
        
        # История и статистика
        self.trade_history: List[Dict] = []
        self.performance_history = []
        self.equity_curve = [initial_capital]
        
        # Текущее состояние
        self.current_regime = None
        self.current_timing_score = None
        self.current_parameters = {}
        self.is_active = False
        self.bars_processed = 0
        
        # Настройки
        self.settings = {
            'max_positions': 3,
            'use_timing_filter': True,
            'use_regime_filter': True,
            'use_adaptive_parameters': True,
            'min_timing_score': 0.5,
            'reoptimize_frequency': 100,
            'max_correlation': 0.7
        }
        
        logger.info(f"Инициализирован адаптивный торговый робот для {symbol}")
    
    def start(self, price_data: pd.DataFrame, start_time: Optional[datetime] = None):
        """
        Запуск торгового робота.
        
        Args:
            price_data: Исторические данные для анализа
            start_time: Время запуска (None = оптимальное время)
        """
        logger.info("Запуск торгового робота...")
        
        # Анализ оптимального времени запуска
        if start_time is None and self.settings['use_timing_filter']:
            timing_score = self.timing_analyzer.analyze_timing(
                price_data, 
                self.strategy_type
            )
            
            if timing_score.recommendation == 'avoid':
                logger.warning(f"Не рекомендуется запуск в текущее время. Score: {timing_score.score:.2f}")
                self.is_active = False
                return
            elif timing_score.recommendation == 'wait':
                logger.info(f"Рекомендуется подождать. Score: {timing_score.score:.2f}")
                # Поиск лучшего окна
                best_windows = self.timing_analyzer.find_best_launch_windows(
                    price_data, 
                    self.strategy_type
                )
                if best_windows:
                    logger.info(f"Лучшее время для запуска: {best_windows[0].timestamp}")
                self.is_active = False
                return
            else:
                logger.info(f"Хорошее время для запуска. Score: {timing_score.score:.2f}")
                self.current_timing_score = timing_score
                
        self.is_active = True
        logger.info("Робот активирован и готов к торговле")
    
    def process_bar(self, price_bar: pd.Series) -> Optional[TradeSignal]:
        """
        Обработка нового бара данных.
        
        Args:
            price_bar: Новый бар с данными OHLCV
            
        Returns:
            TradeSignal если сгенерирован сигнал
        """
        if not self.is_active:
            return None
            
        self.bars_processed += 1
        
        # Обновление позиций
        self._update_positions(price_bar)
        
        # Проверка необходимости реоптимизации
        if self.bars_processed % self.settings['reoptimize_frequency'] == 0:
            self._reoptimize_parameters(price_bar)
            
        # Анализ рыночных условий
        market_conditions = self._analyze_market(price_bar)
        
        # Генерация сигнала
        signal = self._generate_signal(price_bar, market_conditions)
        
        # Фильтрация сигнала
        if signal and self._filter_signal(signal, market_conditions):
            # Управление рисками
            signal = self._apply_risk_management(signal)
            
            # Исполнение сигнала
            if self._can_open_position(signal):
                self._open_position(signal)
                return signal
                
        return None
    
    def _analyze_market(self, price_data: pd.DataFrame) -> Dict:
        """
        Комплексный анализ рыночных условий.
        """
        analysis = {}
        
        # Определение режима рынка
        if self.settings['use_regime_filter']:
            regime = self.regime_detector.detect_regime(price_data)
            self.current_regime = regime
            analysis['regime'] = regime
            logger.debug(f"Рыночный режим: {regime.regime_type} (уверенность: {regime.confidence:.2f})")
            
        # Анализ рыночных условий для адаптации
        conditions = self.market_adapter.analyze_market_conditions(price_data)
        analysis['conditions'] = conditions
        
        # Оценка времени
        if self.settings['use_timing_filter']:
            timing_score = self.timing_analyzer.analyze_timing(
                price_data,
                self.strategy_type,
                datetime.now()
            )
            self.current_timing_score = timing_score
            analysis['timing'] = timing_score
            
        return analysis
    
    def _generate_signal(self, 
                        price_bar: pd.Series,
                        market_analysis: Dict) -> Optional[TradeSignal]:
        """
        Генерация торгового сигнала на основе стратегии.
        """
        # Получаем адаптированные параметры
        if self.settings['use_adaptive_parameters']:
            params = self.market_adapter.adapt_parameters(self.current_parameters)
        else:
            params = self.current_parameters
            
        # Расчет индикаторов с адаптивными параметрами
        indicators = self._calculate_indicators(price_bar, params)
        
        # Определение направления и силы сигнала
        direction, strength = self._evaluate_strategy(indicators, params)
        
        if direction == TradeDirection.NEUTRAL or strength < params.get('signal_threshold', 0.5):
            return None
            
        # Расчет уровней входа и выхода
        entry_price = price_bar['close']
        atr = self._calculate_atr(price_bar)
        
        if direction == TradeDirection.LONG:
            stop_loss = entry_price - atr * params.get('stop_loss_atr_mult', 2.0)
            take_profit = entry_price + atr * params.get('take_profit_atr_mult', 3.0)
        else:
            stop_loss = entry_price + atr * params.get('stop_loss_atr_mult', 2.0)
            take_profit = entry_price - atr * params.get('take_profit_atr_mult', 3.0)
            
        # Расчет размера позиции
        position_size = self._calculate_position_size(
            entry_price, 
            stop_loss, 
            params.get('position_size_pct', 0.02)
        )
        
        # Расчет уверенности
        confidence = self._calculate_signal_confidence(
            strength,
            market_analysis,
            indicators
        )
        
        signal = TradeSignal(
            timestamp=datetime.now(),
            direction=direction,
            strength=strength,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            regime=self.current_regime.regime_type if self.current_regime else 'unknown',
            timing_score=self.current_timing_score.score if self.current_timing_score else 0.5,
            metadata={
                'indicators': indicators,
                'parameters': params
            }
        )
        
        return signal
    
    def _calculate_indicators(self, price_data: pd.DataFrame, params: Dict) -> Dict:
        """
        Расчет технических индикаторов.
        """
        indicators = {}
        
        # Moving Averages
        ma_fast = int(params.get('ma_fast_period', 20))
        ma_slow = int(params.get('ma_slow_period', 50))
        
        indicators['ma_fast'] = price_data['close'].rolling(ma_fast).mean().iloc[-1]
        indicators['ma_slow'] = price_data['close'].rolling(ma_slow).mean().iloc[-1]
        indicators['ma_cross'] = indicators['ma_fast'] - indicators['ma_slow']
        
        # RSI
        rsi_period = int(params.get('rsi_period', 14))
        indicators['rsi'] = self._calculate_rsi(price_data['close'], rsi_period)
        
        # Momentum
        indicators['momentum'] = price_data['close'].pct_change(10).iloc[-1]
        
        # Volatility
        indicators['volatility'] = price_data['close'].pct_change().rolling(20).std().iloc[-1]
        
        # Volume (если доступен)
        if 'volume' in price_data.columns:
            indicators['volume_ratio'] = (
                price_data['volume'].iloc[-1] / 
                price_data['volume'].rolling(20).mean().iloc[-1]
            )
        else:
            indicators['volume_ratio'] = 1.0
            
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        Расчет RSI.
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """
        Расчет ATR.
        """
        if not all(col in price_data.columns for col in ['high', 'low', 'close']):
            # Упрощенный ATR на основе close
            return price_data['close'].pct_change().rolling(period).std().iloc[-1] * price_data['close'].iloc[-1]
            
        high = price_data['high']
        low = price_data['low']
        close = price_data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr
    
    def _evaluate_strategy(self, 
                          indicators: Dict,
                          params: Dict) -> Tuple[TradeDirection, float]:
        """
        Оценка стратегии и генерация направления сигнала.
        """
        if self.strategy_type == 'trend_following':
            return self._trend_following_strategy(indicators, params)
        elif self.strategy_type == 'mean_reversion':
            return self._mean_reversion_strategy(indicators, params)
        elif self.strategy_type == 'momentum':
            return self._momentum_strategy(indicators, params)
        else:
            return TradeDirection.NEUTRAL, 0.0
    
    def _trend_following_strategy(self,
                                 indicators: Dict,
                                 params: Dict) -> Tuple[TradeDirection, float]:
        """
        Трендовая стратегия.
        """
        strength = 0.0
        direction = TradeDirection.NEUTRAL
        
        # MA crossover
        if indicators['ma_cross'] > 0:
            direction = TradeDirection.LONG
            strength += 0.3
        elif indicators['ma_cross'] < 0:
            direction = TradeDirection.SHORT
            strength += 0.3
            
        # RSI confirmation
        rsi = indicators['rsi']
        if direction == TradeDirection.LONG and 40 < rsi < 70:
            strength += 0.2
        elif direction == TradeDirection.SHORT and 30 < rsi < 60:
            strength += 0.2
            
        # Momentum confirmation
        if direction == TradeDirection.LONG and indicators['momentum'] > 0:
            strength += 0.3
        elif direction == TradeDirection.SHORT and indicators['momentum'] < 0:
            strength += 0.3
            
        # Volume confirmation
        if indicators['volume_ratio'] > 1.2:
            strength += 0.2
            
        # Применение трендового фильтра
        trend_filter = params.get('trend_filter_strength', 0.5)
        strength *= (0.5 + trend_filter * 0.5)
        
        return direction, min(1.0, strength)
    
    def _mean_reversion_strategy(self,
                                indicators: Dict,
                                params: Dict) -> Tuple[TradeDirection, float]:
        """
        Стратегия возврата к среднему.
        """
        strength = 0.0
        direction = TradeDirection.NEUTRAL
        
        rsi = indicators['rsi']
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)
        
        # RSI экстремумы
        if rsi < rsi_oversold:
            direction = TradeDirection.LONG
            strength = (rsi_oversold - rsi) / rsi_oversold
        elif rsi > rsi_overbought:
            direction = TradeDirection.SHORT
            strength = (rsi - rsi_overbought) / (100 - rsi_overbought)
            
        # Подтверждение волатильностью
        if indicators['volatility'] < params.get('max_volatility', 0.03):
            strength *= 1.2
            
        return direction, min(1.0, strength)
    
    def _momentum_strategy(self,
                          indicators: Dict,
                          params: Dict) -> Tuple[TradeDirection, float]:
        """
        Моментум стратегия.
        """
        momentum = indicators['momentum']
        strength = abs(momentum) * 10  # Масштабирование
        
        if momentum > 0.01:
            direction = TradeDirection.LONG
        elif momentum < -0.01:
            direction = TradeDirection.SHORT
        else:
            direction = TradeDirection.NEUTRAL
            strength = 0.0
            
        # Подтверждение объемом
        if indicators['volume_ratio'] > 1.5:
            strength *= 1.3
            
        return direction, min(1.0, strength)
    
    def _calculate_signal_confidence(self,
                                    strength: float,
                                    market_analysis: Dict,
                                    indicators: Dict) -> float:
        """
        Расчет уверенности в сигнале.
        """
        confidence = strength * 0.4  # Базовая уверенность от силы сигнала
        
        # Учет режима рынка
        if 'regime' in market_analysis:
            regime = market_analysis['regime']
            if regime.regime_type in ['trending_up', 'trending_down']:
                if self.strategy_type == 'trend_following':
                    confidence += regime.confidence * 0.2
            elif regime.regime_type == 'ranging':
                if self.strategy_type == 'mean_reversion':
                    confidence += regime.confidence * 0.2
                    
        # Учет времени
        if 'timing' in market_analysis:
            timing = market_analysis['timing']
            confidence += timing.score * 0.2
            
        # Учет рыночных условий
        if 'conditions' in market_analysis:
            conditions = market_analysis['conditions']
            if conditions.liquidity > 0.5:
                confidence += 0.1
            if conditions.volatility < 0.03:
                confidence += 0.1
                
        return min(1.0, confidence)
    
    def _filter_signal(self, signal: TradeSignal, market_analysis: Dict) -> bool:
        """
        Фильтрация сигнала на основе условий.
        """
        # Проверка адаптера рынка
        if not self.market_adapter.should_trade(signal.strength):
            logger.debug(f"Сигнал отфильтрован адаптером рынка")
            return False
            
        # Проверка режима
        if self.settings['use_regime_filter'] and 'regime' in market_analysis:
            regime = market_analysis['regime']
            
            # Фильтр по типу стратегии и режиму
            if self.strategy_type == 'trend_following':
                if regime.regime_type == 'ranging':
                    logger.debug(f"Трендовый сигнал отфильтрован в боковике")
                    return False
            elif self.strategy_type == 'mean_reversion':
                if regime.regime_type in ['trending_up', 'trending_down']:
                    logger.debug(f"Mean-reversion сигнал отфильтрован в тренде")
                    return False
                    
        # Проверка времени
        if self.settings['use_timing_filter'] and signal.timing_score < self.settings['min_timing_score']:
            logger.debug(f"Сигнал отфильтрован по времени: {signal.timing_score:.2f}")
            return False
            
        # Проверка корреляции с существующими позициями
        if self._check_correlation(signal) > self.settings['max_correlation']:
            logger.debug(f"Сигнал отфильтрован из-за высокой корреляции")
            return False
            
        return True
    
    def _check_correlation(self, signal: TradeSignal) -> float:
        """
        Проверка корреляции с открытыми позициями.
        """
        if not self.positions:
            return 0.0
            
        # Упрощенная проверка: одинаковое направление = высокая корреляция
        same_direction_count = sum(
            1 for pos in self.positions 
            if pos.direction == signal.direction
        )
        
        correlation = same_direction_count / len(self.positions)
        
        return correlation
    
    def _apply_risk_management(self, signal: TradeSignal) -> TradeSignal:
        """
        Применение правил риск-менеджмента к сигналу.
        """
        # Корректировка размера позиции на основе уверенности
        signal.position_size *= signal.confidence
        
        # Ограничение максимальным риском
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        max_units = (self.current_capital * self.max_risk_per_trade) / risk_per_unit
        
        signal.position_size = min(signal.position_size, max_units)
        
        # Корректировка на основе текущей экспозиции
        current_exposure = sum(pos.size for pos in self.positions)
        max_exposure = self.current_capital * 0.3  # Макс 30% капитала
        
        if current_exposure + signal.position_size * signal.entry_price > max_exposure:
            signal.position_size = (max_exposure - current_exposure) / signal.entry_price
            
        # Минимальный размер позиции
        min_position = self.current_capital * 0.001
        if signal.position_size * signal.entry_price < min_position:
            logger.debug("Размер позиции слишком мал")
            signal.position_size = 0
            
        return signal
    
    def _can_open_position(self, signal: TradeSignal) -> bool:
        """
        Проверка возможности открытия позиции.
        """
        if signal.position_size <= 0:
            return False
            
        if len(self.positions) >= self.settings['max_positions']:
            logger.info(f"Достигнут лимит позиций: {len(self.positions)}")
            return False
            
        required_capital = signal.position_size * signal.entry_price
        available_capital = self.current_capital - sum(
            pos.size * pos.entry_price for pos in self.positions
        )
        
        if required_capital > available_capital:
            logger.info(f"Недостаточно капитала: требуется {required_capital:.2f}, доступно {available_capital:.2f}")
            return False
            
        return True
    
    def _open_position(self, signal: TradeSignal):
        """
        Открытие новой позиции.
        """
        position = Position(
            id=f"{self.symbol}_{datetime.now().timestamp()}",
            timestamp=signal.timestamp,
            direction=signal.direction,
            entry_price=signal.entry_price,
            current_price=signal.entry_price,
            size=signal.position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            metadata=signal.metadata
        )
        
        self.positions.append(position)
        
        logger.info(f"Открыта позиция: {position.direction.name} {position.size:.2f} @ {position.entry_price:.5f}")
        
        # Запись в историю
        self.trade_history.append({
            'timestamp': position.timestamp,
            'type': 'open',
            'direction': position.direction.value,
            'price': position.entry_price,
            'size': position.size,
            'signal_strength': signal.strength,
            'confidence': signal.confidence,
            'regime': signal.regime
        })
    
    def _update_positions(self, price_bar: pd.Series):
        """
        Обновление открытых позиций.
        """
        current_price = price_bar['close']
        positions_to_close = []
        
        for position in self.positions:
            position.current_price = current_price
            position.duration += 1
            
            # Расчет P&L
            if position.direction == TradeDirection.LONG:
                position.profit_loss = (current_price - position.entry_price) * position.size
            else:
                position.profit_loss = (position.entry_price - current_price) * position.size
                
            # Проверка стоп-лосса
            if position.direction == TradeDirection.LONG:
                if current_price <= position.stop_loss:
                    positions_to_close.append((position, 'stop_loss'))
            else:
                if current_price >= position.stop_loss:
                    positions_to_close.append((position, 'stop_loss'))
                    
            # Проверка тейк-профита
            if position.direction == TradeDirection.LONG:
                if current_price >= position.take_profit:
                    positions_to_close.append((position, 'take_profit'))
            else:
                if current_price <= position.take_profit:
                    positions_to_close.append((position, 'take_profit'))
                    
            # Trailing stop
            if position.trailing_stop is not None:
                if position.direction == TradeDirection.LONG:
                    if current_price <= position.trailing_stop:
                        positions_to_close.append((position, 'trailing_stop'))
                    else:
                        # Обновление trailing stop
                        new_trailing = current_price * (1 - self.current_parameters.get('trailing_stop_distance', 0.015))
                        position.trailing_stop = max(position.trailing_stop, new_trailing)
                else:
                    if current_price >= position.trailing_stop:
                        positions_to_close.append((position, 'trailing_stop'))
                    else:
                        new_trailing = current_price * (1 + self.current_parameters.get('trailing_stop_distance', 0.015))
                        position.trailing_stop = min(position.trailing_stop, new_trailing)
                        
            # Максимальное время удержания
            max_holding = self.current_parameters.get('max_holding_period', 100)
            if position.duration >= max_holding:
                positions_to_close.append((position, 'max_duration'))
                
        # Закрытие позиций
        for position, reason in positions_to_close:
            self._close_position(position, reason)
    
    def _close_position(self, position: Position, reason: str):
        """
        Закрытие позиции.
        """
        self.positions.remove(position)
        self.closed_positions.append({
            'position': position,
            'close_time': datetime.now(),
            'close_reason': reason,
            'profit_loss': position.profit_loss
        })
        
        # Обновление капитала
        self.current_capital += position.profit_loss
        self.equity_curve.append(self.current_capital)
        
        logger.info(f"Закрыта позиция: {position.id} по причине {reason}, P&L: {position.profit_loss:.2f}")
        
        # Запись в историю
        self.trade_history.append({
            'timestamp': datetime.now(),
            'type': 'close',
            'direction': position.direction.value,
            'price': position.current_price,
            'size': position.size,
            'profit': position.profit_loss,
            'reason': reason,
            'duration': position.duration
        })
    
    def _reoptimize_parameters(self, price_data: pd.DataFrame):
        """
        Переоптимизация параметров стратегии.
        """
        if not self.settings['use_adaptive_parameters']:
            return
            
        logger.info("Начата реоптимизация параметров...")
        
        # Оптимизация параметров
        optimization_result = self.parameter_optimizer.optimize_parameters(
            price_data,
            self.trade_history,
            self.current_regime.regime_type if self.current_regime else 'unknown',
            method='adaptive'
        )
        
        # Обновление параметров
        self.current_parameters = optimization_result.parameters
        
        logger.info(f"Параметры оптимизированы. Sharpe: {optimization_result.sharpe_ratio:.2f}, "
                   f"Win Rate: {optimization_result.win_rate:.2%}")
    
    def get_performance_report(self) -> Dict:
        """
        Получение отчета о производительности.
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'total_return': 0,
                'status': 'No trades'
            }
            
        trades = [t for t in self.trade_history if t['type'] == 'close']
        
        if not trades:
            return {
                'total_trades': 0,
                'open_positions': len(self.positions),
                'status': 'Positions open, no closed trades'
            }
            
        # Основные метрики
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t['profit'] > 0)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Profit Factor
        gross_profit = sum(t['profit'] for t in trades if t['profit'] > 0)
        gross_loss = abs(sum(t['profit'] for t in trades if t['profit'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe Ratio
        returns = pd.Series([t['profit'] / self.initial_capital for t in trades])
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # Max Drawdown
        equity = pd.Series(self.equity_curve)
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # Total Return
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # Статистика по режимам
        regime_stats = {}
        for trade in trades:
            regime = trade.get('regime', 'unknown')
            if regime not in regime_stats:
                regime_stats[regime] = {'count': 0, 'profit': 0}
            regime_stats[regime]['count'] += 1
            regime_stats[regime]['profit'] += trade['profit']
            
        report = {
            'total_trades': total_trades,
            'open_positions': len(self.positions),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_return': total_return,
            'current_capital': self.current_capital,
            'regime_statistics': regime_stats,
            'average_trade_duration': np.mean([t['duration'] for t in trades if 'duration' in t]),
            'best_trade': max((t['profit'] for t in trades), default=0),
            'worst_trade': min((t['profit'] for t in trades), default=0),
            'current_regime': self.current_regime.regime_type if self.current_regime else 'unknown',
            'bars_processed': self.bars_processed,
            'status': 'Active' if self.is_active else 'Inactive'
        }
        
        return report
    
    def stop(self):
        """
        Остановка торгового робота.
        """
        logger.info("Остановка торгового робота...")
        
        # Закрытие всех позиций
        for position in self.positions.copy():
            self._close_position(position, 'robot_stopped')
            
        self.is_active = False
        
        # Финальный отчет
        report = self.get_performance_report()
        logger.info(f"Робот остановлен. Финальный капитал: {self.current_capital:.2f}")
        logger.info(f"Общий доход: {report['total_return']:.2%}")
        
        return report