#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Практическое руководство по оптимизации торгового робота
Объединяет все решения в единую систему
"""

import json
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
import datetime as dt

from trading_robot_optimizer import (
    AdaptiveTradingRobot, MarketCondition, create_sample_market_data
)
from advanced_timing_optimizer import (
    AdvancedTimingOptimizer, create_sample_performance_data
)


class TradingRobotManager:
    """Менеджер торгового робота с полной оптимизацией"""
    
    def __init__(self, config_path: str = "robot_config.json"):
        self.config = self.load_config(config_path)
        self.robot = AdaptiveTradingRobot(self.config["robot_settings"])
        self.timing_optimizer = AdvancedTimingOptimizer()
        self.performance_history = []
        self.is_initialized = False
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Загружает конфигурацию робота"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Конфигурационный файл {config_path} не найден. Используется конфигурация по умолчанию.")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "robot_settings": {
                "base_currency": "USD",
                "initial_balance": 10000,
                "max_risk_per_trade": 0.02
            },
            "market_resilience": {
                "regime_detection": {"lookback_period": 50}
            },
            "timing_optimization": {
                "ml_settings": {"min_samples": 100}
            }
        }
    
    def initialize_system(self, historical_data: pd.DataFrame = None):
        """Инициализирует систему с историческими данными"""
        print("🚀 Инициализация системы оптимизации...")
        
        # Если нет исторических данных, создаем тестовые
        if historical_data is None:
            print("📊 Создание тестовых данных...")
            historical_data = create_sample_performance_data(500)
        
        # Обучаем систему оптимизации времени
        print("🧠 Обучение системы анализа времени...")
        analysis_results = self.timing_optimizer.comprehensive_timing_analysis(historical_data)
        
        # Обновляем анализ времени в роботе
        self.robot.update_timing_analysis(historical_data)
        
        self.performance_history = historical_data
        self.is_initialized = True
        
        print("✅ Система инициализирована успешно!")
        return analysis_results
    
    def should_start_trading_now(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Комплексная проверка - стоит ли запускать торговлю сейчас
        
        Returns:
            (should_trade, detailed_analysis)
        """
        current_time = dt.datetime.now()
        analysis = {
            'timestamp': current_time,
            'checks': {},
            'final_decision': False,
            'confidence': 0.0,
            'reasons': []
        }
        
        # 1. Базовая проверка времени
        can_trade_basic, reason_basic = self.robot.should_start_trading(current_time)
        analysis['checks']['basic_timing'] = {
            'result': can_trade_basic,
            'reason': reason_basic
        }
        
        if not can_trade_basic:
            analysis['reasons'].append(f"Базовая проверка: {reason_basic}")
            return False, analysis
        
        # 2. ML предсказание (если обучено)
        if hasattr(self.timing_optimizer, 'ml_predictor') and self.timing_optimizer.ml_predictor.is_trained:
            end_time = current_time + dt.timedelta(hours=1)
            predictions = self.timing_optimizer.ml_predictor.predict_optimal_timing(
                current_time, end_time, self.timing_optimizer.economic_calendar
            )
            
            if predictions:
                ml_confidence = predictions[0][1]  # Вероятность успеха
                analysis['checks']['ml_prediction'] = {
                    'confidence': ml_confidence,
                    'threshold': 0.6
                }
                
                if ml_confidence >= 0.6:
                    analysis['reasons'].append(f"ML модель: высокая вероятность успеха ({ml_confidence:.1%})")
                    analysis['confidence'] += 0.4
                else:
                    analysis['reasons'].append(f"ML модель: низкая вероятность успеха ({ml_confidence:.1%})")
        
        # 3. Экономические события
        economic_impact = self.timing_optimizer.economic_calendar.calculate_impact_score(current_time)
        analysis['checks']['economic_events'] = {
            'impact_score': economic_impact,
            'threshold': 0.5
        }
        
        if economic_impact > 0.5:
            analysis['reasons'].append(f"Высокий экономический импакт ({economic_impact:.2f})")
            analysis['confidence'] -= 0.2
        else:
            analysis['confidence'] += 0.1
        
        # 4. Торговая сессия
        session = self.timing_optimizer.session_analyzer.get_current_session(current_time.hour)
        session_scores = {
            'euro_us_overlap': 0.9,
            'european': 0.8,
            'american': 0.7,
            'asian': 0.5,
            'low_liquidity': 0.2
        }
        session_score = session_scores.get(session, 0.5)
        
        analysis['checks']['trading_session'] = {
            'session': session,
            'score': session_score
        }
        
        if session_score >= 0.7:
            analysis['reasons'].append(f"Хорошая торговая сессия: {session}")
            analysis['confidence'] += 0.2
        elif session_score < 0.5:
            analysis['reasons'].append(f"Плохая торговая сессия: {session}")
            analysis['confidence'] -= 0.3
        
        # Итоговое решение
        analysis['confidence'] = max(0, min(1, analysis['confidence'] + 0.5))  # Базовая уверенность 0.5
        analysis['final_decision'] = analysis['confidence'] >= 0.6
        
        if analysis['final_decision']:
            analysis['reasons'].append(f"✅ Рекомендуется запуск (уверенность: {analysis['confidence']:.1%})")
        else:
            analysis['reasons'].append(f"❌ Запуск не рекомендуется (уверенность: {analysis['confidence']:.1%})")
        
        return analysis['final_decision'], analysis
    
    def optimize_for_market_conditions(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Оптимизирует параметры робота под текущие рыночные условия
        """
        print("🔧 Оптимизация под рыночные условия...")
        
        # Анализируем текущие рыночные условия
        market_condition = self.robot.analyze_market_condition(market_data)
        
        # Получаем адаптированные параметры
        regime = market_condition.market_regime
        adapted_params = self.config["market_resilience"]["adaptive_parameters"].get(
            f"{regime}_market", 
            self.config["market_resilience"]["adaptive_parameters"]["ranging_market"]
        )
        
        # Корректируем параметры на основе волатильности
        volatility_adjustment = min(2.0, max(0.5, 1.0 / (1.0 + market_condition.volatility * 5)))
        
        optimized_params = {
            'market_regime': regime,
            'volatility': market_condition.volatility,
            'trend_strength': market_condition.trend_strength,
            'recommended_params': {
                'entry_threshold': adapted_params['entry_threshold'],
                'stop_loss_pct': adapted_params['stop_loss_pct'] * volatility_adjustment,
                'take_profit_pct': adapted_params['take_profit_pct'] * volatility_adjustment,
                'position_size_multiplier': adapted_params['position_size_multiplier'] * volatility_adjustment
            },
            'risk_adjustments': {
                'volatility_adjustment': volatility_adjustment,
                'max_position_size': min(0.05, 0.02 * volatility_adjustment)
            }
        }
        
        print(f"📈 Режим рынка: {regime}")
        print(f"🎯 Волатильность: {market_condition.volatility:.4f}")
        print(f"⚖️  Корректировка риска: {volatility_adjustment:.2f}")
        
        return optimized_params
    
    def get_next_optimal_launch_times(self, hours_ahead: int = 48) -> List[Dict[str, Any]]:
        """
        Получает следующие оптимальные времена запуска
        """
        if not self.is_initialized:
            print("⚠️  Система не инициализирована. Используются эвристические рекомендации.")
        
        optimal_times = self.timing_optimizer.get_next_optimal_times(hours_ahead)
        
        formatted_times = []
        for timestamp, score, reason in optimal_times[:10]:
            formatted_times.append({
                'datetime': timestamp,
                'time_str': timestamp.strftime('%Y-%m-%d %H:%M'),
                'day_name': timestamp.strftime('%A'),
                'score': score,
                'reason': reason,
                'recommendation': self._get_recommendation_level(score)
            })
        
        return formatted_times
    
    def _get_recommendation_level(self, score: float) -> str:
        """Определяет уровень рекомендации по скору"""
        if score >= 0.8:
            return "🟢 Отлично"
        elif score >= 0.65:
            return "🟡 Хорошо"
        elif score >= 0.5:
            return "🟠 Осторожно"
        else:
            return "🔴 Не рекомендуется"
    
    def generate_trading_report(self) -> Dict[str, Any]:
        """Генерирует подробный отчет о состоянии системы"""
        current_time = dt.datetime.now()
        
        # Проверяем текущую возможность торговли
        can_trade, analysis = self.should_start_trading_now()
        
        # Получаем следующие оптимальные времена
        optimal_times = self.get_next_optimal_launch_times(24)
        
        # Статистика системы
        system_stats = {
            'initialization_status': self.is_initialized,
            'ml_model_trained': (
                hasattr(self.timing_optimizer, 'ml_predictor') and 
                self.timing_optimizer.ml_predictor.is_trained
            ),
            'historical_data_points': len(self.performance_history) if not self.performance_history.empty else 0
        }
        
        report = {
            'generated_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_status': system_stats,
            'current_analysis': analysis,
            'next_optimal_times': optimal_times[:5],  # Топ-5
            'recommendations': self._generate_current_recommendations(analysis, optimal_times)
        }
        
        return report
    
    def _generate_current_recommendations(self, current_analysis: Dict, optimal_times: List) -> List[str]:
        """Генерирует текущие рекомендации"""
        recommendations = []
        
        # Текущее состояние
        if current_analysis['final_decision']:
            recommendations.append("✅ Сейчас хорошее время для запуска робота")
        else:
            next_good_time = None
            for time_info in optimal_times:
                if time_info['score'] >= 0.65:
                    next_good_time = time_info
                    break
            
            if next_good_time:
                recommendations.append(
                    f"⏰ Следующее хорошее время: {next_good_time['time_str']} "
                    f"({next_good_time['reason']})"
                )
            else:
                recommendations.append("⚠️ В ближайшие 24 часа нет явно благоприятных моментов")
        
        # Общие рекомендации
        recommendations.extend([
            "📊 Мониторьте волатильность перед запуском",
            "📅 Избегайте запуска в выходные дни",
            "📰 Проверяйте экономический календарь",
            "📈 Адаптируйте параметры под текущий режим рынка",
            "📋 Ведите детальную статистику для улучшения анализа"
        ])
        
        return recommendations

def main():
    """Основная функция демонстрации системы"""
    print("=" * 60)
    print("🤖 СИСТЕМА ОПТИМИЗАЦИИ ТОРГОВОГО РОБОТА")
    print("=" * 60)
    
    # Создаем менеджера
    manager = TradingRobotManager()
    
    # Инициализируем систему
    print("\n1. ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ")
    print("-" * 30)
    analysis_results = manager.initialize_system()
    
    # Создаем тестовые рыночные данные
    print("\n2. АНАЛИЗ РЫНОЧНЫХ УСЛОВИЙ")
    print("-" * 30)
    market_data = create_sample_market_data()
    market_optimization = manager.optimize_for_market_conditions(market_data.tail(100))
    
    print(f"Рекомендованные параметры для режима '{market_optimization['market_regime']}':")
    for param, value in market_optimization['recommended_params'].items():
        if isinstance(value, float):
            print(f"  • {param}: {value:.3f}")
        else:
            print(f"  • {param}: {value}")
    
    # Проверяем текущую ситуацию
    print("\n3. ТЕКУЩИЙ АНАЛИЗ")
    print("-" * 30)
    can_trade, current_analysis = manager.should_start_trading_now()
    
    print(f"Можно торговать сейчас: {'✅ ДА' if can_trade else '❌ НЕТ'}")
    print(f"Уверенность: {current_analysis['confidence']:.1%}")
    print("\nПричины:")
    for reason in current_analysis['reasons']:
        print(f"  • {reason}")
    
    # Получаем оптимальные времена
    print("\n4. СЛЕДУЮЩИЕ ОПТИМАЛЬНЫЕ ВРЕМЕНА")
    print("-" * 30)
    optimal_times = manager.get_next_optimal_launch_times(48)
    
    for i, time_info in enumerate(optimal_times[:7], 1):
        print(f"{i}. {time_info['time_str']} ({time_info['day_name']}) - "
              f"{time_info['recommendation']} - {time_info['reason']}")
    
    # Генерируем итоговый отчет
    print("\n5. ИТОГОВЫЕ РЕКОМЕНДАЦИИ")
    print("-" * 30)
    report = manager.generate_trading_report()
    
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    print("\n" + "=" * 60)
    print("🎯 АНАЛИЗ ЗАВЕРШЕН")
    print("💡 Используйте эти рекомендации для оптимизации вашего торгового робота")
    print("=" * 60)

if __name__ == "__main__":
    main()