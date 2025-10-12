"""
Система мониторинга производительности торгового робота в реальном времени
Включает отслеживание метрик, алерты, дашборд и автоматические корректировки
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import threading
import time
import json
from enum import Enum
import warnings
from collections import deque
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Уровни алертов"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Типы метрик"""
    PERFORMANCE = "performance"
    RISK = "risk"
    MARKET = "market"
    SYSTEM = "system"

@dataclass
class Alert:
    """Алерт системы"""
    id: str
    timestamp: datetime
    level: AlertLevel
    metric_type: MetricType
    message: str
    value: float
    threshold: float
    acknowledged: bool = False

@dataclass
class MetricSnapshot:
    """Снимок метрики"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    current_balance: float
    total_pnl: float
    daily_pnl: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    active_trades: int
    total_trades: int
    avg_trade_duration: float
    last_trade_pnl: float

class MetricCollector:
    """Сборщик метрик"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = {}
        self.lock = threading.Lock()
    
    def add_metric(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """Добавляет метрику"""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = deque(maxlen=self.max_history)
            
            snapshot = MetricSnapshot(
                timestamp=datetime.now(),
                value=value,
                metadata=metadata or {}
            )
            
            self.metrics[name].append(snapshot)
    
    def get_metric_history(self, name: str, minutes: int = 60) -> List[MetricSnapshot]:
        """Получает историю метрики за указанное время"""
        with self.lock:
            if name not in self.metrics:
                return []
            
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            return [m for m in self.metrics[name] if m.timestamp >= cutoff_time]
    
    def get_current_value(self, name: str) -> Optional[float]:
        """Получает текущее значение метрики"""
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return None
            
            return self.metrics[name][-1].value
    
    def get_metric_stats(self, name: str, minutes: int = 60) -> Dict[str, float]:
        """Получает статистику метрики"""
        history = self.get_metric_history(name, minutes)
        
        if not history:
            return {}
        
        values = [m.value for m in history]
        
        return {
            'current': values[-1],
            'min': min(values),
            'max': max(values),
            'avg': np.mean(values),
            'std': np.std(values),
            'count': len(values)
        }

class AlertManager:
    """Менеджер алертов"""
    
    def __init__(self):
        self.alerts = []
        self.alert_rules = {}
        self.alert_handlers = {}
        self.lock = threading.Lock()
    
    def add_alert_rule(self, metric_name: str, condition: str, threshold: float, 
                      level: AlertLevel, message_template: str):
        """Добавляет правило алерта"""
        rule_id = f"{metric_name}_{condition}_{threshold}"
        
        self.alert_rules[rule_id] = {
            'metric_name': metric_name,
            'condition': condition,
            'threshold': threshold,
            'level': level,
            'message_template': message_template
        }
    
    def check_alerts(self, metric_collector: MetricCollector):
        """Проверяет все правила алертов"""
        with self.lock:
            for rule_id, rule in self.alert_rules.items():
                current_value = metric_collector.get_current_value(rule['metric_name'])
                
                if current_value is None:
                    continue
                
                should_alert = self._evaluate_condition(
                    current_value, rule['condition'], rule['threshold']
                )
                
                if should_alert:
                    # Проверяем, не было ли уже такого алерта недавно
                    if not self._recent_alert_exists(rule_id, minutes=5):
                        self._create_alert(rule, current_value)
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Вычисляет условие алерта"""
        if condition == 'greater_than':
            return value > threshold
        elif condition == 'less_than':
            return value < threshold
        elif condition == 'equals':
            return abs(value - threshold) < 1e-6
        elif condition == 'greater_equal':
            return value >= threshold
        elif condition == 'less_equal':
            return value <= threshold
        else:
            return False
    
    def _recent_alert_exists(self, rule_id: str, minutes: int = 5) -> bool:
        """Проверяет, был ли недавно алерт по этому правилу"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        for alert in self.alerts:
            if (alert.metric_type.value == rule_id and 
                alert.timestamp >= cutoff_time and 
                not alert.acknowledged):
                return True
        
        return False
    
    def _create_alert(self, rule: Dict, value: float):
        """Создает новый алерт"""
        alert = Alert(
            id=f"alert_{len(self.alerts)}_{int(time.time())}",
            timestamp=datetime.now(),
            level=rule['level'],
            metric_type=MetricType.PERFORMANCE,  # Упрощенно
            message=rule['message_template'].format(value=value, threshold=rule['threshold']),
            value=value,
            threshold=rule['threshold']
        )
        
        self.alerts.append(alert)
        
        # Вызываем обработчик алерта
        if rule['level'] in self.alert_handlers:
            self.alert_handlers[rule['level']](alert)
        
        logger.warning(f"ALERT: {alert.message}")
    
    def add_alert_handler(self, level: AlertLevel, handler: Callable[[Alert], None]):
        """Добавляет обработчик алертов"""
        self.alert_handlers[level] = handler
    
    def get_active_alerts(self) -> List[Alert]:
        """Получает активные (не подтвержденные) алерты"""
        with self.lock:
            return [a for a in self.alerts if not a.acknowledged]
    
    def acknowledge_alert(self, alert_id: str):
        """Подтверждает алерт"""
        with self.lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    break

class PerformanceTracker:
    """Трекер производительности"""
    
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.trades = []
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.lock = threading.Lock()
    
    def update_balance(self, new_balance: float):
        """Обновляет баланс"""
        with self.lock:
            self.current_balance = new_balance
            
            if new_balance > self.peak_balance:
                self.peak_balance = new_balance
    
    def add_trade(self, trade_pnl: float, trade_duration: float = 0):
        """Добавляет сделку"""
        with self.lock:
            self.trades.append({
                'pnl': trade_pnl,
                'duration': trade_duration,
                'timestamp': datetime.now()
            })
            
            self.current_balance += trade_pnl
            self.daily_pnl += trade_pnl
    
    def reset_daily_metrics(self):
        """Сбрасывает дневные метрики"""
        with self.lock:
            current_date = datetime.now().date()
            if current_date != self.last_reset_date:
                self.daily_pnl = 0.0
                self.last_reset_date = current_date
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Получает метрики производительности"""
        with self.lock:
            # Базовые метрики
            total_pnl = self.current_balance - self.initial_balance
            max_drawdown = self._calculate_max_drawdown()
            current_drawdown = self._calculate_current_drawdown()
            
            # Метрики сделок
            if self.trades:
                winning_trades = [t for t in self.trades if t['pnl'] > 0]
                losing_trades = [t for t in self.trades if t['pnl'] < 0]
                
                win_rate = len(winning_trades) / len(self.trades)
                
                gross_profit = sum(t['pnl'] for t in winning_trades)
                gross_loss = abs(sum(t['pnl'] for t in losing_trades))
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                
                # Sharpe ratio (упрощенный)
                returns = [t['pnl'] / self.initial_balance for t in self.trades]
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0
                
                avg_trade_duration = np.mean([t['duration'] for t in self.trades if t['duration'] > 0])
                last_trade_pnl = self.trades[-1]['pnl'] if self.trades else 0
            else:
                win_rate = 0.0
                profit_factor = 0.0
                sharpe_ratio = 0.0
                avg_trade_duration = 0.0
                last_trade_pnl = 0.0
            
            return PerformanceMetrics(
                current_balance=self.current_balance,
                total_pnl=total_pnl,
                daily_pnl=self.daily_pnl,
                win_rate=win_rate,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                active_trades=0,  # Упрощенно
                total_trades=len(self.trades),
                avg_trade_duration=avg_trade_duration,
                last_trade_pnl=last_trade_pnl
            )
    
    def _calculate_max_drawdown(self) -> float:
        """Вычисляет максимальную просадку"""
        if not self.trades:
            return 0.0
        
        balance_history = [self.initial_balance]
        for trade in self.trades:
            balance_history.append(balance_history[-1] + trade['pnl'])
        
        peak = balance_history[0]
        max_dd = 0.0
        
        for balance in balance_history:
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_current_drawdown(self) -> float:
        """Вычисляет текущую просадку"""
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
            return 0.0
        
        return (self.peak_balance - self.current_balance) / self.peak_balance

class RealtimeMonitor:
    """Основной класс мониторинга в реальном времени"""
    
    def __init__(self, initial_balance: float = 10000):
        self.metric_collector = MetricCollector()
        self.alert_manager = AlertManager()
        self.performance_tracker = PerformanceTracker(initial_balance)
        self.is_running = False
        self.monitor_thread = None
        
        # Настраиваем алерты по умолчанию
        self._setup_default_alerts()
    
    def start_monitoring(self, update_interval: int = 60):
        """Запускает мониторинг"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(update_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info("Мониторинг запущен")
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        logger.info("Мониторинг остановлен")
    
    def _monitoring_loop(self, update_interval: int):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                # Обновляем метрики
                self._update_metrics()
                
                # Проверяем алерты
                self.alert_manager.check_alerts(self.metric_collector)
                
                # Сбрасываем дневные метрики
                self.performance_tracker.reset_daily_metrics()
                
                time.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(update_interval)
    
    def _update_metrics(self):
        """Обновляет все метрики"""
        metrics = self.performance_tracker.get_performance_metrics()
        
        # Основные метрики производительности
        self.metric_collector.add_metric('balance', metrics.current_balance)
        self.metric_collector.add_metric('total_pnl', metrics.total_pnl)
        self.metric_collector.add_metric('daily_pnl', metrics.daily_pnl)
        self.metric_collector.add_metric('win_rate', metrics.win_rate)
        self.metric_collector.add_metric('sharpe_ratio', metrics.sharpe_ratio)
        self.metric_collector.add_metric('max_drawdown', metrics.max_drawdown)
        self.metric_collector.add_metric('current_drawdown', metrics.current_drawdown)
        self.metric_collector.add_metric('profit_factor', metrics.profit_factor)
        self.metric_collector.add_metric('active_trades', metrics.active_trades)
        
        # Дополнительные метрики
        self.metric_collector.add_metric('uptime', self._get_uptime())
        self.metric_collector.add_metric('memory_usage', self._get_memory_usage())
    
    def _setup_default_alerts(self):
        """Настраивает алерты по умолчанию"""
        # Алерты по просадке
        self.alert_manager.add_alert_rule(
            'current_drawdown', 'greater_than', 0.05, AlertLevel.WARNING,
            "Текущая просадка {value:.1%} превышает 5%"
        )
        
        self.alert_manager.add_alert_rule(
            'current_drawdown', 'greater_than', 0.10, AlertLevel.CRITICAL,
            "КРИТИЧЕСКАЯ просадка {value:.1%} превышает 10%"
        )
        
        # Алерты по дневным убыткам
        self.alert_manager.add_alert_rule(
            'daily_pnl', 'less_than', -500, AlertLevel.WARNING,
            "Дневной убыток {value:.2f} превышает $500"
        )
        
        # Алерты по коэффициенту Шарпа
        self.alert_manager.add_alert_rule(
            'sharpe_ratio', 'less_than', 0.5, AlertLevel.WARNING,
            "Коэффициент Шарпа {value:.2f} ниже 0.5"
        )
        
        # Алерты по количеству активных сделок
        self.alert_manager.add_alert_rule(
            'active_trades', 'greater_than', 10, AlertLevel.WARNING,
            "Слишком много активных сделок: {value}"
        )
    
    def _get_uptime(self) -> float:
        """Получает время работы системы"""
        # Упрощенно - возвращаем время с запуска
        return time.time() - getattr(self, '_start_time', time.time())
    
    def _get_memory_usage(self) -> float:
        """Получает использование памяти"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Получает данные для дашборда"""
        metrics = self.performance_tracker.get_performance_metrics()
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Получаем историю ключевых метрик
        balance_history = self.metric_collector.get_metric_history('balance', 24*60)  # 24 часа
        pnl_history = self.metric_collector.get_metric_history('total_pnl', 24*60)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'performance': {
                'current_balance': metrics.current_balance,
                'total_pnl': metrics.total_pnl,
                'daily_pnl': metrics.daily_pnl,
                'win_rate': metrics.win_rate,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown,
                'current_drawdown': metrics.current_drawdown,
                'profit_factor': metrics.profit_factor,
                'active_trades': metrics.active_trades,
                'total_trades': metrics.total_trades
            },
            'alerts': [
                {
                    'id': alert.id,
                    'level': alert.level.value,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'acknowledged': alert.acknowledged
                }
                for alert in active_alerts
            ],
            'charts': {
                'balance': [{'timestamp': m.timestamp.isoformat(), 'value': m.value} for m in balance_history],
                'pnl': [{'timestamp': m.timestamp.isoformat(), 'value': m.value} for m in pnl_history]
            },
            'system': {
                'uptime': self._get_uptime(),
                'memory_usage': self._get_memory_usage(),
                'is_running': self.is_running
            }
        }
    
    def export_metrics(self, filename: str = None) -> str:
        """Экспортирует метрики в JSON"""
        if filename is None:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = self.get_dashboard_data()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def add_custom_alert(self, metric_name: str, condition: str, threshold: float, 
                        level: AlertLevel, message: str):
        """Добавляет пользовательский алерт"""
        self.alert_manager.add_alert_rule(metric_name, condition, threshold, level, message)
    
    def acknowledge_alert(self, alert_id: str):
        """Подтверждает алерт"""
        self.alert_manager.acknowledge_alert(alert_id)

# Пример использования
if __name__ == "__main__":
    # Создаем монитор
    monitor = RealtimeMonitor(initial_balance=10000)
    
    # Запускаем мониторинг
    monitor.start_monitoring(update_interval=10)  # Обновление каждые 10 секунд
    
    # Симулируем торговую активность
    import random
    
    try:
        for i in range(20):
            # Симулируем сделку
            trade_pnl = random.uniform(-100, 200)
            monitor.performance_tracker.add_trade(trade_pnl, random.uniform(0.5, 5.0))
            
            # Обновляем баланс
            new_balance = monitor.performance_tracker.current_balance
            monitor.performance_tracker.update_balance(new_balance)
            
            # Получаем данные дашборда
            dashboard_data = monitor.get_dashboard_data()
            
            print(f"\n=== ОБНОВЛЕНИЕ {i+1} ===")
            print(f"Баланс: ${dashboard_data['performance']['current_balance']:.2f}")
            print(f"Общий P&L: ${dashboard_data['performance']['total_pnl']:.2f}")
            print(f"Дневной P&L: ${dashboard_data['performance']['daily_pnl']:.2f}")
            print(f"Процент выигрышных: {dashboard_data['performance']['win_rate']:.1%}")
            print(f"Коэффициент Шарпа: {dashboard_data['performance']['sharpe_ratio']:.2f}")
            print(f"Активных алертов: {len(dashboard_data['alerts'])}")
            
            if dashboard_data['alerts']:
                for alert in dashboard_data['alerts']:
                    print(f"  - {alert['level'].upper()}: {alert['message']}")
            
            time.sleep(2)
    
    finally:
        # Останавливаем мониторинг
        monitor.stop_monitoring()
        
        # Экспортируем метрики
        filename = monitor.export_metrics()
        print(f"\nМетрики экспортированы в {filename}")