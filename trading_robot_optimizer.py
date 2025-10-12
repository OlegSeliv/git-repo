#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Торговый робот с адаптивностью к рыночным условиям и оптимизацией времени запуска
"""

import numpy as np
import pandas as pd
import datetime as dt
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

@dataclass
class MarketCondition:
    """Класс для описания рыночных условий"""
    volatility: float
    trend_strength: float
    volume_profile: float
    time_of_day: int
    day_of_week: int
    market_regime: str  # 'trending', 'ranging', 'volatile'
    
@dataclass
class TradingSignal:
    """Класс для торговых сигналов"""
    direction: str  # 'buy', 'sell', 'hold'
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    timestamp: dt.datetime

class MarketRegimeDetector:
    """Детектор рыночных режимов для адаптации стратегии"""
    
    def __init__(self, lookback_period: int = 50):
        self.lookback_period = lookback_period
        self.regime_history = []
        
    def detect_regime(self, prices: pd.Series, volume: pd.Series = None) -> str:
        """
        Определяет текущий рыночный режим
        
        Args:
            prices: Серия цен
            volume: Серия объемов (опционально)
            
        Returns:
            Тип режима: 'trending', 'ranging', 'volatile'
        """
        if len(prices) < self.lookback_period:
            return 'ranging'
            
        # Вычисляем индикаторы для определения режима
        returns = prices.pct_change().dropna()
        
        # 1. Сила тренда (ADX-подобный индикатор)
        high_low_spread = (prices.rolling(14).max() - prices.rolling(14).min()) / prices.rolling(14).mean()
        trend_strength = high_low_spread.iloc[-1] if len(high_low_spread) > 0 else 0
        
        # 2. Волатильность
        volatility = returns.rolling(20).std().iloc[-1] if len(returns) > 20 else returns.std()
        
        # 3. Направленность движения
        sma_short = prices.rolling(10).mean()
        sma_long = prices.rolling(30).mean()
        trend_direction = (sma_short.iloc[-1] - sma_long.iloc[-1]) / sma_long.iloc[-1] if len(sma_long) > 0 else 0
        
        # Определяем режим на основе критериев
        if abs(trend_direction) > 0.02 and trend_strength > 0.05:
            regime = 'trending'
        elif volatility > returns.std() * 1.5:
            regime = 'volatile'
        else:
            regime = 'ranging'
            
        self.regime_history.append({
            'timestamp': dt.datetime.now(),
            'regime': regime,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'trend_direction': trend_direction
        })
        
        return regime

class AdaptiveRiskManager:
    """Адаптивное управление рисками в зависимости от рыночных условий"""
    
    def __init__(self):
        self.base_position_size = 0.02  # 2% от капитала
        self.max_position_size = 0.05   # 5% максимум
        self.volatility_lookback = 20
        
    def calculate_position_size(self, 
                              market_condition: MarketCondition,
                              account_balance: float,
                              confidence: float) -> float:
        """
        Рассчитывает размер позиции на основе рыночных условий
        
        Args:
            market_condition: Текущие рыночные условия
            account_balance: Баланс счета
            confidence: Уверенность в сигнале (0-1)
            
        Returns:
            Размер позиции в долях от капитала
        """
        # Базовый размер позиции
        base_size = self.base_position_size
        
        # Корректировка на волатильность
        volatility_adjustment = 1.0 / (1.0 + market_condition.volatility * 2)
        
        # Корректировка на силу тренда
        trend_adjustment = 1.0 + (market_condition.trend_strength * 0.5)
        
        # Корректировка на уверенность в сигнале
        confidence_adjustment = confidence
        
        # Корректировка на время торгов (избегаем новостных периодов)
        time_adjustment = self._get_time_adjustment(market_condition.time_of_day)
        
        # Итоговый размер позиции
        adjusted_size = (base_size * 
                        volatility_adjustment * 
                        trend_adjustment * 
                        confidence_adjustment * 
                        time_adjustment)
        
        # Ограничиваем максимальный размер
        final_size = min(adjusted_size, self.max_position_size)
        
        return final_size
    
    def _get_time_adjustment(self, hour: int) -> float:
        """Корректировка размера позиции в зависимости от времени"""
        # Снижаем риск в периоды низкой ликвидности
        if hour in [22, 23, 0, 1, 2, 3, 4, 5]:  # Ночные часы по MSK
            return 0.5
        elif hour in [9, 10, 16, 17]:  # Часы открытия/закрытия рынков
            return 0.7
        else:
            return 1.0

class OptimalTimingAnalyzer:
    """Анализатор оптимального времени запуска торгового робота"""
    
    def __init__(self):
        self.performance_history = []
        self.session_stats = {}
        
    def analyze_historical_performance(self, trades_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализирует историческую производительность по времени запуска
        
        Args:
            trades_data: DataFrame с данными сделок (должен содержать 'start_time', 'pnl')
            
        Returns:
            Словарь с рекомендациями по времени запуска
        """
        if trades_data.empty:
            return self._default_timing_recommendations()
            
        # Проверяем наличие нужных колонок
        if 'start_time' not in trades_data.columns:
            # Если нет start_time, используем timestamp
            if 'timestamp' in trades_data.columns:
                trades_data['start_time'] = trades_data['timestamp']
            else:
                return self._default_timing_recommendations()
        
        # Группируем по часам запуска
        trades_data['start_hour'] = pd.to_datetime(trades_data['start_time']).dt.hour
        trades_data['start_dow'] = pd.to_datetime(trades_data['start_time']).dt.dayofweek
        
        # Анализ по часам
        hourly_performance = trades_data.groupby('start_hour')['pnl'].agg(['mean', 'std', 'count'])
        hourly_performance['sharpe'] = hourly_performance['mean'] / hourly_performance['std']
        hourly_performance['score'] = (hourly_performance['sharpe'] * 
                                     np.sqrt(hourly_performance['count']))
        
        # Анализ по дням недели
        daily_performance = trades_data.groupby('start_dow')['pnl'].agg(['mean', 'std', 'count'])
        daily_performance['sharpe'] = daily_performance['mean'] / daily_performance['std']
        
        # Определяем оптимальные временные окна
        best_hours = hourly_performance.nlargest(3, 'score').index.tolist()
        worst_hours = hourly_performance.nsmallest(3, 'score').index.tolist()
        
        best_days = daily_performance.nlargest(3, 'sharpe').index.tolist()
        worst_days = daily_performance.nsmallest(2, 'sharpe').index.tolist()
        
        return {
            'optimal_start_hours': best_hours,
            'avoid_start_hours': worst_hours,
            'optimal_days': best_days,
            'avoid_days': worst_days,
            'hourly_stats': hourly_performance.to_dict(),
            'daily_stats': daily_performance.to_dict(),
            'recommendations': self._generate_timing_recommendations(
                best_hours, worst_hours, best_days, worst_days
            )
        }
    
    def _default_timing_recommendations(self) -> Dict[str, Any]:
        """Рекомендации по умолчанию при отсутствии данных"""
        return {
            'optimal_start_hours': [9, 10, 14, 15],  # Основные торговые часы
            'avoid_start_hours': [22, 23, 0, 1, 2],  # Ночные часы
            'optimal_days': [1, 2, 3, 4],  # Вт-Пт
            'avoid_days': [6, 0],  # Выходные
            'recommendations': [
                "Запускайте робота в основные торговые часы (9-11, 14-16 MSK)",
                "Избегайте запуска в ночные часы и выходные дни",
                "Учитывайте календарь экономических событий",
                "Мониторьте волатильность перед запуском"
            ]
        }
    
    def _generate_timing_recommendations(self, best_hours, worst_hours, 
                                      best_days, worst_days) -> List[str]:
        """Генерирует текстовые рекомендации"""
        recommendations = []
        
        if best_hours:
            hours_str = ', '.join([f"{h}:00" for h in best_hours])
            recommendations.append(f"Оптимальное время запуска: {hours_str}")
            
        if worst_hours:
            hours_str = ', '.join([f"{h}:00" for h in worst_hours])
            recommendations.append(f"Избегайте запуска в: {hours_str}")
            
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        if best_days:
            days_str = ', '.join([day_names[d] for d in best_days])
            recommendations.append(f"Лучшие дни для запуска: {days_str}")
            
        return recommendations

class AdaptiveTradingRobot:
    """Основной класс адаптивного торгового робота"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.regime_detector = MarketRegimeDetector()
        self.risk_manager = AdaptiveRiskManager()
        self.timing_analyzer = OptimalTimingAnalyzer()
        
        # Параметры стратегии для разных режимов
        self.strategy_params = {
            'trending': {
                'entry_threshold': 0.6,
                'exit_threshold': 0.3,
                'stop_loss_pct': 0.015,
                'take_profit_pct': 0.03
            },
            'ranging': {
                'entry_threshold': 0.7,
                'exit_threshold': 0.4,
                'stop_loss_pct': 0.01,
                'take_profit_pct': 0.02
            },
            'volatile': {
                'entry_threshold': 0.8,
                'exit_threshold': 0.2,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.015
            }
        }
        
        self.positions = []
        self.performance_log = []
        
    def should_start_trading(self, current_time: dt.datetime = None) -> Tuple[bool, str]:
        """
        Определяет, стоит ли запускать торговлю в текущий момент
        
        Args:
            current_time: Текущее время (если не указано, используется системное)
            
        Returns:
            Tuple из булевого значения и причины решения
        """
        if current_time is None:
            current_time = dt.datetime.now()
            
        hour = current_time.hour
        dow = current_time.weekday()
        
        # Проверяем исторические данные
        if hasattr(self, 'timing_recommendations'):
            optimal_hours = self.timing_recommendations.get('optimal_start_hours', [])
            avoid_hours = self.timing_recommendations.get('avoid_start_hours', [])
            avoid_days = self.timing_recommendations.get('avoid_days', [])
            
            if hour in avoid_hours:
                return False, f"Неоптимальный час для запуска: {hour}:00"
                
            if dow in avoid_days:
                day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
                return False, f"Неоптимальный день: {day_names[dow]}"
                
            if hour in optimal_hours:
                return True, f"Оптимальное время для запуска: {hour}:00"
        
        # Базовые правила по умолчанию
        if dow >= 5:  # Выходные
            return False, "Выходной день"
            
        if hour in [22, 23, 0, 1, 2, 3, 4, 5]:  # Ночные часы
            return False, "Ночное время с низкой ликвидностью"
            
        return True, "Подходящее время для торговли"
    
    def analyze_market_condition(self, market_data: pd.DataFrame) -> MarketCondition:
        """Анализирует текущие рыночные условия"""
        current_time = dt.datetime.now()
        
        # Получаем цены и объемы
        prices = market_data['close'] if 'close' in market_data.columns else market_data.iloc[:, 0]
        volume = market_data['volume'] if 'volume' in market_data.columns else pd.Series([1] * len(prices))
        
        # Определяем режим рынка
        regime = self.regime_detector.detect_regime(prices, volume)
        
        # Вычисляем метрики
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(20).std().iloc[-1] if len(returns) > 20 else returns.std()
        
        # Сила тренда
        sma_short = prices.rolling(10).mean()
        sma_long = prices.rolling(30).mean()
        trend_strength = abs((sma_short.iloc[-1] - sma_long.iloc[-1]) / sma_long.iloc[-1]) if len(sma_long) > 0 else 0
        
        # Профиль объема
        volume_profile = volume.rolling(20).mean().iloc[-1] / volume.mean() if len(volume) > 20 else 1.0
        
        return MarketCondition(
            volatility=volatility,
            trend_strength=trend_strength,
            volume_profile=volume_profile,
            time_of_day=current_time.hour,
            day_of_week=current_time.weekday(),
            market_regime=regime
        )
    
    def generate_trading_signal(self, market_data: pd.DataFrame, 
                              market_condition: MarketCondition) -> Optional[TradingSignal]:
        """
        Генерирует торговый сигнал на основе рыночных условий
        
        Args:
            market_data: Рыночные данные
            market_condition: Текущие рыночные условия
            
        Returns:
            Торговый сигнал или None
        """
        # Получаем параметры для текущего режима
        params = self.strategy_params[market_condition.market_regime]
        
        # Простая стратегия на основе скользящих средних (адаптированная под режим)
        prices = market_data['close'] if 'close' in market_data.columns else market_data.iloc[:, 0]
        
        if len(prices) < 50:
            return None
            
        # Индикаторы
        sma_fast = prices.rolling(10).mean()
        sma_slow = prices.rolling(21).mean()
        rsi = self._calculate_rsi(prices, 14)
        
        current_price = prices.iloc[-1]
        signal_strength = 0
        direction = 'hold'
        
        # Логика генерации сигналов
        if sma_fast.iloc[-1] > sma_slow.iloc[-1]:  # Восходящий тренд
            if rsi.iloc[-1] < 70 and market_condition.trend_strength > 0.01:
                signal_strength = min(0.8, market_condition.trend_strength * 10)
                direction = 'buy'
        elif sma_fast.iloc[-1] < sma_slow.iloc[-1]:  # Нисходящий тренд
            if rsi.iloc[-1] > 30 and market_condition.trend_strength > 0.01:
                signal_strength = min(0.8, market_condition.trend_strength * 10)
                direction = 'sell'
        
        # Проверяем пороговые значения
        if signal_strength < params['entry_threshold']:
            return None
            
        # Рассчитываем уровни
        if direction == 'buy':
            stop_loss = current_price * (1 - params['stop_loss_pct'])
            take_profit = current_price * (1 + params['take_profit_pct'])
        else:
            stop_loss = current_price * (1 + params['stop_loss_pct'])
            take_profit = current_price * (1 - params['take_profit_pct'])
            
        # Размер позиции
        position_size = self.risk_manager.calculate_position_size(
            market_condition, 10000, signal_strength  # Предполагаем баланс 10000
        )
        
        return TradingSignal(
            direction=direction,
            confidence=signal_strength,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            timestamp=dt.datetime.now()
        )
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Расчет RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def update_timing_analysis(self, historical_trades: pd.DataFrame):
        """Обновляет анализ оптимального времени запуска"""
        self.timing_recommendations = self.timing_analyzer.analyze_historical_performance(
            historical_trades
        )
    
    def get_status_report(self) -> Dict[str, Any]:
        """Возвращает отчет о текущем состоянии робота"""
        current_time = dt.datetime.now()
        can_trade, reason = self.should_start_trading(current_time)
        
        return {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'can_start_trading': can_trade,
            'reason': reason,
            'active_positions': len(self.positions),
            'regime_history': self.regime_detector.regime_history[-5:],  # Последние 5 режимов
            'timing_recommendations': getattr(self, 'timing_recommendations', {}),
            'strategy_status': 'active' if can_trade else 'waiting'
        }

def create_sample_market_data() -> pd.DataFrame:
    """Создает примерные рыночные данные для тестирования"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='1h')
    
    # Генерируем синтетические данные с трендами и волатильностью
    n_points = len(dates)
    price_changes = np.random.normal(0, 0.001, n_points)
    
    # Добавляем тренды в определенные периоды
    trend_periods = [(100, 200), (500, 600), (1000, 1200)]
    for start, end in trend_periods:
        if end < n_points:
            price_changes[start:end] += np.linspace(0, 0.05, end - start)
    
    # Добавляем волатильные периоды
    volatile_periods = [(300, 350), (800, 850)]
    for start, end in volatile_periods:
        if end < n_points:
            price_changes[start:end] *= 3
    
    prices = 100 * (1 + price_changes).cumprod()
    volumes = np.random.lognormal(10, 0.5, n_points)
    
    return pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'volume': volumes
    })

if __name__ == "__main__":
    # Демонстрация работы системы
    print("=== Система оптимизации торгового робота ===\n")
    
    # Создаем конфигурацию
    config = {
        'base_currency': 'USD',
        'quote_currency': 'EUR',
        'initial_balance': 10000,
        'max_risk_per_trade': 0.02
    }
    
    # Инициализируем робота
    robot = AdaptiveTradingRobot(config)
    
    # Создаем тестовые данные
    print("1. Создание тестовых рыночных данных...")
    market_data = create_sample_market_data()
    print(f"   Создано {len(market_data)} точек данных")
    
    # Анализируем рыночные условия
    print("\n2. Анализ рыночных условий...")
    market_condition = robot.analyze_market_condition(market_data.tail(100))
    print(f"   Режим рынка: {market_condition.market_regime}")
    print(f"   Волатильность: {market_condition.volatility:.4f}")
    print(f"   Сила тренда: {market_condition.trend_strength:.4f}")
    
    # Проверяем время запуска
    print("\n3. Анализ оптимального времени запуска...")
    can_start, reason = robot.should_start_trading()
    print(f"   Можно запускать: {can_start}")
    print(f"   Причина: {reason}")
    
    # Генерируем сигнал
    print("\n4. Генерация торгового сигнала...")
    signal = robot.generate_trading_signal(market_data.tail(100), market_condition)
    if signal:
        print(f"   Направление: {signal.direction}")
        print(f"   Уверенность: {signal.confidence:.2f}")
        print(f"   Размер позиции: {signal.position_size:.3f}")
        print(f"   Цена входа: {signal.entry_price:.4f}")
        print(f"   Stop Loss: {signal.stop_loss:.4f}")
        print(f"   Take Profit: {signal.take_profit:.4f}")
    else:
        print("   Сигнал не сгенерирован (недостаточная уверенность)")
    
    # Создаем примерные исторические данные о сделках для анализа времени
    print("\n5. Анализ исторической производительности...")
    sample_trades = pd.DataFrame({
        'start_time': pd.date_range('2024-01-01', periods=100, freq='6h'),
        'pnl': np.random.normal(0.001, 0.02, 100)
    })
    
    robot.update_timing_analysis(sample_trades)
    
    # Получаем отчет
    print("\n6. Итоговый отчет:")
    status = robot.get_status_report()
    
    print(f"   Текущее время: {status['current_time']}")
    print(f"   Можно торговать: {status['can_start_trading']}")
    print(f"   Активных позиций: {status['active_positions']}")
    
    if 'timing_recommendations' in status and status['timing_recommendations']:
        print("\n   Рекомендации по времени запуска:")
        for rec in status['timing_recommendations'].get('recommendations', []):
            print(f"   - {rec}")
    
    print("\n=== Анализ завершен ===")