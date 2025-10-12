"""
Модуль динамической настройки параметров торгового робота.
Автоматически оптимизирует параметры в реальном времени на основе текущих условий.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from scipy.optimize import minimize, differential_evolution
import json
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ParameterConfig:
    """Конфигурация параметра для оптимизации"""
    name: str
    current_value: float
    min_value: float
    max_value: float
    step: float
    optimization_weight: float = 1.0
    adapt_speed: float = 0.1
    parameter_type: str = 'continuous'  # 'continuous', 'discrete', 'boolean'
    dependencies: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class OptimizationResult:
    """Результат оптимизации параметров"""
    parameters: Dict[str, float]
    performance_score: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    optimization_time: datetime
    confidence: float


class DynamicParameterOptimizer:
    """
    Динамический оптимизатор параметров с использованием:
    1. Байесовской оптимизации
    2. Генетических алгоритмов
    3. Walk-forward анализа
    4. Адаптивной корректировки
    """
    
    def __init__(self,
                 lookback_window: int = 500,
                 optimization_frequency: int = 50,
                 min_trades_required: int = 30):
        """
        Args:
            lookback_window: Окно для анализа исторических данных
            optimization_frequency: Частота переоптимизации (в барах)
            min_trades_required: Минимальное количество сделок для оптимизации
        """
        self.lookback_window = lookback_window
        self.optimization_frequency = optimization_frequency
        self.min_trades_required = min_trades_required
        
        # Параметры для оптимизации
        self.parameter_configs = self._initialize_parameters()
        
        # История оптимизаций
        self.optimization_history = []
        self.current_parameters = {}
        self.bars_since_optimization = 0
        
        # Метрики для отслеживания
        self.performance_metrics = {
            'sharpe_ratio': [],
            'win_rate': [],
            'profit_factor': [],
            'max_drawdown': []
        }
        
    def _initialize_parameters(self) -> Dict[str, ParameterConfig]:
        """
        Инициализация конфигураций параметров.
        """
        return {
            # Параметры входа
            'signal_threshold': ParameterConfig(
                name='signal_threshold',
                current_value=0.6,
                min_value=0.3,
                max_value=0.9,
                step=0.05,
                optimization_weight=1.2,
                description='Порог силы сигнала для входа'
            ),
            
            # Параметры риск-менеджмента
            'stop_loss_atr_mult': ParameterConfig(
                name='stop_loss_atr_mult',
                current_value=2.0,
                min_value=0.5,
                max_value=4.0,
                step=0.25,
                optimization_weight=1.5,
                description='Множитель ATR для стоп-лосса'
            ),
            
            'take_profit_atr_mult': ParameterConfig(
                name='take_profit_atr_mult',
                current_value=3.0,
                min_value=1.0,
                max_value=6.0,
                step=0.25,
                optimization_weight=1.3,
                description='Множитель ATR для тейк-профита'
            ),
            
            'position_size_pct': ParameterConfig(
                name='position_size_pct',
                current_value=0.02,
                min_value=0.005,
                max_value=0.05,
                step=0.005,
                optimization_weight=1.4,
                description='Процент капитала на позицию'
            ),
            
            # Параметры индикаторов
            'ma_fast_period': ParameterConfig(
                name='ma_fast_period',
                current_value=20,
                min_value=5,
                max_value=50,
                step=5,
                parameter_type='discrete',
                optimization_weight=1.0,
                description='Период быстрой MA'
            ),
            
            'ma_slow_period': ParameterConfig(
                name='ma_slow_period',
                current_value=50,
                min_value=20,
                max_value=200,
                step=10,
                parameter_type='discrete',
                optimization_weight=1.0,
                dependencies=['ma_fast_period'],  # Должен быть больше ma_fast
                description='Период медленной MA'
            ),
            
            'rsi_period': ParameterConfig(
                name='rsi_period',
                current_value=14,
                min_value=5,
                max_value=30,
                step=1,
                parameter_type='discrete',
                optimization_weight=0.8,
                description='Период RSI'
            ),
            
            'rsi_overbought': ParameterConfig(
                name='rsi_overbought',
                current_value=70,
                min_value=60,
                max_value=85,
                step=5,
                parameter_type='discrete',
                optimization_weight=0.8,
                description='Уровень перекупленности RSI'
            ),
            
            'rsi_oversold': ParameterConfig(
                name='rsi_oversold',
                current_value=30,
                min_value=15,
                max_value=40,
                step=5,
                parameter_type='discrete',
                optimization_weight=0.8,
                description='Уровень перепроданности RSI'
            ),
            
            # Параметры фильтров
            'volatility_filter_enabled': ParameterConfig(
                name='volatility_filter_enabled',
                current_value=1,
                min_value=0,
                max_value=1,
                step=1,
                parameter_type='boolean',
                optimization_weight=0.6,
                description='Включить фильтр волатильности'
            ),
            
            'max_volatility': ParameterConfig(
                name='max_volatility',
                current_value=0.03,
                min_value=0.01,
                max_value=0.05,
                step=0.005,
                optimization_weight=0.7,
                description='Максимальная волатильность для торговли'
            ),
            
            'trend_filter_strength': ParameterConfig(
                name='trend_filter_strength',
                current_value=0.5,
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                optimization_weight=0.9,
                description='Сила трендового фильтра'
            ),
            
            # Параметры выхода
            'trailing_stop_enabled': ParameterConfig(
                name='trailing_stop_enabled',
                current_value=1,
                min_value=0,
                max_value=1,
                step=1,
                parameter_type='boolean',
                optimization_weight=1.0,
                description='Включить trailing stop'
            ),
            
            'trailing_stop_distance': ParameterConfig(
                name='trailing_stop_distance',
                current_value=0.015,
                min_value=0.005,
                max_value=0.03,
                step=0.005,
                optimization_weight=1.1,
                description='Дистанция trailing stop'
            ),
            
            # Параметры времени
            'max_holding_period': ParameterConfig(
                name='max_holding_period',
                current_value=100,
                min_value=20,
                max_value=500,
                step=20,
                parameter_type='discrete',
                optimization_weight=0.7,
                description='Максимальный период удержания (бары)'
            )
        }
    
    def optimize_parameters(self,
                           price_data: pd.DataFrame,
                           trade_history: List[Dict],
                           market_regime: str = 'unknown',
                           method: str = 'adaptive') -> OptimizationResult:
        """
        Оптимизация параметров торговой стратегии.
        
        Args:
            price_data: Исторические ценовые данные
            trade_history: История сделок
            market_regime: Текущий рыночный режим
            method: Метод оптимизации ('adaptive', 'genetic', 'bayesian', 'grid')
            
        Returns:
            OptimizationResult: Результат оптимизации
        """
        # Проверка необходимости оптимизации
        if not self._should_optimize(trade_history):
            return self._get_current_optimization_result()
            
        # Выбор метода оптимизации
        if method == 'adaptive':
            result = self._adaptive_optimization(price_data, trade_history, market_regime)
        elif method == 'genetic':
            result = self._genetic_optimization(price_data, trade_history)
        elif method == 'bayesian':
            result = self._bayesian_optimization(price_data, trade_history)
        else:  # grid
            result = self._grid_search_optimization(price_data, trade_history)
            
        # Валидация результатов
        result = self._validate_optimization_result(result, trade_history)
        
        # Обновление параметров
        self._update_parameters(result)
        
        # Сохранение истории
        self.optimization_history.append(result)
        self.bars_since_optimization = 0
        
        return result
    
    def _should_optimize(self, trade_history: List[Dict]) -> bool:
        """
        Определение необходимости переоптимизации.
        """
        # Проверка минимального количества сделок
        if len(trade_history) < self.min_trades_required:
            return False
            
        # Проверка частоты оптимизации
        if self.bars_since_optimization < self.optimization_frequency:
            return False
            
        # Проверка деградации производительности
        if self._detect_performance_degradation():
            return True
            
        return True
    
    def _detect_performance_degradation(self) -> bool:
        """
        Обнаружение ухудшения производительности.
        """
        if len(self.performance_metrics['sharpe_ratio']) < 10:
            return False
            
        # Сравнение последних метрик с историческими
        recent_sharpe = np.mean(self.performance_metrics['sharpe_ratio'][-5:])
        historical_sharpe = np.mean(self.performance_metrics['sharpe_ratio'][:-5])
        
        # Деградация если упало на 30%+
        if recent_sharpe < historical_sharpe * 0.7:
            return True
            
        # Проверка win rate
        recent_wr = np.mean(self.performance_metrics['win_rate'][-5:])
        historical_wr = np.mean(self.performance_metrics['win_rate'][:-5])
        
        if recent_wr < historical_wr * 0.8:
            return True
            
        return False
    
    def _adaptive_optimization(self,
                              price_data: pd.DataFrame,
                              trade_history: List[Dict],
                              market_regime: str) -> OptimizationResult:
        """
        Адаптивная оптимизация на основе текущего режима рынка.
        """
        # Получаем текущие параметры
        current_params = self._get_current_parameters()
        
        # Адаптация под режим рынка
        adapted_params = self._adapt_to_market_regime(current_params, market_regime)
        
        # Инкрементальная корректировка на основе последних результатов
        if trade_history:
            performance_adjustment = self._calculate_performance_adjustment(trade_history)
            adapted_params = self._apply_performance_adjustment(
                adapted_params, performance_adjustment
            )
            
        # Walk-forward валидация
        validation_score = self._walk_forward_validation(
            price_data, adapted_params, trade_history
        )
        
        # Расчет метрик
        metrics = self._calculate_metrics(trade_history, adapted_params)
        
        return OptimizationResult(
            parameters=adapted_params,
            performance_score=validation_score,
            sharpe_ratio=metrics['sharpe_ratio'],
            win_rate=metrics['win_rate'],
            profit_factor=metrics['profit_factor'],
            max_drawdown=metrics['max_drawdown'],
            optimization_time=datetime.now(),
            confidence=self._calculate_confidence(validation_score, len(trade_history))
        )
    
    def _adapt_to_market_regime(self, 
                               params: Dict[str, float],
                               market_regime: str) -> Dict[str, float]:
        """
        Адаптация параметров к рыночному режиму.
        """
        adapted = params.copy()
        
        regime_adjustments = {
            'trending_up': {
                'signal_threshold': 0.5,  # Менее строгий вход
                'stop_loss_atr_mult': 2.5,  # Шире стопы
                'take_profit_atr_mult': 4.0,  # Больше цели
                'trend_filter_strength': 0.8,  # Сильный трендовый фильтр
                'trailing_stop_enabled': 1,
                'max_holding_period': 200
            },
            'trending_down': {
                'signal_threshold': 0.7,  # Более строгий вход
                'stop_loss_atr_mult': 1.5,  # Уже стопы
                'take_profit_atr_mult': 2.5,  # Меньше цели
                'trend_filter_strength': 0.8,
                'trailing_stop_enabled': 1,
                'max_holding_period': 100
            },
            'ranging': {
                'signal_threshold': 0.6,
                'stop_loss_atr_mult': 1.5,
                'take_profit_atr_mult': 2.0,
                'trend_filter_strength': 0.2,  # Слабый трендовый фильтр
                'trailing_stop_enabled': 0,
                'max_holding_period': 50,
                'rsi_overbought': 65,  # Более чувствительные уровни
                'rsi_oversold': 35
            },
            'volatile': {
                'signal_threshold': 0.8,  # Очень строгий вход
                'stop_loss_atr_mult': 3.0,  # Широкие стопы
                'take_profit_atr_mult': 3.5,
                'position_size_pct': 0.01,  # Меньший размер позиции
                'volatility_filter_enabled': 1,
                'max_volatility': 0.04
            },
            'quiet': {
                'signal_threshold': 0.4,  # Менее строгий вход
                'stop_loss_atr_mult': 1.0,  # Узкие стопы
                'take_profit_atr_mult': 1.5,
                'position_size_pct': 0.03,  # Больший размер позиции
                'volatility_filter_enabled': 0,
                'max_holding_period': 30
            }
        }
        
        # Применяем корректировки для режима
        if market_regime in regime_adjustments:
            adjustments = regime_adjustments[market_regime]
            
            for param, target_value in adjustments.items():
                if param in adapted and param in self.parameter_configs:
                    config = self.parameter_configs[param]
                    
                    # Плавная адаптация к целевому значению
                    current = adapted[param]
                    adapted[param] = (
                        current * (1 - config.adapt_speed) + 
                        target_value * config.adapt_speed
                    )
                    
                    # Ограничение диапазоном
                    adapted[param] = np.clip(
                        adapted[param], 
                        config.min_value, 
                        config.max_value
                    )
                    
        return adapted
    
    def _calculate_performance_adjustment(self, trade_history: List[Dict]) -> Dict:
        """
        Расчет корректировок на основе последних результатов.
        """
        if len(trade_history) < 10:
            return {}
            
        recent_trades = trade_history[-20:]
        
        # Анализ последних сделок
        wins = sum(1 for t in recent_trades if t.get('profit', 0) > 0)
        losses = len(recent_trades) - wins
        win_rate = wins / len(recent_trades) if recent_trades else 0
        
        # Средний профит и лосс
        profits = [t['profit'] for t in recent_trades if t.get('profit', 0) > 0]
        losses_list = [abs(t['profit']) for t in recent_trades if t.get('profit', 0) < 0]
        
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses_list) if losses_list else 0
        
        adjustments = {}
        
        # Корректировка порога входа
        if win_rate < 0.4:
            adjustments['signal_threshold'] = 1.1  # Увеличить на 10%
        elif win_rate > 0.6:
            adjustments['signal_threshold'] = 0.95  # Уменьшить на 5%
            
        # Корректировка стоп-лосса
        if avg_loss > avg_profit * 1.5:
            adjustments['stop_loss_atr_mult'] = 0.9  # Уменьшить стопы
            
        # Корректировка размера позиции
        max_drawdown = self._calculate_max_drawdown(recent_trades)
        if max_drawdown > 0.15:
            adjustments['position_size_pct'] = 0.8  # Уменьшить позицию
            
        return adjustments
    
    def _apply_performance_adjustment(self,
                                     params: Dict[str, float],
                                     adjustments: Dict) -> Dict[str, float]:
        """
        Применение корректировок производительности.
        """
        adjusted = params.copy()
        
        for param, multiplier in adjustments.items():
            if param in adjusted:
                adjusted[param] *= multiplier
                
                # Ограничение диапазоном
                if param in self.parameter_configs:
                    config = self.parameter_configs[param]
                    adjusted[param] = np.clip(
                        adjusted[param],
                        config.min_value,
                        config.max_value
                    )
                    
        return adjusted
    
    def _genetic_optimization(self,
                            price_data: pd.DataFrame,
                            trade_history: List[Dict]) -> OptimizationResult:
        """
        Оптимизация с использованием генетического алгоритма.
        """
        # Определение границ параметров
        bounds = []
        param_names = []
        
        for name, config in self.parameter_configs.items():
            bounds.append((config.min_value, config.max_value))
            param_names.append(name)
            
        # Целевая функция
        def objective(params):
            param_dict = dict(zip(param_names, params))
            
            # Проверка зависимостей
            if not self._check_dependencies(param_dict):
                return -1000  # Штраф за нарушение зависимостей
                
            # Симуляция торговли с параметрами
            score = self._simulate_trading(price_data, param_dict)
            return -score  # Минимизируем негативный score
            
        # Запуск генетического алгоритма
        result = differential_evolution(
            objective,
            bounds,
            maxiter=50,
            popsize=15,
            mutation=(0.5, 1.5),
            recombination=0.7,
            seed=42
        )
        
        # Формирование результата
        optimized_params = dict(zip(param_names, result.x))
        metrics = self._calculate_metrics(trade_history, optimized_params)
        
        return OptimizationResult(
            parameters=optimized_params,
            performance_score=-result.fun,
            sharpe_ratio=metrics['sharpe_ratio'],
            win_rate=metrics['win_rate'],
            profit_factor=metrics['profit_factor'],
            max_drawdown=metrics['max_drawdown'],
            optimization_time=datetime.now(),
            confidence=0.7
        )
    
    def _bayesian_optimization(self,
                              price_data: pd.DataFrame,
                              trade_history: List[Dict]) -> OptimizationResult:
        """
        Байесовская оптимизация параметров.
        """
        # Упрощенная версия байесовской оптимизации
        # В реальности нужно использовать специализированные библиотеки
        
        n_iterations = 30
        best_params = self._get_current_parameters()
        best_score = -float('inf')
        
        # Гауссовский процесс для моделирования
        explored_params = []
        explored_scores = []
        
        for iteration in range(n_iterations):
            # Выбор следующей точки для исследования
            if iteration < 5:
                # Случайное исследование вначале
                candidate_params = self._generate_random_parameters()
            else:
                # Использование acquisition function
                candidate_params = self._acquisition_function(
                    explored_params, explored_scores
                )
                
            # Оценка параметров
            score = self._simulate_trading(price_data, candidate_params)
            
            explored_params.append(candidate_params)
            explored_scores.append(score)
            
            if score > best_score:
                best_score = score
                best_params = candidate_params
                
        # Формирование результата
        metrics = self._calculate_metrics(trade_history, best_params)
        
        return OptimizationResult(
            parameters=best_params,
            performance_score=best_score,
            sharpe_ratio=metrics['sharpe_ratio'],
            win_rate=metrics['win_rate'],
            profit_factor=metrics['profit_factor'],
            max_drawdown=metrics['max_drawdown'],
            optimization_time=datetime.now(),
            confidence=0.75
        )
    
    def _grid_search_optimization(self,
                                 price_data: pd.DataFrame,
                                 trade_history: List[Dict]) -> OptimizationResult:
        """
        Оптимизация методом перебора по сетке.
        """
        # Выбираем ключевые параметры для оптимизации
        key_params = [
            'signal_threshold',
            'stop_loss_atr_mult',
            'take_profit_atr_mult',
            'position_size_pct'
        ]
        
        best_params = self._get_current_parameters()
        best_score = -float('inf')
        
        # Создаем сетку параметров
        for param_name in key_params:
            if param_name not in self.parameter_configs:
                continue
                
            config = self.parameter_configs[param_name]
            
            # Генерируем значения для тестирования
            if config.parameter_type == 'discrete':
                values = np.arange(
                    config.min_value,
                    config.max_value + config.step,
                    config.step
                )
            else:
                values = np.linspace(
                    config.min_value,
                    config.max_value,
                    5  # 5 точек для каждого параметра
                )
                
            for value in values:
                test_params = best_params.copy()
                test_params[param_name] = value
                
                # Проверка зависимостей
                if not self._check_dependencies(test_params):
                    continue
                    
                # Оценка параметров
                score = self._simulate_trading(price_data, test_params)
                
                if score > best_score:
                    best_score = score
                    best_params = test_params.copy()
                    
        # Формирование результата
        metrics = self._calculate_metrics(trade_history, best_params)
        
        return OptimizationResult(
            parameters=best_params,
            performance_score=best_score,
            sharpe_ratio=metrics['sharpe_ratio'],
            win_rate=metrics['win_rate'],
            profit_factor=metrics['profit_factor'],
            max_drawdown=metrics['max_drawdown'],
            optimization_time=datetime.now(),
            confidence=0.65
        )
    
    def _check_dependencies(self, params: Dict[str, float]) -> bool:
        """
        Проверка зависимостей между параметрами.
        """
        # ma_slow должен быть больше ma_fast
        if 'ma_slow_period' in params and 'ma_fast_period' in params:
            if params['ma_slow_period'] <= params['ma_fast_period']:
                return False
                
        # rsi_overbought должен быть больше rsi_oversold
        if 'rsi_overbought' in params and 'rsi_oversold' in params:
            if params['rsi_overbought'] <= params['rsi_oversold']:
                return False
                
        # take_profit должен быть больше stop_loss
        if 'take_profit_atr_mult' in params and 'stop_loss_atr_mult' in params:
            if params['take_profit_atr_mult'] <= params['stop_loss_atr_mult'] * 0.8:
                return False
                
        return True
    
    def _simulate_trading(self, 
                        price_data: pd.DataFrame,
                        params: Dict[str, float]) -> float:
        """
        Симуляция торговли с заданными параметрами.
        """
        # Упрощенная симуляция для демонстрации
        # В реальности здесь должна быть полная стратегия
        
        if len(price_data) < 100:
            return 0.0
            
        # Простая стратегия на пересечении MA
        ma_fast = price_data['close'].rolling(
            int(params.get('ma_fast_period', 20))
        ).mean()
        ma_slow = price_data['close'].rolling(
            int(params.get('ma_slow_period', 50))
        ).mean()
        
        # Сигналы
        signals = pd.DataFrame(index=price_data.index)
        signals['position'] = 0
        signals['position'][ma_fast > ma_slow] = 1
        signals['position'][ma_fast <= ma_slow] = -1
        
        # Расчет доходности
        returns = price_data['close'].pct_change()
        strategy_returns = signals['position'].shift(1) * returns
        
        # Расчет метрик
        sharpe = self._calculate_sharpe_ratio(strategy_returns.dropna())
        total_return = (1 + strategy_returns).prod() - 1
        
        # Комбинированный score
        score = sharpe * 0.5 + total_return * 100 * 0.3 + 0.2
        
        return score
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """
        Расчет коэффициента Шарпа.
        """
        if len(returns) < 2:
            return 0.0
            
        mean_return = returns.mean()
        std_return = returns.std()
        
        if std_return == 0:
            return 0.0
            
        # Годовой Sharpe (предполагаем дневные данные)
        sharpe = np.sqrt(252) * mean_return / std_return
        
        return sharpe
    
    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """
        Расчет максимальной просадки.
        """
        if not trades:
            return 0.0
            
        # Кумулятивная прибыль
        cumulative = []
        total = 0
        
        for trade in trades:
            total += trade.get('profit', 0)
            cumulative.append(total)
            
        # Максимальная просадка
        peak = cumulative[0]
        max_dd = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)
            
        return max_dd
    
    def _walk_forward_validation(self,
                                price_data: pd.DataFrame,
                                params: Dict[str, float],
                                trade_history: List[Dict]) -> float:
        """
        Walk-forward валидация параметров.
        """
        if len(price_data) < self.lookback_window:
            return 0.0
            
        # Разбиваем данные на обучающую и тестовую выборки
        train_size = int(len(price_data) * 0.7)
        
        scores = []
        
        # Скользящее окно
        for i in range(3):  # 3 периода валидации
            start_idx = i * (len(price_data) - train_size) // 3
            end_idx = start_idx + train_size
            
            if end_idx >= len(price_data):
                break
                
            # Обучающая выборка
            train_data = price_data.iloc[start_idx:end_idx]
            
            # Тестовая выборка
            test_start = end_idx
            test_end = min(test_start + (len(price_data) - train_size) // 3, len(price_data))
            test_data = price_data.iloc[test_start:test_end]
            
            # Оценка на тестовой выборке
            score = self._simulate_trading(test_data, params)
            scores.append(score)
            
        return np.mean(scores) if scores else 0.0
    
    def _calculate_metrics(self, 
                         trade_history: List[Dict],
                         params: Dict[str, float]) -> Dict:
        """
        Расчет метрик производительности.
        """
        if not trade_history:
            return {
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0
            }
            
        # Win rate
        wins = sum(1 for t in trade_history if t.get('profit', 0) > 0)
        win_rate = wins / len(trade_history)
        
        # Profit factor
        gross_profit = sum(t['profit'] for t in trade_history if t.get('profit', 0) > 0)
        gross_loss = abs(sum(t['profit'] for t in trade_history if t.get('profit', 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio (упрощенный)
        returns = [t.get('profit', 0) for t in trade_history]
        sharpe = self._calculate_sharpe_ratio(pd.Series(returns))
        
        # Max drawdown
        max_dd = self._calculate_max_drawdown(trade_history)
        
        return {
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd
        }
    
    def _calculate_confidence(self, score: float, num_trades: int) -> float:
        """
        Расчет уверенности в результатах оптимизации.
        """
        # Базовая уверенность на основе score
        base_confidence = min(1.0, score / 2)  # Нормализация score
        
        # Корректировка на количество сделок
        trade_confidence = min(1.0, num_trades / 100)
        
        # Комбинированная уверенность
        confidence = base_confidence * 0.7 + trade_confidence * 0.3
        
        return min(1.0, max(0.0, confidence))
    
    def _generate_random_parameters(self) -> Dict[str, float]:
        """
        Генерация случайных параметров в допустимых диапазонах.
        """
        params = {}
        
        for name, config in self.parameter_configs.items():
            if config.parameter_type == 'boolean':
                params[name] = np.random.choice([0, 1])
            elif config.parameter_type == 'discrete':
                steps = int((config.max_value - config.min_value) / config.step)
                value = config.min_value + np.random.randint(0, steps + 1) * config.step
                params[name] = value
            else:
                params[name] = np.random.uniform(config.min_value, config.max_value)
                
        return params
    
    def _acquisition_function(self,
                            explored_params: List[Dict],
                            explored_scores: List[float]) -> Dict[str, float]:
        """
        Acquisition function для байесовской оптимизации.
        """
        # Упрощенная версия UCB (Upper Confidence Bound)
        
        if not explored_params:
            return self._generate_random_parameters()
            
        # Находим параметры с лучшим UCB
        best_params = explored_params[np.argmax(explored_scores)].copy()
        
        # Добавляем исследование (exploration)
        for param_name in best_params:
            if param_name in self.parameter_configs:
                config = self.parameter_configs[param_name]
                # Добавляем шум для исследования
                noise = np.random.normal(0, config.step * 0.5)
                best_params[param_name] += noise
                best_params[param_name] = np.clip(
                    best_params[param_name],
                    config.min_value,
                    config.max_value
                )
                
        return best_params
    
    def _validate_optimization_result(self,
                                     result: OptimizationResult,
                                     trade_history: List[Dict]) -> OptimizationResult:
        """
        Валидация результатов оптимизации.
        """
        # Проверка на экстремальные значения
        for param_name, value in result.parameters.items():
            if param_name in self.parameter_configs:
                config = self.parameter_configs[param_name]
                
                # Корректировка экстремальных значений
                if value == config.min_value or value == config.max_value:
                    # Сдвигаем от границы
                    if value == config.min_value:
                        result.parameters[param_name] = value + config.step
                    else:
                        result.parameters[param_name] = value - config.step
                        
        # Проверка разумности метрик
        if result.sharpe_ratio > 5:  # Подозрительно высокий Sharpe
            result.confidence *= 0.5
            
        if result.win_rate > 0.8:  # Подозрительно высокий win rate
            result.confidence *= 0.7
            
        return result
    
    def _update_parameters(self, result: OptimizationResult):
        """
        Обновление текущих параметров.
        """
        # Плавное обновление с учетом уверенности
        for param_name, new_value in result.parameters.items():
            if param_name in self.current_parameters:
                old_value = self.current_parameters[param_name]
                # Взвешенное среднее на основе уверенности
                self.current_parameters[param_name] = (
                    old_value * (1 - result.confidence * 0.5) +
                    new_value * result.confidence * 0.5
                )
            else:
                self.current_parameters[param_name] = new_value
                
        # Обновление конфигураций
        for param_name, value in self.current_parameters.items():
            if param_name in self.parameter_configs:
                self.parameter_configs[param_name].current_value = value
    
    def _get_current_parameters(self) -> Dict[str, float]:
        """
        Получение текущих параметров.
        """
        if not self.current_parameters:
            # Инициализация из конфигураций
            self.current_parameters = {
                name: config.current_value
                for name, config in self.parameter_configs.items()
            }
        return self.current_parameters.copy()
    
    def _get_current_optimization_result(self) -> OptimizationResult:
        """
        Получение текущего результата оптимизации.
        """
        if self.optimization_history:
            return self.optimization_history[-1]
            
        # Возвращаем дефолтный результат
        return OptimizationResult(
            parameters=self._get_current_parameters(),
            performance_score=0.0,
            sharpe_ratio=0.0,
            win_rate=0.5,
            profit_factor=1.0,
            max_drawdown=0.0,
            optimization_time=datetime.now(),
            confidence=0.5
        )
    
    def get_parameter_importance(self) -> Dict[str, float]:
        """
        Оценка важности каждого параметра.
        """
        if len(self.optimization_history) < 10:
            # Возвращаем веса по умолчанию
            return {
                name: config.optimization_weight
                for name, config in self.parameter_configs.items()
            }
            
        # Анализ влияния параметров на результаты
        importance = {}
        
        for param_name in self.parameter_configs:
            values = []
            scores = []
            
            for result in self.optimization_history[-50:]:
                if param_name in result.parameters:
                    values.append(result.parameters[param_name])
                    scores.append(result.performance_score)
                    
            if len(values) > 5:
                # Корреляция между значением параметра и score
                correlation = np.corrcoef(values, scores)[0, 1]
                importance[param_name] = abs(correlation)
            else:
                importance[param_name] = 0.5
                
        return importance
    
    def export_parameters(self, filepath: str):
        """
        Экспорт текущих параметров в файл.
        """
        export_data = {
            'parameters': self.current_parameters,
            'last_optimization': (
                self.optimization_history[-1].__dict__
                if self.optimization_history else None
            ),
            'parameter_configs': {
                name: {
                    'current_value': config.current_value,
                    'min_value': config.min_value,
                    'max_value': config.max_value,
                    'description': config.description
                }
                for name, config in self.parameter_configs.items()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def import_parameters(self, filepath: str):
        """
        Импорт параметров из файла.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        if 'parameters' in data:
            self.current_parameters = data['parameters']
            
        if 'parameter_configs' in data:
            for name, config_data in data['parameter_configs'].items():
                if name in self.parameter_configs:
                    self.parameter_configs[name].current_value = config_data['current_value']