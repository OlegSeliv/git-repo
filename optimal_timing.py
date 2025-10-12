"""
Модуль для определения оптимального времени запуска торгового робота.
Анализирует исторические паттерны и текущие условия для выбора лучшего момента входа.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time, timedelta
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class TimingScore:
    """Оценка времени для запуска торговли"""
    timestamp: datetime
    score: float  # 0-1, где 1 - идеальное время
    session: str  # 'asian', 'european', 'american', 'overlap'
    volatility_profile: str  # 'low', 'medium', 'high'
    liquidity_score: float
    historical_performance: float
    recommendation: str  # 'start_now', 'wait', 'avoid'
    confidence: float


class OptimalTimingAnalyzer:
    """
    Анализатор для определения оптимального времени запуска торгового робота.
    
    Учитывает:
    1. Торговые сессии и их пересечения
    2. Внутридневные паттерны волатильности
    3. Исторические результаты по времени суток
    4. Сезонные факторы
    5. Макроэкономические события
    """
    
    def __init__(self, 
                 symbol: str = "EURUSD",
                 lookback_days: int = 90,
                 min_sample_size: int = 30):
        """
        Args:
            symbol: Торговый инструмент
            lookback_days: Количество дней для анализа
            min_sample_size: Минимальный размер выборки для статистики
        """
        self.symbol = symbol
        self.lookback_days = lookback_days
        self.min_sample_size = min_sample_size
        
        # Определение торговых сессий (UTC)
        self.trading_sessions = {
            'asian': (time(0, 0), time(9, 0)),
            'european': (time(7, 0), time(16, 0)),
            'american': (time(13, 0), time(22, 0)),
            'sydney': (time(22, 0), time(7, 0))
        }
        
        # Оптимальные периоды для разных стратегий
        self.strategy_timing = {
            'trend_following': {
                'best_sessions': ['european', 'american'],
                'best_hours': list(range(9, 16)),  # UTC
                'avoid_hours': list(range(22, 24)) + list(range(0, 7))
            },
            'scalping': {
                'best_sessions': ['overlap_eu_us', 'european'],
                'best_hours': list(range(13, 16)),  # Максимальная ликвидность
                'avoid_hours': list(range(22, 24)) + list(range(0, 6))
            },
            'range_trading': {
                'best_sessions': ['asian', 'sydney'],
                'best_hours': list(range(2, 7)) + list(range(23, 24)),
                'avoid_hours': list(range(13, 16))  # Избегаем высокой волатильности
            },
            'news_trading': {
                'best_sessions': ['european', 'american'],
                'best_hours': [8, 13, 14, 15],  # Время выхода новостей
                'avoid_hours': list(range(18, 22))
            }
        }
        
        self.historical_performance = {}
        self.volatility_patterns = {}
        self.liquidity_patterns = {}
        
    def analyze_timing(self, 
                       historical_data: pd.DataFrame,
                       strategy_type: str = 'trend_following',
                       current_time: Optional[datetime] = None) -> TimingScore:
        """
        Анализ оптимального времени для запуска робота.
        
        Args:
            historical_data: Исторические данные с результатами торговли
            strategy_type: Тип торговой стратегии
            current_time: Время для анализа (None = сейчас)
            
        Returns:
            TimingScore: Оценка текущего времени
        """
        if current_time is None:
            current_time = datetime.now()
            
        # Анализ исторических паттернов
        self._analyze_historical_patterns(historical_data)
        
        # Определение текущей торговой сессии
        session = self._get_trading_session(current_time)
        
        # Оценка волатильности для текущего времени
        volatility_profile = self._get_volatility_profile(current_time.hour)
        
        # Оценка ликвидности
        liquidity_score = self._estimate_liquidity(current_time)
        
        # Историческая эффективность в это время
        hist_performance = self._get_historical_performance(
            current_time, strategy_type
        )
        
        # Расчет общего скора
        score = self._calculate_timing_score(
            session, volatility_profile, liquidity_score, 
            hist_performance, strategy_type, current_time
        )
        
        # Рекомендация
        recommendation = self._get_recommendation(score, strategy_type, current_time)
        
        # Уровень уверенности
        confidence = self._calculate_confidence(historical_data, current_time)
        
        return TimingScore(
            timestamp=current_time,
            score=score,
            session=session,
            volatility_profile=volatility_profile,
            liquidity_score=liquidity_score,
            historical_performance=hist_performance,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def _analyze_historical_patterns(self, data: pd.DataFrame):
        """
        Анализ исторических паттернов эффективности по времени.
        """
        if 'timestamp' not in data.columns or 'returns' not in data.columns:
            # Создаем синтетические данные для демонстрации
            data['timestamp'] = pd.date_range(
                end=datetime.now(), 
                periods=len(data), 
                freq='1H'
            )
            data['returns'] = np.random.randn(len(data)) * 0.001
            
        data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
        data['weekday'] = pd.to_datetime(data['timestamp']).dt.dayofweek
        
        # Паттерны по часам
        hourly_stats = data.groupby('hour')['returns'].agg([
            'mean', 'std', 'count',
            lambda x: (x > 0).mean(),  # Win rate
            lambda x: x[x > 0].mean() / abs(x[x < 0].mean()) if len(x[x < 0]) > 0 else 0  # Risk/reward
        ])
        hourly_stats.columns = ['avg_return', 'volatility', 'count', 'win_rate', 'risk_reward']
        
        self.historical_performance = hourly_stats.to_dict('index')
        
        # Паттерны волатильности
        for hour in range(24):
            hour_data = data[data['hour'] == hour]
            if len(hour_data) > self.min_sample_size:
                self.volatility_patterns[hour] = {
                    'mean': hour_data['returns'].std(),
                    'q25': hour_data['returns'].quantile(0.25),
                    'q75': hour_data['returns'].quantile(0.75)
                }
                
    def _get_trading_session(self, current_time: datetime) -> str:
        """
        Определение текущей торговой сессии.
        """
        hour = current_time.hour
        
        # Проверка пересечений сессий
        if 13 <= hour <= 16:
            return 'overlap_eu_us'  # Европа + США
        elif 7 <= hour <= 9:
            return 'overlap_eu_asia'  # Европа + Азия
        elif 0 <= hour <= 2:
            return 'overlap_asia_sydney'  # Азия + Сидней
            
        # Основные сессии
        for session, (start, end) in self.trading_sessions.items():
            if start <= time(hour, 0) <= end:
                return session
                
        return 'off_hours'
    
    def _get_volatility_profile(self, hour: int) -> str:
        """
        Определение профиля волатильности для заданного часа.
        """
        if hour not in self.volatility_patterns:
            # Используем типичные паттерны
            if hour in [13, 14, 15, 16]:  # Пересечение EU/US
                return 'high'
            elif hour in [8, 9, 10, 11, 17, 18, 19]:  # Активные сессии
                return 'medium'
            else:  # Азиатская сессия, ночь
                return 'low'
                
        vol = self.volatility_patterns[hour]['mean']
        all_vols = [v['mean'] for v in self.volatility_patterns.values()]
        
        if vol > np.percentile(all_vols, 75):
            return 'high'
        elif vol > np.percentile(all_vols, 25):
            return 'medium'
        else:
            return 'low'
    
    def _estimate_liquidity(self, current_time: datetime) -> float:
        """
        Оценка ликвидности в заданное время.
        """
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Базовая ликвидность по часам
        liquidity_by_hour = {
            13: 1.0, 14: 1.0, 15: 0.95, 16: 0.9,  # EU/US overlap
            8: 0.8, 9: 0.85, 10: 0.85, 11: 0.8,    # European session
            17: 0.7, 18: 0.65, 19: 0.6, 20: 0.5,   # US session
            21: 0.4, 22: 0.3, 23: 0.25,            # Late US
            0: 0.3, 1: 0.35, 2: 0.4, 3: 0.35,      # Asian session
            4: 0.3, 5: 0.25, 6: 0.3, 7: 0.5        # Early European
        }
        
        base_liquidity = liquidity_by_hour.get(hour, 0.3)
        
        # Корректировка на день недели
        weekday_multiplier = {
            0: 0.9,   # Понедельник (медленный старт)
            1: 1.0,   # Вторник
            2: 1.0,   # Среда
            3: 1.0,   # Четверг
            4: 0.85,  # Пятница (закрытие позиций)
            5: 0.2,   # Суббота
            6: 0.2    # Воскресенье
        }
        
        liquidity = base_liquidity * weekday_multiplier.get(weekday, 1.0)
        
        return min(1.0, max(0.0, liquidity))
    
    def _get_historical_performance(self, 
                                   current_time: datetime, 
                                   strategy_type: str) -> float:
        """
        Получение исторической эффективности для данного времени.
        """
        hour = current_time.hour
        
        if hour not in self.historical_performance:
            # Используем эвристику на основе типа стратегии
            strategy_timing = self.strategy_timing.get(strategy_type, {})
            
            if hour in strategy_timing.get('best_hours', []):
                return 0.8
            elif hour in strategy_timing.get('avoid_hours', []):
                return 0.2
            else:
                return 0.5
                
        perf = self.historical_performance[hour]
        
        # Комплексная оценка на основе нескольких метрик
        score = 0.0
        
        # Средний доход (нормализованный)
        avg_return = perf.get('avg_return', 0)
        score += np.tanh(avg_return * 1000) * 0.3  # 30% веса
        
        # Win rate
        win_rate = perf.get('win_rate', 0.5)
        score += win_rate * 0.3  # 30% веса
        
        # Risk/Reward ratio
        rr_ratio = perf.get('risk_reward', 1.0)
        score += min(1.0, rr_ratio / 2) * 0.2  # 20% веса
        
        # Стабильность (обратная волатильности)
        volatility = perf.get('volatility', 0.001)
        stability = 1.0 / (1.0 + volatility * 100)
        score += stability * 0.2  # 20% веса
        
        return min(1.0, max(0.0, score))
    
    def _calculate_timing_score(self,
                               session: str,
                               volatility_profile: str,
                               liquidity_score: float,
                               hist_performance: float,
                               strategy_type: str,
                               current_time: datetime) -> float:
        """
        Расчет общего скора времени для торговли.
        """
        score = 0.0
        weights = {
            'session': 0.25,
            'volatility': 0.2,
            'liquidity': 0.25,
            'historical': 0.2,
            'special_factors': 0.1
        }
        
        strategy_prefs = self.strategy_timing.get(strategy_type, {})
        
        # Оценка сессии
        session_score = 0.0
        if session in strategy_prefs.get('best_sessions', []):
            session_score = 1.0
        elif session == 'off_hours':
            session_score = 0.1
        elif 'overlap' in session:
            session_score = 0.8 if strategy_type != 'range_trading' else 0.2
        else:
            session_score = 0.5
        score += session_score * weights['session']
        
        # Оценка волатильности
        vol_score = 0.0
        if strategy_type == 'trend_following':
            vol_score = {'low': 0.3, 'medium': 0.8, 'high': 1.0}.get(volatility_profile, 0.5)
        elif strategy_type == 'scalping':
            vol_score = {'low': 0.2, 'medium': 0.7, 'high': 1.0}.get(volatility_profile, 0.5)
        elif strategy_type == 'range_trading':
            vol_score = {'low': 1.0, 'medium': 0.5, 'high': 0.2}.get(volatility_profile, 0.5)
        else:
            vol_score = 0.5
        score += vol_score * weights['volatility']
        
        # Ликвидность
        score += liquidity_score * weights['liquidity']
        
        # Историческая эффективность
        score += hist_performance * weights['historical']
        
        # Специальные факторы
        special_score = self._check_special_factors(current_time)
        score += special_score * weights['special_factors']
        
        return min(1.0, max(0.0, score))
    
    def _check_special_factors(self, current_time: datetime) -> float:
        """
        Проверка специальных факторов (праздники, важные события и т.д.).
        """
        score = 0.5  # Нейтральный скор по умолчанию
        
        weekday = current_time.weekday()
        day = current_time.day
        month = current_time.month
        hour = current_time.hour
        
        # Пятница после обеда - много закрытий позиций
        if weekday == 4 and hour >= 16:
            score *= 0.7
            
        # Понедельник утро - медленный старт
        if weekday == 0 and hour < 10:
            score *= 0.8
            
        # Начало/конец месяца - ребалансировка портфелей
        if day <= 3 or day >= 28:
            score *= 0.9
            
        # Конец квартала
        if (month in [3, 6, 9, 12] and day >= 25):
            score *= 0.8
            
        # Праздничные периоды (упрощенно)
        if month == 12 and day >= 20:  # Рождественский период
            score *= 0.5
        if month == 7 or month == 8:  # Летний период
            score *= 0.85
            
        return score
    
    def _get_recommendation(self, 
                           score: float, 
                           strategy_type: str,
                           current_time: datetime) -> str:
        """
        Формирование рекомендации на основе скора.
        """
        hour = current_time.hour
        strategy_timing = self.strategy_timing.get(strategy_type, {})
        
        # Жесткие ограничения
        if hour in strategy_timing.get('avoid_hours', []):
            return 'avoid'
            
        # Рекомендации по скору
        if score >= 0.7:
            return 'start_now'
        elif score >= 0.5:
            return 'acceptable'
        elif score >= 0.3:
            return 'wait'
        else:
            return 'avoid'
    
    def _calculate_confidence(self, 
                            historical_data: pd.DataFrame,
                            current_time: datetime) -> float:
        """
        Расчет уверенности в прогнозе.
        """
        confidence = 0.5  # Базовая уверенность
        
        # Увеличиваем уверенность при наличии данных
        hour = current_time.hour
        if hour in self.historical_performance:
            sample_size = self.historical_performance[hour].get('count', 0)
            if sample_size >= self.min_sample_size:
                confidence += 0.2
            if sample_size >= self.min_sample_size * 2:
                confidence += 0.1
                
        # Уверенность выше в типичные торговые часы
        session = self._get_trading_session(current_time)
        if session in ['european', 'american', 'overlap_eu_us']:
            confidence += 0.1
            
        # Снижаем уверенность в выходные
        if current_time.weekday() >= 5:
            confidence *= 0.7
            
        return min(1.0, max(0.0, confidence))
    
    def find_best_launch_windows(self,
                                historical_data: pd.DataFrame,
                                strategy_type: str = 'trend_following',
                                next_hours: int = 24) -> List[TimingScore]:
        """
        Поиск лучших окон для запуска в ближайшие N часов.
        
        Args:
            historical_data: Исторические данные
            strategy_type: Тип стратегии
            next_hours: Количество часов для анализа
            
        Returns:
            List[TimingScore]: Отсортированный список лучших времен
        """
        current_time = datetime.now()
        windows = []
        
        for hours_ahead in range(next_hours):
            check_time = current_time + timedelta(hours=hours_ahead)
            score = self.analyze_timing(historical_data, strategy_type, check_time)
            windows.append(score)
            
        # Сортируем по скору
        windows.sort(key=lambda x: x.score, reverse=True)
        
        # Возвращаем топ-5 окон
        return windows[:5]
    
    def get_session_schedule(self) -> Dict:
        """
        Получение расписания торговых сессий с рекомендациями.
        """
        schedule = {}
        
        for session, (start, end) in self.trading_sessions.items():
            schedule[session] = {
                'start': start.strftime('%H:%M'),
                'end': end.strftime('%H:%M'),
                'timezone': 'UTC',
                'characteristics': self._get_session_characteristics(session)
            }
            
        # Добавляем информацию о пересечениях
        schedule['overlaps'] = {
            'EU/US': {
                'time': '13:00-16:00 UTC',
                'characteristics': 'Highest liquidity and volatility'
            },
            'EU/Asia': {
                'time': '07:00-09:00 UTC', 
                'characteristics': 'Moderate liquidity, good for breakouts'
            },
            'Asia/Sydney': {
                'time': '00:00-02:00 UTC',
                'characteristics': 'Low volatility, range-bound'
            }
        }
        
        return schedule
    
    def _get_session_characteristics(self, session: str) -> Dict:
        """
        Характеристики торговой сессии.
        """
        characteristics = {
            'asian': {
                'volatility': 'low',
                'liquidity': 'medium',
                'best_for': ['range_trading', 'carry_trades'],
                'pairs': ['USDJPY', 'AUDJPY', 'NZDJPY']
            },
            'european': {
                'volatility': 'medium-high',
                'liquidity': 'high',
                'best_for': ['trend_following', 'breakout'],
                'pairs': ['EURUSD', 'GBPUSD', 'EURGBP']
            },
            'american': {
                'volatility': 'high',
                'liquidity': 'high',
                'best_for': ['trend_following', 'news_trading'],
                'pairs': ['EURUSD', 'GBPUSD', 'USDCAD']
            },
            'sydney': {
                'volatility': 'low',
                'liquidity': 'low',
                'best_for': ['range_trading'],
                'pairs': ['AUDUSD', 'NZDUSD', 'AUDNZD']
            }
        }
        
        return characteristics.get(session, {})
    
    def optimize_schedule(self,
                         historical_data: pd.DataFrame,
                         strategy_type: str,
                         risk_tolerance: str = 'medium') -> Dict:
        """
        Оптимизация расписания торговли на основе исторических данных.
        
        Args:
            historical_data: Исторические данные
            strategy_type: Тип стратегии
            risk_tolerance: Уровень риска ('low', 'medium', 'high')
            
        Returns:
            Dict: Оптимизированное расписание
        """
        # Анализируем все часы недели
        weekly_scores = {}
        
        for weekday in range(7):
            daily_scores = {}
            for hour in range(24):
                # Создаем время для проверки
                check_time = datetime.now().replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                # Устанавливаем нужный день недели
                days_ahead = (weekday - check_time.weekday()) % 7
                check_time = check_time + timedelta(days=days_ahead)
                
                score = self.analyze_timing(historical_data, strategy_type, check_time)
                daily_scores[hour] = score
                
            weekly_scores[weekday] = daily_scores
            
        # Формируем рекомендации
        schedule = {
            'recommended_hours': [],
            'avoid_hours': [],
            'best_days': [],
            'worst_days': []
        }
        
        # Анализ по часам
        for weekday, hours_data in weekly_scores.items():
            for hour, timing_score in hours_data.items():
                if timing_score.score >= 0.7:
                    schedule['recommended_hours'].append({
                        'day': weekday,
                        'hour': hour,
                        'score': timing_score.score,
                        'session': timing_score.session
                    })
                elif timing_score.score < 0.3:
                    schedule['avoid_hours'].append({
                        'day': weekday,
                        'hour': hour,
                        'score': timing_score.score,
                        'reason': timing_score.recommendation
                    })
                    
        # Сортировка и ограничение результатов
        schedule['recommended_hours'].sort(key=lambda x: x['score'], reverse=True)
        schedule['recommended_hours'] = schedule['recommended_hours'][:20]
        
        # Применение фильтров риска
        if risk_tolerance == 'low':
            # Только самые надежные часы
            schedule['recommended_hours'] = [
                h for h in schedule['recommended_hours'] 
                if h['score'] >= 0.8
            ]
        elif risk_tolerance == 'high':
            # Добавляем больше возможностей
            schedule['recommended_hours'] = [
                h for h in schedule['recommended_hours'] 
                if h['score'] >= 0.6
            ]
            
        return schedule