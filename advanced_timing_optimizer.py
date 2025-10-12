#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Расширенный модуль для оптимизации времени запуска торгового робота
Включает в себя анализ экономических событий, сезонности и машинное обучение
"""

import numpy as np
import pandas as pd
import datetime as dt
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import warnings
warnings.filterwarnings('ignore')

@dataclass
class EconomicEvent:
    """Экономическое событие"""
    name: str
    time: dt.datetime
    currency: str
    impact: str  # 'low', 'medium', 'high'
    forecast: Optional[float] = None
    actual: Optional[float] = None

@dataclass
class TimingFeatures:
    """Признаки для анализа оптимального времени"""
    hour: int
    day_of_week: int
    day_of_month: int
    month: int
    quarter: int
    is_month_end: bool
    is_quarter_end: bool
    is_year_end: bool
    session_overlap: str  # 'asian', 'european', 'american', 'overlap'
    volatility_forecast: float
    economic_impact_score: float

class EconomicCalendar:
    """Календарь экономических событий"""
    
    def __init__(self):
        self.events = []
        self.impact_weights = {'low': 0.1, 'medium': 0.5, 'high': 1.0}
        
    def add_event(self, event: EconomicEvent):
        """Добавляет событие в календарь"""
        self.events.append(event)
        
    def get_events_for_period(self, start_time: dt.datetime, 
                             end_time: dt.datetime) -> List[EconomicEvent]:
        """Получает события для указанного периода"""
        return [event for event in self.events 
                if start_time <= event.time <= end_time]
    
    def calculate_impact_score(self, target_time: dt.datetime, 
                              window_hours: int = 4) -> float:
        """
        Рассчитывает совокупный импакт экономических событий
        в окне времени вокруг целевого времени
        """
        start_time = target_time - dt.timedelta(hours=window_hours)
        end_time = target_time + dt.timedelta(hours=window_hours)
        
        events = self.get_events_for_period(start_time, end_time)
        total_impact = 0
        
        for event in events:
            # Вес события уменьшается с расстоянием по времени
            time_distance = abs((event.time - target_time).total_seconds() / 3600)
            distance_weight = max(0, 1 - (time_distance / window_hours))
            
            impact_weight = self.impact_weights.get(event.impact, 0)
            total_impact += impact_weight * distance_weight
            
        return total_impact
    
    def create_sample_calendar(self) -> None:
        """Создает примерный календарь событий"""
        base_date = dt.datetime(2024, 1, 1)
        
        # NFP (первая пятница месяца)
        for month in range(1, 13):
            first_day = dt.datetime(2024, month, 1)
            # Находим первую пятницу
            days_to_friday = (4 - first_day.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            first_friday = first_day + dt.timedelta(days=days_to_friday)
            
            self.add_event(EconomicEvent(
                name="Non-Farm Payrolls (NFP)",
                time=first_friday.replace(hour=15, minute=30),  # 15:30 MSK
                currency="USD",
                impact="high"
            ))
        
        # Решения центробанков (примерные даты)
        fed_dates = [
            (3, 20), (5, 1), (6, 12), (7, 31), (9, 18), (11, 7), (12, 18)
        ]
        for month, day in fed_dates:
            try:
                self.add_event(EconomicEvent(
                    name="FOMC Decision",
                    time=dt.datetime(2024, month, day, 21, 0),  # 21:00 MSK
                    currency="USD",
                    impact="high"
                ))
            except ValueError:
                continue
        
        # CPI данные (примерно середина месяца)
        for month in range(1, 13):
            try:
                self.add_event(EconomicEvent(
                    name="US CPI",
                    time=dt.datetime(2024, month, 15, 16, 30),
                    currency="USD",
                    impact="high"
                ))
            except ValueError:
                continue

class SessionAnalyzer:
    """Анализатор торговых сессий"""
    
    def __init__(self):
        self.session_times = {
            'asian': (0, 9),      # 00:00 - 09:00 MSK
            'european': (9, 17),   # 09:00 - 17:00 MSK
            'american': (16, 1),   # 16:00 - 01:00 MSK (следующего дня)
        }
        
    def get_current_session(self, hour: int) -> str:
        """Определяет текущую торговую сессию"""
        if 0 <= hour < 9:
            return 'asian'
        elif 9 <= hour < 16:
            return 'european'
        elif 16 <= hour < 18:
            return 'euro_us_overlap'
        elif 18 <= hour <= 23:
            return 'american'
        else:
            return 'low_liquidity'
    
    def get_overlap_periods(self) -> List[Tuple[int, int, str]]:
        """Возвращает периоды пересечения торговых сессий"""
        return [
            (7, 9, 'asian_european'),    # Пересечение азиатской и европейской
            (16, 18, 'european_american'), # Пересечение европейской и американской
        ]

class SeasonalityAnalyzer:
    """Анализатор сезонных паттернов"""
    
    def __init__(self):
        self.monthly_patterns = {}
        self.weekly_patterns = {}
        self.daily_patterns = {}
        
    def analyze_seasonal_patterns(self, performance_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Анализирует сезонные паттерны в производительности
        
        Args:
            performance_data: DataFrame с колонками 'timestamp', 'pnl'
        """
        if performance_data.empty:
            return {}
            
        df = performance_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Извлекаем временные компоненты
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['quarter'] = df['timestamp'].dt.quarter
        
        # Анализируем паттерны
        patterns = {}
        
        # Месячная сезонность
        monthly_perf = df.groupby('month')['pnl'].agg(['mean', 'std', 'count'])
        monthly_perf['sharpe'] = monthly_perf['mean'] / monthly_perf['std']
        patterns['monthly'] = monthly_perf.to_dict()
        
        # Недельная сезонность
        weekly_perf = df.groupby('day_of_week')['pnl'].agg(['mean', 'std', 'count'])
        weekly_perf['sharpe'] = weekly_perf['mean'] / weekly_perf['std']
        patterns['weekly'] = weekly_perf.to_dict()
        
        # Дневная сезонность (по часам)
        hourly_perf = df.groupby('hour')['pnl'].agg(['mean', 'std', 'count'])
        hourly_perf['sharpe'] = hourly_perf['mean'] / hourly_perf['std']
        patterns['hourly'] = hourly_perf.to_dict()
        
        # Квартальная сезонность
        quarterly_perf = df.groupby('quarter')['pnl'].agg(['mean', 'std', 'count'])
        quarterly_perf['sharpe'] = quarterly_perf['mean'] / quarterly_perf['std']
        patterns['quarterly'] = quarterly_perf.to_dict()
        
        return patterns
    
    def get_seasonal_score(self, target_time: dt.datetime, 
                          patterns: Dict[str, Any]) -> float:
        """
        Рассчитывает сезонный скор для заданного времени
        """
        if not patterns:
            return 0.5  # Нейтральный скор
            
        scores = []
        weights = []
        
        # Месячный скор
        if 'monthly' in patterns and 'sharpe' in patterns['monthly']:
            month_sharpe = patterns['monthly']['sharpe'].get(target_time.month, 0)
            scores.append(max(0, min(1, (month_sharpe + 2) / 4)))  # Нормализация
            weights.append(0.2)
        
        # Недельный скор
        if 'weekly' in patterns and 'sharpe' in patterns['weekly']:
            dow_sharpe = patterns['weekly']['sharpe'].get(target_time.weekday(), 0)
            scores.append(max(0, min(1, (dow_sharpe + 2) / 4)))
            weights.append(0.3)
        
        # Часовой скор
        if 'hourly' in patterns and 'sharpe' in patterns['hourly']:
            hour_sharpe = patterns['hourly']['sharpe'].get(target_time.hour, 0)
            scores.append(max(0, min(1, (hour_sharpe + 2) / 4)))
            weights.append(0.5)
        
        if not scores:
            return 0.5
            
        # Взвешенное среднее
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        return weighted_score

class MLTimingPredictor:
    """Предсказатель оптимального времени на основе машинного обучения"""
    
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self.feature_names = [
            'hour', 'day_of_week', 'day_of_month', 'month', 'quarter',
            'is_month_end', 'is_quarter_end', 'session_overlap_score',
            'economic_impact', 'volatility_forecast', 'seasonal_score'
        ]
        
    def extract_features(self, timestamp: dt.datetime, 
                        economic_calendar: EconomicCalendar = None,
                        seasonality_analyzer: SeasonalityAnalyzer = None,
                        seasonal_patterns: Dict = None) -> np.ndarray:
        """Извлекает признаки для заданного времени"""
        
        # Базовые временные признаки
        features = [
            timestamp.hour,
            timestamp.weekday(),
            timestamp.day,
            timestamp.month,
            (timestamp.month - 1) // 3 + 1,  # quarter
        ]
        
        # Специальные даты
        # Конец месяца (последние 3 дня)
        next_month = timestamp.replace(day=28) + dt.timedelta(days=4)
        last_day_of_month = (next_month - dt.timedelta(days=next_month.day)).day
        is_month_end = timestamp.day >= last_day_of_month - 2
        features.append(int(is_month_end))
        
        # Конец квартера
        quarter_end_months = [3, 6, 9, 12]
        is_quarter_end = timestamp.month in quarter_end_months and is_month_end
        features.append(int(is_quarter_end))
        
        # Анализ торговых сессий
        session_analyzer = SessionAnalyzer()
        current_session = session_analyzer.get_current_session(timestamp.hour)
        session_score = {
            'euro_us_overlap': 1.0,
            'european': 0.8,
            'american': 0.7,
            'asian': 0.5,
            'low_liquidity': 0.2
        }.get(current_session, 0.5)
        features.append(session_score)
        
        # Экономическое влияние
        if economic_calendar:
            economic_impact = economic_calendar.calculate_impact_score(timestamp)
        else:
            economic_impact = 0.0
        features.append(economic_impact)
        
        # Прогноз волатильности (упрощенный)
        volatility_forecast = 0.5 + 0.3 * np.sin(timestamp.hour * np.pi / 12)
        features.append(volatility_forecast)
        
        # Сезонный скор
        if seasonality_analyzer and seasonal_patterns:
            seasonal_score = seasonality_analyzer.get_seasonal_score(timestamp, seasonal_patterns)
        else:
            seasonal_score = 0.5
        features.append(seasonal_score)
        
        return np.array(features)
    
    def prepare_training_data(self, performance_data: pd.DataFrame,
                            economic_calendar: EconomicCalendar = None) -> Tuple[np.ndarray, np.ndarray]:
        """Подготавливает данные для обучения"""
        
        if performance_data.empty:
            return np.array([]), np.array([])
            
        # Создаем анализатор сезонности
        seasonality_analyzer = SeasonalityAnalyzer()
        seasonal_patterns = seasonality_analyzer.analyze_seasonal_patterns(performance_data)
        
        features_list = []
        labels = []
        
        for _, row in performance_data.iterrows():
            timestamp = pd.to_datetime(row['timestamp'])
            pnl = row['pnl']
            
            # Извлекаем признаки
            features = self.extract_features(
                timestamp, economic_calendar, seasonality_analyzer, seasonal_patterns
            )
            features_list.append(features)
            
            # Создаем метку (1 если прибыльно, 0 если нет)
            label = 1 if pnl > 0 else 0
            labels.append(label)
        
        return np.array(features_list), np.array(labels)
    
    def train(self, performance_data: pd.DataFrame, 
              economic_calendar: EconomicCalendar = None) -> Dict[str, Any]:
        """Обучает модель предсказания оптимального времени"""
        
        X, y = self.prepare_training_data(performance_data, economic_calendar)
        
        if len(X) == 0:
            return {'error': 'Недостаточно данных для обучения'}
        
        # Разделяем на обучающую и тестовую выборки
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
        )
        
        # Обучаем модель
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Оцениваем качество
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test) if len(X_test) > 0 else train_score
        
        # Важность признаков
        feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
        
        return {
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'feature_importance': feature_importance,
            'n_samples': len(X),
            'model_trained': True
        }
    
    def predict_optimal_timing(self, start_time: dt.datetime, 
                             end_time: dt.datetime,
                             economic_calendar: EconomicCalendar = None) -> List[Tuple[dt.datetime, float]]:
        """
        Предсказывает оптимальное время в заданном интервале
        
        Returns:
            List of (timestamp, probability) tuples sorted by probability
        """
        if not self.is_trained:
            return []
        
        # Создаем временную сетку (каждый час)
        current_time = start_time
        predictions = []
        
        while current_time <= end_time:
            features = self.extract_features(current_time, economic_calendar).reshape(1, -1)
            
            # Получаем вероятность успешной торговли
            probabilities = self.model.predict_proba(features)[0]
            success_probability = probabilities[1] if len(probabilities) > 1 else probabilities[0]
            
            predictions.append((current_time, success_probability))
            current_time += dt.timedelta(hours=1)
        
        # Сортируем по вероятности
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions

class AdvancedTimingOptimizer:
    """Продвинутый оптимизатор времени запуска"""
    
    def __init__(self):
        self.economic_calendar = EconomicCalendar()
        self.session_analyzer = SessionAnalyzer()
        self.seasonality_analyzer = SeasonalityAnalyzer()
        self.ml_predictor = MLTimingPredictor()
        
        # Создаем примерный календарь
        self.economic_calendar.create_sample_calendar()
        
    def comprehensive_timing_analysis(self, 
                                   performance_data: pd.DataFrame) -> Dict[str, Any]:
        """Комплексный анализ оптимального времени"""
        
        results = {}
        
        # 1. Сезонный анализ
        print("Выполняется сезонный анализ...")
        seasonal_patterns = self.seasonality_analyzer.analyze_seasonal_patterns(performance_data)
        results['seasonal_analysis'] = seasonal_patterns
        
        # 2. Анализ торговых сессий
        print("Анализ торговых сессий...")
        session_performance = self._analyze_session_performance(performance_data)
        results['session_analysis'] = session_performance
        
        # 3. Влияние экономических событий
        print("Анализ влияния экономических событий...")
        economic_impact = self._analyze_economic_impact(performance_data)
        results['economic_impact'] = economic_impact
        
        # 4. Машинное обучение
        print("Обучение ML модели...")
        ml_results = self.ml_predictor.train(performance_data, self.economic_calendar)
        results['ml_analysis'] = ml_results
        
        # 5. Интегрированные рекомендации
        recommendations = self._generate_integrated_recommendations(results)
        results['recommendations'] = recommendations
        
        return results
    
    def _analyze_session_performance(self, performance_data: pd.DataFrame) -> Dict[str, Any]:
        """Анализ производительности по торговым сессиям"""
        if performance_data.empty:
            return {}
            
        df = performance_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        
        # Определяем сессию для каждой записи
        df['session'] = df['hour'].apply(self.session_analyzer.get_current_session)
        
        # Анализ по сессиям
        session_stats = df.groupby('session')['pnl'].agg(['mean', 'std', 'count', 'sum'])
        session_stats['sharpe'] = session_stats['mean'] / session_stats['std']
        session_stats['win_rate'] = df.groupby('session')['pnl'].apply(lambda x: (x > 0).mean())
        
        return session_stats.to_dict()
    
    def _analyze_economic_impact(self, performance_data: pd.DataFrame) -> Dict[str, Any]:
        """Анализ влияния экономических событий"""
        if performance_data.empty:
            return {}
        
        df = performance_data.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Рассчитываем экономический импакт для каждой сделки
        impact_scores = []
        for timestamp in df['timestamp']:
            score = self.economic_calendar.calculate_impact_score(timestamp)
            impact_scores.append(score)
        
        df['economic_impact'] = impact_scores
        
        # Разделяем на категории по уровню импа��та
        df['impact_level'] = pd.cut(df['economic_impact'], 
                                   bins=[0, 0.1, 0.5, float('inf')], 
                                   labels=['low', 'medium', 'high'])
        
        # Анализ по уровням импакта
        impact_stats = df.groupby('impact_level')['pnl'].agg(['mean', 'std', 'count'])
        
        return {
            'impact_correlation': df['pnl'].corr(df['economic_impact']),
            'impact_stats': impact_stats.to_dict(),
            'high_impact_events': len(df[df['impact_level'] == 'high'])
        }
    
    def _generate_integrated_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Генерирует интегрированные рекомендации"""
        recommendations = []
        
        # Рекомендации на основе сезонного анализа
        if 'seasonal_analysis' in analysis_results and 'hourly' in analysis_results['seasonal_analysis']:
            hourly_sharpe = analysis_results['seasonal_analysis']['hourly'].get('sharpe', {})
            if hourly_sharpe:
                best_hours = sorted(hourly_sharpe.items(), key=lambda x: x[1], reverse=True)[:3]
                hours_str = ', '.join([f"{h}:00" for h, _ in best_hours])
                recommendations.append(f"Лучшие часы по историческим данным: {hours_str}")
        
        # Рекомендации на основе торговых сессий
        if 'session_analysis' in analysis_results:
            session_sharpe = analysis_results['session_analysis'].get('sharpe', {})
            if session_sharpe:
                best_session = max(session_sharpe.items(), key=lambda x: x[1])
                recommendations.append(f"Лучшая торговая сессия: {best_session[0]} (Sharpe: {best_session[1]:.2f})")
        
        # Рекомендации на основе экономических событий
        if 'economic_impact' in analysis_results:
            correlation = analysis_results['economic_impact'].get('impact_correlation', 0)
            if correlation < -0.1:
                recommendations.append("Избегайте торговли во время крупных экономических событий")
            elif correlation > 0.1:
                recommendations.append("Экономические события могут быть благоприятны для торговли")
        
        # Рекомендации на основе ML
        if 'ml_analysis' in analysis_results and analysis_results['ml_analysis'].get('model_trained'):
            accuracy = analysis_results['ml_analysis'].get('test_accuracy', 0)
            if accuracy > 0.6:
                recommendations.append(f"ML модель обучена (точность: {accuracy:.1%}) - используйте предсказания")
                
                # Топ признаки
                importance = analysis_results['ml_analysis'].get('feature_importance', {})
                if importance:
                    top_feature = max(importance.items(), key=lambda x: x[1])
                    recommendations.append(f"Наиболее важный фактор: {top_feature[0]}")
        
        # Общие рекомендации
        recommendations.extend([
            "Мониторьте волатильность перед запуском",
            "Учитывайте пересечения торговых сессий",
            "Ведите детальную статистику для улучшения анализа",
            "Регулярно переобучайте ML модель на новых данных"
        ])
        
        return recommendations
    
    def get_next_optimal_times(self, n_hours: int = 24) -> List[Tuple[dt.datetime, float, str]]:
        """
        Получает следующие оптимальные времена для запуска
        
        Returns:
            List of (timestamp, score, reason) tuples
        """
        if not self.ml_predictor.is_trained:
            return self._get_heuristic_optimal_times(n_hours)
        
        start_time = dt.datetime.now()
        end_time = start_time + dt.timedelta(hours=n_hours)
        
        predictions = self.ml_predictor.predict_optimal_timing(
            start_time, end_time, self.economic_calendar
        )
        
        # Добавляем причины
        results = []
        for timestamp, probability in predictions[:10]:  # Топ 10
            reason = self._explain_timing_score(timestamp, probability)
            results.append((timestamp, probability, reason))
        
        return results
    
    def _get_heuristic_optimal_times(self, n_hours: int) -> List[Tuple[dt.datetime, float, str]]:
        """Эвристические оптимальные времена при отсутствии обученной модели"""
        start_time = dt.datetime.now()
        results = []
        
        for i in range(n_hours):
            timestamp = start_time + dt.timedelta(hours=i)
            score = self._calculate_heuristic_score(timestamp)
            reason = self._explain_heuristic_score(timestamp, score)
            results.append((timestamp, score, reason))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:10]
    
    def _calculate_heuristic_score(self, timestamp: dt.datetime) -> float:
        """Эвристический расчет скора времени"""
        score = 0.5  # Базовый скор
        
        # Торговая сессия
        session = self.session_analyzer.get_current_session(timestamp.hour)
        session_scores = {
            'euro_us_overlap': 0.9,
            'european': 0.8,
            'american': 0.7,
            'asian': 0.5,
            'low_liquidity': 0.2
        }
        score = session_scores.get(session, 0.5)
        
        # Экономические события
        economic_impact = self.economic_calendar.calculate_impact_score(timestamp)
        score *= max(0.5, 1.0 - economic_impact)  # Снижаем скор при высоком импакте
        
        # День недели
        if timestamp.weekday() >= 5:  # Выходные
            score *= 0.3
        
        return max(0, min(1, score))
    
    def _explain_timing_score(self, timestamp: dt.datetime, score: float) -> str:
        """Объясняет скор времени"""
        reasons = []
        
        session = self.session_analyzer.get_current_session(timestamp.hour)
        if session == 'euro_us_overlap':
            reasons.append("пересечение сессий")
        elif session in ['european', 'american']:
            reasons.append(f"{session} сессия")
        
        if timestamp.weekday() >= 5:
            reasons.append("выходной день")
        
        economic_impact = self.economic_calendar.calculate_impact_score(timestamp)
        if economic_impact > 0.5:
            reasons.append("высокий экономический импакт")
        
        if score > 0.7:
            return f"Отличное время: {', '.join(reasons) if reasons else 'благоприятные условия'}"
        elif score > 0.5:
            return f"Хорошее время: {', '.join(reasons) if reasons else 'нормальные условия'}"
        else:
            return f"Осторожно: {', '.join(reasons) if reasons else 'неблагоприятные условия'}"
    
    def _explain_heuristic_score(self, timestamp: dt.datetime, score: float) -> str:
        """Объясняет эвристический скор"""
        return self._explain_timing_score(timestamp, score)

def create_sample_performance_data(n_samples: int = 1000) -> pd.DataFrame:
    """Создает примерные данные о производительности для тестирования"""
    np.random.seed(42)
    
    # Генерируем временные метки
    start_date = dt.datetime(2024, 1, 1)
    timestamps = []
    
    for i in range(n_samples):
        # Случайное время в течение года
        days_offset = np.random.randint(0, 365)
        hours_offset = np.random.randint(0, 24)
        timestamp = start_date + dt.timedelta(days=days_offset, hours=hours_offset)
        timestamps.append(timestamp)
    
    df = pd.DataFrame({'timestamp': timestamps})
    
    # Генерируем PnL с учетом паттернов
    pnl_values = []
    
    for timestamp in timestamps:
        base_pnl = np.random.normal(0.001, 0.02)  # Базовая доходность
        
        # Корректировка на час (европейская и американская сессии лучше)
        hour_multiplier = 1.0
        if 9 <= timestamp.hour <= 17:  # Европейская сессия
            hour_multiplier = 1.2
        elif 16 <= timestamp.hour <= 18:  # Пересечение сессий
            hour_multiplier = 1.5
        elif timestamp.hour in [22, 23, 0, 1, 2, 3]:  # Ночь
            hour_multiplier = 0.7
        
        # Корректировка на день недели
        dow_multiplier = 1.0
        if timestamp.weekday() >= 5:  # Выходные
            dow_multiplier = 0.5
        elif timestamp.weekday() in [1, 2, 3]:  # Вт-Чт
            dow_multiplier = 1.1
        
        # Месячная сезонность
        month_multiplier = 1.0 + 0.1 * np.sin(timestamp.month * np.pi / 6)
        
        final_pnl = base_pnl * hour_multiplier * dow_multiplier * month_multiplier
        pnl_values.append(final_pnl)
    
    df['pnl'] = pnl_values
    return df.sort_values('timestamp').reset_index(drop=True)

if __name__ == "__main__":
    print("=== Расширенная система оптимизации времени запуска ===\n")
    
    # Создаем оптимизатор
    optimizer = AdvancedTimingOptimizer()
    
    # Создаем примерные данные
    print("1. Создание тестовых данных о производительности...")
    performance_data = create_sample_performance_data(1000)
    print(f"   Создано {len(performance_data)} записей о сделках")
    
    # Комплексный анализ
    print("\n2. Выполнение комплексного анализа...")
    analysis_results = optimizer.comprehensive_timing_analysis(performance_data)
    
    # Выводим результаты
    print("\n3. Результаты анализа:")
    
    if 'ml_analysis' in analysis_results:
        ml_results = analysis_results['ml_analysis']
        if ml_results.get('model_trained'):
            print(f"   ML модель обучена на {ml_results['n_samples']} образцах")
            print(f"   Точность: {ml_results['test_accuracy']:.1%}")
            
            # Топ-3 важных признака
            importance = ml_results.get('feature_importance', {})
            if importance:
                top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
                print("   Наиболее важные факторы:")
                for feature, imp in top_features:
                    print(f"     - {feature}: {imp:.3f}")
    
    # Рекомендации
    if 'recommendations' in analysis_results:
        print("\n4. Рекомендации:")
        for i, rec in enumerate(analysis_results['recommendations'][:7], 1):
            print(f"   {i}. {rec}")
    
    # Следующие оптимальные времена
    print("\n5. Следующие оптимальные времена для запуска:")
    optimal_times = optimizer.get_next_optimal_times(48)  # Следующие 48 часов
    
    for i, (timestamp, score, reason) in enumerate(optimal_times[:5], 1):
        time_str = timestamp.strftime('%Y-%m-%d %H:%M')
        print(f"   {i}. {time_str} (скор: {score:.2f}) - {reason}")
    
    print("\n=== Анализ завершен ===")