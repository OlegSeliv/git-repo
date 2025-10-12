"""
Главный файл системы оптимизации торгового робота
Объединяет все компоненты для устранения влияния изменений рынка и оптимизации времени запуска
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
import warnings
warnings.filterwarnings('ignore')

# Импортируем все созданные модули
from market_adaptation_system import MarketAdaptationSystem, MarketConditions
from timing_optimization_system import TimingOptimizer, TimeAnalysis
from advanced_risk_management import AdvancedRiskManager, RiskLevel
from backtesting_framework import BacktestEngine, MovingAverageCrossoverStrategy
from realtime_monitoring_system import RealtimeMonitor, AlertLevel

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OptimizedTradingRobot:
    """Оптимизированный торговый робот с адаптацией к рынку и оптимизацией времени"""
    
    def __init__(self, initial_balance: float = 10000):
        # Инициализируем все системы
        self.market_adaptation = MarketAdaptationSystem()
        self.timing_optimizer = TimingOptimizer()
        self.risk_manager = AdvancedRiskManager(initial_balance)
        self.monitor = RealtimeMonitor(initial_balance)
        
        # Состояние робота
        self.is_running = False
        self.current_positions = {}
        self.trading_schedule = None
        self.optimal_timing = None
        
        # Статистика
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        logger.info("Оптимизированный торговый робот инициализирован")
    
    def analyze_market_and_timing(self, historical_data: pd.DataFrame) -> Dict:
        """Анализирует рынок и определяет оптимальное время торговли"""
        logger.info("Начинаем анализ рынка и времени торговли...")
        
        # Анализ условий рынка
        prices = historical_data['close'].tolist()
        volume = historical_data.get('volume', [1000] * len(prices)).tolist()
        
        market_conditions = self.market_adaptation.analyze_market_conditions(prices, volume)
        
        # Анализ оптимального времени
        timing_analysis = self.timing_optimizer.optimize_timing(historical_data)
        
        # Создаем расписание торговли
        trading_schedule = self.timing_optimizer.get_trading_schedule(timing_analysis)
        
        # Сохраняем результаты
        self.optimal_timing = timing_analysis
        self.trading_schedule = trading_schedule
        
        analysis_results = {
            'market_conditions': {
                'regime': market_conditions.regime.value,
                'volatility': market_conditions.volatility,
                'trend_strength': market_conditions.trend_strength,
                'should_trade': self.market_adaptation.should_trade()
            },
            'timing_analysis': {
                'best_hour': timing_analysis.best_hour,
                'best_session': timing_analysis.best_session.value,
                'expected_return': timing_analysis.expected_return,
                'confidence_score': timing_analysis.confidence_score
            },
            'trading_schedule': trading_schedule,
            'recommendations': self.timing_optimizer.get_recommendations(timing_analysis)
        }
        
        logger.info("Анализ завершен")
        return analysis_results
    
    def optimize_strategy_parameters(self, historical_data: pd.DataFrame, 
                                   strategy_class, parameter_ranges: Dict) -> Dict:
        """Оптимизирует параметры торговой стратегии"""
        logger.info("Начинаем оптимизацию параметров стратегии...")
        
        from backtesting_framework import ParameterOptimizer
        
        optimizer = ParameterOptimizer(strategy_class, parameter_ranges)
        results = optimizer.optimize(historical_data, max_combinations=100)
        
        best_parameters = optimizer.get_best_parameters(5)
        
        optimization_results = {
            'best_parameters': best_parameters,
            'total_combinations_tested': len(results),
            'optimization_metric': 'sharpe_ratio'
        }
        
        logger.info(f"Оптимизация завершена. Протестировано {len(results)} комбинаций")
        return optimization_results
    
    def start_trading(self, real_time_data_callback, update_interval: int = 60):
        """Запускает торговлю в реальном времени"""
        if self.is_running:
            logger.warning("Торговля уже запущена")
            return
        
        if not self.optimal_timing or not self.trading_schedule:
            logger.error("Необходимо сначала провести анализ рынка и времени")
            return
        
        self.is_running = True
        self.monitor.start_monitoring(update_interval)
        
        logger.info("Торговля запущена")
        
        # Основной торговый цикл
        try:
            while self.is_running:
                current_time = datetime.now()
                current_hour = current_time.hour
                
                # Проверяем, подходящее ли время для торговли
                if self._should_trade_now(current_hour):
                    # Получаем текущие данные рынка
                    market_data = real_time_data_callback()
                    
                    if market_data:
                        # Анализируем текущие условия рынка
                        self._analyze_current_market(market_data)
                        
                        # Принимаем торговые решения
                        self._make_trading_decisions(market_data)
                
                # Обновляем существующие позиции
                self._update_positions()
                
                # Проверяем алерты и риски
                self._check_risk_conditions()
                
                # Небольшая пауза
                import time
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Ошибка в торговом цикле: {e}")
        finally:
            self.stop_trading()
    
    def stop_trading(self):
        """Останавливает торговлю"""
        self.is_running = False
        self.monitor.stop_monitoring()
        
        # Закрываем все позиции
        for position_id in list(self.current_positions.keys()):
            self._close_position(position_id, "Robot stopped")
        
        logger.info("Торговля остановлена")
    
    def _should_trade_now(self, current_hour: int) -> bool:
        """Определяет, подходящее ли время для торговли"""
        if not self.trading_schedule:
            return False
        
        # Проверяем основные часы торговли
        if current_hour in self.trading_schedule['primary_hours']:
            return True
        
        # Проверяем дополнительные часы
        if current_hour in self.trading_schedule['secondary_hours']:
            return True
        
        # Избегаем неблагоприятных часов
        if current_hour in self.trading_schedule['avoid_hours']:
            return False
        
        return False
    
    def _analyze_current_market(self, market_data: Dict):
        """Анализирует текущие условия рынка"""
        try:
            # Извлекаем данные
            prices = market_data.get('prices', [])
            volume = market_data.get('volume', [])
            
            if len(prices) < 20:  # Недостаточно данных
                return
            
            # Анализируем условия рынка
            conditions = self.market_adaptation.analyze_market_conditions(prices, volume)
            
            # Обновляем параметры риска
            adaptive_params = self.market_adaptation.get_adaptive_parameters()
            
            # Логируем изменения
            logger.info(f"Режим рынка: {conditions.regime.value}, "
                       f"Волатильность: {conditions.volatility:.3f}")
            
        except Exception as e:
            logger.error(f"Ошибка анализа рынка: {e}")
    
    def _make_trading_decisions(self, market_data: Dict):
        """Принимает торговые решения"""
        try:
            current_price = market_data.get('current_price', 0)
            symbol = market_data.get('symbol', 'EURUSD')
            
            if current_price <= 0:
                return
            
            # Проверяем, можно ли открыть новую позицию
            if not self.risk_manager.can_open_position(symbol):
                return
            
            # Упрощенная логика входа (в реальности здесь будет сложная стратегия)
            should_enter, direction = self._evaluate_entry_signal(market_data)
            
            if should_enter:
                self._open_position(symbol, current_price, direction, market_data)
            
        except Exception as e:
            logger.error(f"Ошибка принятия торговых решений: {e}")
    
    def _evaluate_entry_signal(self, market_data: Dict) -> tuple:
        """Оценивает сигнал входа (упрощенная версия)"""
        # Здесь должна быть сложная логика анализа сигналов
        # Для демонстрации используем случайную логику
        import random
        
        # Простая логика на основе волатильности
        volatility = market_data.get('volatility', 0.1)
        trend = market_data.get('trend', 0)
        
        # Входим с вероятностью 20% при низкой волатильности
        if volatility < 0.15 and random.random() < 0.2:
            direction = 'long' if trend > 0 else 'short'
            return True, direction
        
        return False, None
    
    def _open_position(self, symbol: str, price: float, direction: str, market_data: Dict):
        """Открывает новую позицию"""
        try:
            # Вычисляем размер позиции
            stop_loss = price * (0.98 if direction == 'long' else 1.02)
            volatility = market_data.get('volatility', 0.1)
            
            position_size = self.risk_manager.calculate_position_size(
                symbol, price, stop_loss, volatility
            )
            
            if position_size <= 0:
                return
            
            # Создаем позицию
            position_id = f"pos_{len(self.current_positions)}_{int(datetime.now().timestamp())}"
            
            position = {
                'id': position_id,
                'symbol': symbol,
                'direction': direction,
                'size': position_size,
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': price * (1.02 if direction == 'long' else 0.98),
                'entry_time': datetime.now(),
                'unrealized_pnl': 0.0
            }
            
            self.current_positions[position_id] = position
            
            # Обновляем статистику
            self.total_trades += 1
            
            logger.info(f"Открыта позиция {position_id}: {direction} {symbol} "
                       f"размер {position_size:.2f} по цене {price:.4f}")
            
        except Exception as e:
            logger.error(f"Ошибка открытия позиции: {e}")
    
    def _update_positions(self):
        """Обновляет существующие позиции"""
        for position_id, position in list(self.current_positions.items()):
            try:
                # Получаем текущую цену (в реальности из API)
                current_price = self._get_current_price(position['symbol'])
                
                if current_price <= 0:
                    continue
                
                # Обновляем P&L
                if position['direction'] == 'long':
                    position['unrealized_pnl'] = (current_price - position['entry_price']) * position['size']
                else:
                    position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['size']
                
                # Проверяем условия выхода
                should_close, reason = self.risk_manager.should_close_position(position_id)
                
                if should_close:
                    self._close_position(position_id, reason)
                else:
                    # Обновляем стоп-лосс (трейлинг)
                    self.risk_manager.update_position(position_id, current_price, 0.01)
                
            except Exception as e:
                logger.error(f"Ошибка обновления позиции {position_id}: {e}")
    
    def _close_position(self, position_id: str, reason: str):
        """Закрывает позицию"""
        if position_id not in self.current_positions:
            return
        
        position = self.current_positions[position_id]
        
        # Получаем цену закрытия
        exit_price = self._get_current_price(position['symbol'])
        
        if exit_price <= 0:
            return
        
        # Вычисляем P&L
        if position['direction'] == 'long':
            pnl = (exit_price - position['entry_price']) * position['size']
        else:
            pnl = (position['entry_price'] - exit_price) * position['size']
        
        # Обновляем статистику
        self.total_pnl += pnl
        if pnl > 0:
            self.winning_trades += 1
        
        # Обновляем трекер производительности
        trade_duration = (datetime.now() - position['entry_time']).total_seconds() / 3600
        self.monitor.performance_tracker.add_trade(pnl, trade_duration)
        
        # Удаляем позицию
        del self.current_positions[position_id]
        
        logger.info(f"Закрыта позиция {position_id}: P&L {pnl:.2f}, причина: {reason}")
    
    def _get_current_price(self, symbol: str) -> float:
        """Получает текущую цену (заглушка)"""
        # В реальности здесь будет запрос к API брокера
        import random
        return 1.2000 + random.uniform(-0.01, 0.01)
    
    def _check_risk_conditions(self):
        """Проверяет условия риска"""
        try:
            # Проверяем, нужно ли снизить риски
            if self.risk_manager.portfolio_manager.should_reduce_risk():
                logger.warning("Обнаружены условия для снижения рисков")
                
                # Закрываем часть позиций
                if len(self.current_positions) > 1:
                    position_to_close = list(self.current_positions.keys())[0]
                    self._close_position(position_to_close, "Risk reduction")
            
        except Exception as e:
            logger.error(f"Ошибка проверки рисков: {e}")
    
    def get_performance_summary(self) -> Dict:
        """Получает сводку производительности"""
        metrics = self.monitor.performance_tracker.get_performance_metrics()
        
        return {
            'trading_summary': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
                'total_pnl': self.total_pnl,
                'active_positions': len(self.current_positions)
            },
            'performance_metrics': {
                'current_balance': metrics.current_balance,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown,
                'profit_factor': metrics.profit_factor
            },
            'market_adaptation': {
                'current_regime': self.market_adaptation.current_conditions.regime.value if self.market_adaptation.current_conditions else "Unknown",
                'should_trade': self.market_adaptation.should_trade() if self.market_adaptation.current_conditions else False
            },
            'timing_optimization': {
                'optimal_hour': self.optimal_timing.best_hour if self.optimal_timing else None,
                'confidence_score': self.optimal_timing.confidence_score if self.optimal_timing else 0
            }
        }

def create_sample_data(days: int = 30) -> pd.DataFrame:
    """Создает пример исторических данных"""
    np.random.seed(42)
    
    # Создаем данные по часам для каждого дня
    total_hours = days * 24
    dates = pd.date_range(start='2024-01-01', periods=total_hours, freq='H')
    base_price = 1.2000
    prices = [base_price]
    
    for i in range(1, len(dates)):
        # Симулируем ценовое движение
        change = np.random.normal(0, 0.001)
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.0005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.0005))) for p in prices],
        'volume': [1000 + np.random.normal(0, 100) for _ in range(len(dates))]
    })
    
    return data

def main():
    """Главная функция демонстрации"""
    print("=== СИСТЕМА ОПТИМИЗАЦИИ ТОРГОВОГО РОБОТА ===\n")
    
    # Создаем торгового робота
    robot = OptimizedTradingRobot(initial_balance=10000)
    
    # Создаем пример данных
    print("Создаем пример исторических данных...")
    historical_data = create_sample_data(days=720)  # 30 дней по 24 часа
    print(f"Создано {len(historical_data)} записей данных\n")
    
    # Анализируем рынок и время
    print("1. АНАЛИЗ РЫНКА И ОПТИМИЗАЦИЯ ВРЕМЕНИ")
    print("-" * 50)
    analysis_results = robot.analyze_market_and_timing(historical_data)
    
    print(f"Режим рынка: {analysis_results['market_conditions']['regime']}")
    print(f"Волатильность: {analysis_results['market_conditions']['volatility']:.3f}")
    print(f"Стоит ли торговать: {analysis_results['market_conditions']['should_trade']}")
    print(f"Оптимальный час: {analysis_results['timing_analysis']['best_hour']}:00 UTC")
    print(f"Лучшая сессия: {analysis_results['timing_analysis']['best_session']}")
    print(f"Уверенность: {analysis_results['timing_analysis']['confidence_score']:.1%}")
    
    print("\nРекомендации:")
    for rec in analysis_results['recommendations']:
        print(f"  - {rec}")
    
    # Оптимизируем параметры стратегии
    print("\n\n2. ОПТИМИЗАЦИЯ ПАРАМЕТРОВ СТРАТЕГИИ")
    print("-" * 50)
    
    parameter_ranges = {
        'fast_period': [5, 10, 15],
        'slow_period': [20, 30, 40],
        'stop_loss_pct': [0.01, 0.02, 0.03]
    }
    
    optimization_results = robot.optimize_strategy_parameters(
        historical_data, MovingAverageCrossoverStrategy, parameter_ranges
    )
    
    print(f"Протестировано комбинаций: {optimization_results['total_combinations_tested']}")
    print("Лучшие параметры:")
    for i, params in enumerate(optimization_results['best_parameters'][:3]):
        print(f"  {i+1}. {params['parameters']} - Sharpe: {params['metric_value']:.2f}")
    
    # Демонстрируем мониторинг
    print("\n\n3. СИСТЕМА МОНИТОРИНГА")
    print("-" * 50)
    
    # Запускаем мониторинг
    robot.monitor.start_monitoring(update_interval=5)
    
    # Симулируем торговую активность
    print("Симулируем торговую активность...")
    import random
    import time
    
    for i in range(10):
        # Симулируем сделку
        trade_pnl = random.uniform(-50, 100)
        robot.monitor.performance_tracker.add_trade(trade_pnl, random.uniform(0.5, 2.0))
        
        # Обновляем баланс
        new_balance = robot.monitor.performance_tracker.current_balance
        robot.monitor.performance_tracker.update_balance(new_balance)
        
        # Получаем данные дашборда
        dashboard_data = robot.monitor.get_dashboard_data()
        
        print(f"\nОбновление {i+1}:")
        print(f"  Баланс: ${dashboard_data['performance']['current_balance']:.2f}")
        print(f"  Общий P&L: ${dashboard_data['performance']['total_pnl']:.2f}")
        print(f"  Коэффициент Шарпа: {dashboard_data['performance']['sharpe_ratio']:.2f}")
        print(f"  Активных алертов: {len(dashboard_data['alerts'])}")
        
        if dashboard_data['alerts']:
            for alert in dashboard_data['alerts']:
                print(f"    ⚠️  {alert['level'].upper()}: {alert['message']}")
        
        time.sleep(1)
    
    # Останавливаем мониторинг
    robot.monitor.stop_monitoring()
    
    # Получаем итоговую сводку
    print("\n\n4. ИТОГОВАЯ СВОДКА ПРОИЗВОДИТЕЛЬНОСТИ")
    print("-" * 50)
    
    summary = robot.get_performance_summary()
    
    print("Торговая статистика:")
    print(f"  Всего сделок: {summary['trading_summary']['total_trades']}")
    print(f"  Выигрышных: {summary['trading_summary']['winning_trades']}")
    print(f"  Процент выигрышных: {summary['trading_summary']['win_rate']:.1%}")
    print(f"  Общий P&L: ${summary['trading_summary']['total_pnl']:.2f}")
    
    print("\nМетрики производительности:")
    print(f"  Текущий баланс: ${summary['performance_metrics']['current_balance']:.2f}")
    print(f"  Коэффициент Шарпа: {summary['performance_metrics']['sharpe_ratio']:.2f}")
    print(f"  Максимальная просадка: {summary['performance_metrics']['max_drawdown']:.1%}")
    print(f"  Profit Factor: {summary['performance_metrics']['profit_factor']:.2f}")
    
    print("\nАдаптация к рынку:")
    print(f"  Текущий режим: {summary['market_adaptation']['current_regime']}")
    print(f"  Рекомендуется торговать: {summary['market_adaptation']['should_trade']}")
    
    print("\nОптимизация времени:")
    print(f"  Оптимальный час: {summary['timing_optimization']['optimal_hour']}:00 UTC")
    print(f"  Уверенность: {summary['timing_optimization']['confidence_score']:.1%}")
    
    # Экспортируем метрики
    filename = robot.monitor.export_metrics()
    print(f"\nМетрики экспортированы в файл: {filename}")
    
    print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")

if __name__ == "__main__":
    main()