"""
Система оптимизации времени запуска торгового робота
Анализирует различные временные паттерны и сессии для поиска оптимального времени торговли
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta, time
import logging
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class TradingSession(Enum):
    """Торговые сессии"""
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP_LONDON_NY = "london_ny_overlap"
    OVERLAP_ASIAN_LONDON = "asian_london_overlap"
    AFTER_HOURS = "after_hours"

class MarketPhase(Enum):
    """Фазы рынка в течение дня"""
    OPENING = "opening"  # Первые 2 часа после открытия
    MID_SESSION = "mid_session"  # Середина сессии
    CLOSING = "closing"  # Последние 2 часа перед закрытием
    OVERNIGHT = "overnight"  # Вне основных сессий

@dataclass
class TimeAnalysis:
    """Результат анализа времени"""
    best_hour: int
    best_session: TradingSession
    best_phase: MarketPhase
    expected_return: float
    volatility: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    confidence_score: float

@dataclass
class SessionCharacteristics:
    """Характеристики торговой сессии"""
    session: TradingSession
    start_hour: int
    end_hour: int
    avg_volatility: float
    avg_volume: float
    trend_strength: float
    breakout_probability: float
    reversal_probability: float

class MarketSessionAnalyzer:
    """Анализатор торговых сессий"""
    
    def __init__(self):
        self.sessions = {
            TradingSession.ASIAN: SessionCharacteristics(
                session=TradingSession.ASIAN,
                start_hour=0,  # UTC
                end_hour=8,
                avg_volatility=0.15,
                avg_volume=0.8,
                trend_strength=0.6,
                breakout_probability=0.3,
                reversal_probability=0.4
            ),
            TradingSession.LONDON: SessionCharacteristics(
                session=TradingSession.LONDON,
                start_hour=8,
                end_hour=16,
                avg_volatility=0.25,
                avg_volume=1.2,
                trend_strength=0.8,
                breakout_probability=0.6,
                reversal_probability=0.2
            ),
            TradingSession.NEW_YORK: SessionCharacteristics(
                session=TradingSession.NEW_YORK,
                start_hour=13,
                end_hour=21,
                avg_volatility=0.22,
                avg_volume=1.0,
                trend_strength=0.7,
                breakout_probability=0.5,
                reversal_probability=0.3
            ),
            TradingSession.OVERLAP_LONDON_NY: SessionCharacteristics(
                session=TradingSession.OVERLAP_LONDON_NY,
                start_hour=13,
                end_hour=16,
                avg_volatility=0.35,
                avg_volume=1.5,
                trend_strength=0.9,
                breakout_probability=0.8,
                reversal_probability=0.1
            ),
            TradingSession.OVERLAP_ASIAN_LONDON: SessionCharacteristics(
                session=TradingSession.OVERLAP_ASIAN_LONDON,
                start_hour=6,
                end_hour=10,
                avg_volatility=0.2,
                avg_volume=1.0,
                trend_strength=0.7,
                breakout_probability=0.4,
                reversal_probability=0.3
            )
        }
    
    def get_current_session(self, utc_hour: int) -> TradingSession:
        """Определяет текущую торговую сессию"""
        if 0 <= utc_hour < 8:
            return TradingSession.ASIAN
        elif 8 <= utc_hour < 13:
            return TradingSession.LONDON
        elif 13 <= utc_hour < 16:
            return TradingSession.OVERLAP_LONDON_NY
        elif 16 <= utc_hour < 21:
            return TradingSession.NEW_YORK
        else:
            return TradingSession.AFTER_HOURS
    
    def get_session_characteristics(self, session: TradingSession) -> SessionCharacteristics:
        """Возвращает характеристики сессии"""
        return self.sessions.get(session, self.sessions[TradingSession.ASIAN])

class VolatilityPatternAnalyzer:
    """Анализатор паттернов волатильности по времени"""
    
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
        self.hourly_volatility = {}
        self.hourly_returns = {}
        self.hourly_win_rates = {}
    
    def analyze_hourly_patterns(self, price_data: pd.DataFrame) -> Dict[int, Dict]:
        """Анализирует паттерны по часам"""
        # Группируем данные по часам
        price_data['hour'] = price_data.index.hour
        price_data['returns'] = price_data['close'].pct_change()
        
        hourly_stats = {}
        
        for hour in range(24):
            hour_data = price_data[price_data['hour'] == hour]
            
            if len(hour_data) < 10:  # Недостаточно данных
                continue
            
            returns = hour_data['returns'].dropna()
            volatility = returns.std() * np.sqrt(252)  # Годовая волатильность
            avg_return = returns.mean() * 252  # Годовая доходность
            win_rate = (returns > 0).mean()
            
            # Вычисляем Sharpe ratio
            sharpe_ratio = avg_return / volatility if volatility > 0 else 0
            
            # Максимальная просадка
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            hourly_stats[hour] = {
                'volatility': volatility,
                'avg_return': avg_return,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': abs(max_drawdown),
                'trade_count': len(returns)
            }
        
        return hourly_stats
    
    def find_optimal_hours(self, hourly_stats: Dict[int, Dict], 
                          min_trades: int = 20) -> List[Tuple[int, float]]:
        """Находит оптимальные часы для торговли"""
        optimal_hours = []
        
        for hour, stats in hourly_stats.items():
            if stats['trade_count'] < min_trades:
                continue
            
            # Комплексная оценка качества торговли
            score = self._calculate_trading_score(stats)
            optimal_hours.append((hour, score))
        
        # Сортируем по убыванию качества
        optimal_hours.sort(key=lambda x: x[1], reverse=True)
        return optimal_hours
    
    def _calculate_trading_score(self, stats: Dict) -> float:
        """Вычисляет комплексную оценку качества торговли для часа"""
        # Веса для различных метрик
        weights = {
            'sharpe_ratio': 0.3,
            'win_rate': 0.25,
            'avg_return': 0.2,
            'volatility': 0.15,  # Отрицательный вес - меньше волатильности лучше
            'max_drawdown': 0.1   # Отрицательный вес - меньше просадки лучше
        }
        
        # Нормализация метрик (0-1)
        sharpe_norm = max(0, min(1, stats['sharpe_ratio'] / 2))  # 2 - хороший Sharpe
        win_rate_norm = stats['win_rate']
        return_norm = max(0, min(1, (stats['avg_return'] + 0.5) / 1.0))  # -0.5 до 0.5
        volatility_norm = max(0, 1 - stats['volatility'] / 1.0)  # Инвертированная волатильность
        drawdown_norm = max(0, 1 - stats['max_drawdown'] / 0.5)  # Инвертированная просадка
        
        score = (weights['sharpe_ratio'] * sharpe_norm +
                weights['win_rate'] * win_rate_norm +
                weights['avg_return'] * return_norm +
                weights['volatility'] * volatility_norm +
                weights['max_drawdown'] * drawdown_norm)
        
        return score

class EconomicCalendarAnalyzer:
    """Анализатор экономического календаря для оптимизации времени"""
    
    def __init__(self):
        self.high_impact_events = {
            'NFP': {'hour': 13, 'day': 'first_friday', 'impact': 'high'},
            'FOMC': {'hour': 19, 'day': 'variable', 'impact': 'high'},
            'CPI': {'hour': 13, 'day': 'mid_month', 'impact': 'high'},
            'GDP': {'hour': 13, 'day': 'end_quarter', 'impact': 'high'},
            'Interest_Rate': {'hour': 19, 'day': 'variable', 'impact': 'high'}
        }
    
    def get_high_impact_hours(self, date: datetime) -> List[int]:
        """Возвращает часы с высоким влиянием новостей"""
        high_impact_hours = []
        
        # Проверяем день недели
        weekday = date.weekday()
        
        # Пятница - NFP
        if weekday == 4:  # Пятница
            high_impact_hours.append(13)
        
        # Середина месяца - CPI
        if 10 <= date.day <= 20:
            high_impact_hours.append(13)
        
        # Конец квартала - GDP
        if date.month in [3, 6, 9, 12] and date.day >= 25:
            high_impact_hours.append(13)
        
        return high_impact_hours
    
    def should_avoid_trading(self, date: datetime, hour: int) -> bool:
        """Определяет, стоит ли избегать торговли в данное время"""
        high_impact_hours = self.get_high_impact_hours(date)
        return hour in high_impact_hours

class TimingOptimizer:
    """Основной класс для оптимизации времени запуска"""
    
    def __init__(self):
        self.session_analyzer = MarketSessionAnalyzer()
        self.volatility_analyzer = VolatilityPatternAnalyzer()
        self.economic_calendar = EconomicCalendarAnalyzer()
        self.optimization_results = {}
    
    def optimize_timing(self, price_data: pd.DataFrame, 
                       strategy_type: str = 'trend_following') -> TimeAnalysis:
        """Оптимизирует время запуска торгового робота"""
        
        # Анализируем паттерны по часам
        hourly_stats = self.volatility_analyzer.analyze_hourly_patterns(price_data)
        optimal_hours = self.volatility_analyzer.find_optimal_hours(hourly_stats)
        
        if not optimal_hours:
            raise ValueError("Недостаточно данных для оптимизации времени")
        
        # Находим лучший час
        best_hour, best_score = optimal_hours[0]
        best_stats = hourly_stats[best_hour]
        
        # Определяем лучшую сессию
        best_session = self.session_analyzer.get_current_session(best_hour)
        
        # Определяем лучшую фазу
        best_phase = self._determine_market_phase(best_hour)
        
        # Вычисляем метрики
        expected_return = best_stats['avg_return']
        volatility = best_stats['volatility']
        win_rate = best_stats['win_rate']
        sharpe_ratio = best_stats['sharpe_ratio']
        max_drawdown = best_stats['max_drawdown']
        
        # Учитываем влияние экономических событий
        confidence_score = self._calculate_confidence_score(
            best_hour, best_session, best_stats, price_data
        )
        
        analysis = TimeAnalysis(
            best_hour=best_hour,
            best_session=best_session,
            best_phase=best_phase,
            expected_return=expected_return,
            volatility=volatility,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            confidence_score=confidence_score
        )
        
        self.optimization_results[strategy_type] = analysis
        return analysis
    
    def get_trading_schedule(self, analysis: TimeAnalysis) -> Dict:
        """Создает расписание торговли на основе анализа"""
        schedule = {
            'primary_hours': [analysis.best_hour],
            'secondary_hours': [],
            'avoid_hours': [],
            'session_focus': analysis.best_session.value,
            'phase_focus': analysis.best_phase.value
        }
        
        # Добавляем дополнительные часы в той же сессии
        session_chars = self.session_analyzer.get_session_characteristics(analysis.best_session)
        for hour in range(session_chars.start_hour, session_chars.end_hour):
            if hour != analysis.best_hour:
                schedule['secondary_hours'].append(hour)
        
        # Определяем часы, которых следует избегать
        for hour in range(24):
            if hour not in schedule['primary_hours'] and hour not in schedule['secondary_hours']:
                # Проверяем, есть ли в этот час важные новости
                if self.economic_calendar.should_avoid_trading(datetime.now(), hour):
                    schedule['avoid_hours'].append(hour)
        
        return schedule
    
    def _determine_market_phase(self, hour: int) -> MarketPhase:
        """Определяет фазу рынка по часу"""
        session = self.session_analyzer.get_current_session(hour)
        session_chars = self.session_analyzer.get_session_characteristics(session)
        
        session_duration = session_chars.end_hour - session_chars.start_hour
        hour_in_session = hour - session_chars.start_hour
        
        if hour_in_session <= 2:
            return MarketPhase.OPENING
        elif hour_in_session >= session_duration - 2:
            return MarketPhase.CLOSING
        else:
            return MarketPhase.MID_SESSION
    
    def _calculate_confidence_score(self, hour: int, session: TradingSession, 
                                  stats: Dict, price_data: pd.DataFrame) -> float:
        """Вычисляет оценку уверенности в рекомендации"""
        base_confidence = 0.5
        
        # Увеличиваем уверенность при высоком качестве торговли
        if stats['sharpe_ratio'] > 1.0:
            base_confidence += 0.2
        if stats['win_rate'] > 0.6:
            base_confidence += 0.15
        if stats['max_drawdown'] < 0.1:
            base_confidence += 0.15
        
        # Учитываем количество данных
        data_confidence = min(1.0, stats['trade_count'] / 100)
        base_confidence += data_confidence * 0.2
        
        # Уменьшаем уверенность при важных новостях
        if self.economic_calendar.should_avoid_trading(datetime.now(), hour):
            base_confidence -= 0.3
        
        return max(0.0, min(1.0, base_confidence))
    
    def get_recommendations(self, analysis: TimeAnalysis) -> List[str]:
        """Возвращает рекомендации по времени торговли"""
        recommendations = []
        
        # Основные рекомендации
        recommendations.append(f"Оптимальное время: {analysis.best_hour}:00 UTC")
        recommendations.append(f"Лучшая сессия: {analysis.best_session.value}")
        recommendations.append(f"Фаза рынка: {analysis.best_phase.value}")
        
        # Метрики качества
        recommendations.append(f"Ожидаемая доходность: {analysis.expected_return:.2%}")
        recommendations.append(f"Коэффициент Шарпа: {analysis.sharpe_ratio:.2f}")
        recommendations.append(f"Процент выигрышных сделок: {analysis.win_rate:.1%}")
        
        # Дополнительные рекомендации
        if analysis.volatility > 0.3:
            recommendations.append("⚠️ Высокая волатильность - используйте меньшие позиции")
        
        if analysis.max_drawdown > 0.2:
            recommendations.append("⚠️ Большая максимальная просадка - усильте управление рисками")
        
        if analysis.confidence_score < 0.6:
            recommendations.append("⚠️ Низкая уверенность в рекомендации - требуется больше данных")
        
        return recommendations

# Пример использования
if __name__ == "__main__":
    # Создаем тестовые данные
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='H')
    prices = [100 + i * 0.01 + np.random.normal(0, 0.5) for i in range(len(dates))]
    
    price_data = pd.DataFrame({
        'timestamp': dates,
        'price': prices
    })
    
    # Создаем оптимизатор времени
    optimizer = TimingOptimizer()
    
    # Оптимизируем время
    analysis = optimizer.optimize_timing(price_data)
    
    print("=== РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ ВРЕМЕНИ ===")
    print(f"Лучший час: {analysis.best_hour}:00 UTC")
    print(f"Лучшая сессия: {analysis.best_session.value}")
    print(f"Фаза рынка: {analysis.best_phase.value}")
    print(f"Ожидаемая доходность: {analysis.expected_return:.2%}")
    print(f"Коэффициент Шарпа: {analysis.sharpe_ratio:.2f}")
    print(f"Процент выигрышных сделок: {analysis.win_rate:.1%}")
    print(f"Уверенность: {analysis.confidence_score:.1%}")
    
    # Получаем расписание
    schedule = optimizer.get_trading_schedule(analysis)
    print(f"\nРасписание торговли: {schedule}")
    
    # Получаем рекомендации
    recommendations = optimizer.get_recommendations(analysis)
    print(f"\nРекомендации:")
    for rec in recommendations:
        print(f"- {rec}")