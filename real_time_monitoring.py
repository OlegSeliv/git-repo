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
    level: AlertLevel
    metric_type: MetricType
    message: str
    timestamp: datetime
    value: float
    threshold: float
    is_active: bool = True
    acknowledged: bool = False

@dataclass
class MetricSnapshot:
    """Снимок метрики"""
    name: str
    value: float
    timestamp: datetime
    metric_type: MetricType
    trend: str = "stable"  # "up", "down", "stable"
    change_pct: float = 0.0

@dataclass
class PerformanceReport:
    """Отчет о производительности"""
    timestamp: datetime
    total_pnl: float
    daily_pnl: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    active_trades: int
    total_trades: int
    equity: float
    risk_metrics: Dict[str, float]
    market_conditions: Dict[str, Any]

class MetricCollector:
    """Сборщик метрик"""
    
    def __init__(self):
        self.metrics_history = {}
        self.current_metrics = {}
        self.collectors = {}
    
    def register_metric(self, name: str, metric_type: MetricType, 
                       collector_func: Callable[[], float]):
        """Регистрирует метрику для сбора"""
        self.collectors[name] = {
            'type': metric_type,
            'func': collector_func
        }
    
    def collect_metrics(self) -> Dict[str, MetricSnapshot]:
        """Собирает все зарегистрированные метрики"""
        snapshots = {}
        current_time = datetime.now()
        
        for name, collector in self.collectors.items():
            try:
                value = collector['func']()
                trend = self._calculate_trend(name, value)
                change_pct = self._calculate_change(name, value)
                
                snapshot = MetricSnapshot(
                    name=name,
                    value=value,
                    timestamp=current_time,
                    metric_type=collector['type'],
                    trend=trend,
                    change_pct=change_pct
                )
                
                snapshots[name] = snapshot
                self.current_metrics[name] = snapshot
                
                # Сохраняем в историю
                if name not in self.metrics_history:
                    self.metrics_history[name] = []
                self.metrics_history[name].append(snapshot)
                
                # Ограничиваем размер истории
                if len(self.metrics_history[name]) > 1000:
                    self.metrics_history[name] = self.metrics_history[name][-500:]
                
            except Exception as e:
                logger.error(f"Ошибка при сборе метрики {name}: {e}")
        
        return snapshots
    
    def _calculate_trend(self, name: str, current_value: float) -> str:
        """Вычисляет тренд метрики"""
        if name not in self.metrics_history or len(self.metrics_history[name]) < 2:
            return "stable"
        
        recent_values = [m.value for m in self.metrics_history[name][-5:]]
        if len(recent_values) < 2:
            return "stable"
        
        avg_old = np.mean(recent_values[:-1])
        if avg_old == 0:
            return "stable"
        
        change_pct = (current_value - avg_old) / avg_old
        
        if change_pct > 0.05:  # 5% рост
            return "up"
        elif change_pct < -0.05:  # 5% падение
            return "down"
        else:
            return "stable"
    
    def _calculate_change(self, name: str, current_value: float) -> float:
        """Вычисляет изменение метрики в процентах"""
        if name not in self.metrics_history or len(self.metrics_history[name]) < 1:
            return 0.0
        
        previous_value = self.metrics_history[name][-1].value
        if previous_value == 0:
            return 0.0
        
        return (current_value - previous_value) / previous_value * 100

class AlertManager:
    """Менеджер алертов"""
    
    def __init__(self):
        self.alerts = []
        self.alert_rules = {}
        self.alert_handlers = {}
        self.max_alerts = 1000
    
    def add_alert_rule(self, metric_name: str, condition: str, threshold: float,
                      level: AlertLevel, message_template: str):
        """Добавляет правило для алерта"""
        rule_id = f"{metric_name}_{condition}_{threshold}"
        self.alert_rules[rule_id] = {
            'metric_name': metric_name,
            'condition': condition,
            'threshold': threshold,
            'level': level,
            'message_template': message_template
        }
    
    def check_alerts(self, metrics: Dict[str, MetricSnapshot]):
        """Проверяет условия для алертов"""
        for rule_id, rule in self.alert_rules.items():
            metric_name = rule['metric_name']
            
            if metric_name not in metrics:
                continue
            
            metric = metrics[metric_name]
            value = metric.value
            threshold = rule['threshold']
            condition = rule['condition']
            
            should_alert = False
            
            if condition == "greater_than" and value > threshold:
                should_alert = True
            elif condition == "less_than" and value < threshold:
                should_alert = True
            elif condition == "equals" and abs(value - threshold) < 0.001:
                should_alert = True
            elif condition == "change_greater_than" and abs(metric.change_pct) > threshold:
                should_alert = True
            
            if should_alert:
                # Проверяем, не создан ли уже такой алерт
                existing_alert = self._find_existing_alert(metric_name, rule_id)
                
                if not existing_alert:
                    self._create_alert(metric, rule)
    
    def _find_existing_alert(self, metric_name: str, rule_id: str) -> Optional[Alert]:
        """Ищет существующий активный алерт"""
        for alert in self.alerts:
            if (alert.metric_type.value == metric_name and 
                alert.is_active and 
                not alert.acknowledged):
                return alert
        return None
    
    def _create_alert(self, metric: MetricSnapshot, rule: Dict):
        """Создает новый алерт"""
        alert_id = f"{rule['metric_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        message = rule['message_template'].format(
            metric_name=metric.name,
            value=metric.value,
            threshold=rule['threshold'],
            change_pct=metric.change_pct
        )
        
        alert = Alert(
            id=alert_id,
            level=rule['level'],
            metric_type=metric.metric_type,
            message=message,
            timestamp=datetime.now(),
            value=metric.value,
            threshold=rule['threshold']
        )
        
        self.alerts.append(alert)
        
        # Ограничиваем количество алертов
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Вызываем обработчики
        self._trigger_alert_handlers(alert)
    
    def _trigger_alert_handlers(self, alert: Alert):
        """Вызывает обработчики алертов"""
        for handler in self.alert_handlers.values():
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Ошибка в обработчике алерта: {e}")
    
    def register_alert_handler(self, name: str, handler: Callable[[Alert], None]):
        """Регистрирует обработчик алертов"""
        self.alert_handlers[name] = handler
    
    def acknowledge_alert(self, alert_id: str):
        """Подтверждает алерт"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                break
    
    def get_active_alerts(self) -> List[Alert]:
        """Возвращает активные алерты"""
        return [a for a in self.alerts if a.is_active and not a.acknowledged]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Возвращает алерты по уровню"""
        return [a for a in self.alerts if a.level == level and a.is_active]

class PerformanceAnalyzer:
    """Анализатор производительности"""
    
    def __init__(self):
        self.trade_history = []
        self.equity_curve = []
        self.peak_equity = 0
        self.max_drawdown = 0
        self.current_drawdown = 0
    
    def add_trade(self, trade_data: Dict):
        """Добавляет сделку в историю"""
        self.trade_history.append(trade_data)
        self._update_equity_curve()
    
    def update_equity(self, current_equity: float):
        """Обновляет текущий капитал"""
        self.equity_curve.append({
            'timestamp': datetime.now(),
            'equity': current_equity
        })
        
        # Обновляем пиковый капитал
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # Вычисляем просадку
        self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
    
    def _update_equity_curve(self):
        """Обновляет кривую капитала"""
        if not self.trade_history:
            return
        
        # Вычисляем текущий капитал на основе сделок
        total_pnl = sum(trade.get('pnl', 0) for trade in self.trade_history)
        current_equity = 10000 + total_pnl  # Предполагаем начальный капитал 10000
        
        self.update_equity(current_equity)
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """Вычисляет метрики производительности"""
        if not self.trade_history:
            return {}
        
        # Базовые метрики
        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trade_history if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # P&L метрики
        total_pnl = sum(t.get('pnl', 0) for t in self.trade_history)
        gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Доходность
        if self.equity_curve:
            initial_equity = self.equity_curve[0]['equity']
            current_equity = self.equity_curve[-1]['equity']
            total_return = (current_equity - initial_equity) / initial_equity
        else:
            total_return = 0
        
        # Sharpe ratio (упрощенный)
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                if prev_equity > 0:
                    ret = (curr_equity - prev_equity) / prev_equity
                    returns.append(ret)
            
            if returns:
                avg_return = np.mean(returns)
                return_std = np.std(returns)
                sharpe_ratio = avg_return / return_std if return_std > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'current_equity': self.equity_curve[-1]['equity'] if self.equity_curve else 0
        }

class RealTimeMonitor:
    """Основной класс мониторинга в реальном времени"""
    
    def __init__(self, update_interval: int = 60):
        self.update_interval = update_interval  # секунды
        self.is_running = False
        self.monitor_thread = None
        
        self.metric_collector = MetricCollector()
        self.alert_manager = AlertManager()
        self.performance_analyzer = PerformanceAnalyzer()
        
        self.setup_default_metrics()
        self.setup_default_alerts()
        self.setup_default_handlers()
    
    def start_monitoring(self):
        """Запускает мониторинг"""
        if self.is_running:
            logger.warning("Мониторинг уже запущен")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Мониторинг запущен")
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        logger.info("Мониторинг остановлен")
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                # Собираем метрики
                metrics = self.metric_collector.collect_metrics()
                
                # Проверяем алерты
                self.alert_manager.check_alerts(metrics)
                
                # Обновляем производительность
                self._update_performance_metrics()
                
                # Логируем статус
                if len(metrics) > 0:
                    logger.debug(f"Собрано {len(metrics)} метрик")
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
            
            time.sleep(self.update_interval)
    
    def _update_performance_metrics(self):
        """Обновляет метрики производительности"""
        metrics = self.performance_analyzer.calculate_performance_metrics()
        
        # Регистрируем метрики
        for name, value in metrics.items():
            self.metric_collector.register_metric(
                name=f"performance_{name}",
                metric_type=MetricType.PERFORMANCE,
                collector_func=lambda v=value: v
            )
    
    def setup_default_metrics(self):
        """Настраивает метрики по умолчанию"""
        # Метрики производительности
        self.metric_collector.register_metric(
            "win_rate",
            MetricType.PERFORMANCE,
            lambda: self.performance_analyzer.calculate_performance_metrics().get('win_rate', 0)
        )
        
        self.metric_collector.register_metric(
            "sharpe_ratio",
            MetricType.PERFORMANCE,
            lambda: self.performance_analyzer.calculate_performance_metrics().get('sharpe_ratio', 0)
        )
        
        self.metric_collector.register_metric(
            "max_drawdown",
            MetricType.RISK,
            lambda: self.performance_analyzer.calculate_performance_metrics().get('max_drawdown', 0)
        )
        
        self.metric_collector.register_metric(
            "current_drawdown",
            MetricType.RISK,
            lambda: self.performance_analyzer.calculate_performance_metrics().get('current_drawdown', 0)
        )
    
    def setup_default_alerts(self):
        """Настраивает алерты по умолчанию"""
        # Алерт на большую просадку
        self.alert_manager.add_alert_rule(
            "current_drawdown",
            "greater_than",
            0.1,  # 10%
            AlertLevel.WARNING,
            "Текущая просадка {value:.1%} превышает порог {threshold:.1%}"
        )
        
        # Алерт на критическую просадку
        self.alert_manager.add_alert_rule(
            "current_drawdown",
            "greater_than",
            0.2,  # 20%
            AlertLevel.CRITICAL,
            "КРИТИЧЕСКАЯ ПРОСАДКА: {value:.1%} превышает порог {threshold:.1%}"
        )
        
        # Алерт на низкий коэффициент Шарпа
        self.alert_manager.add_alert_rule(
            "sharpe_ratio",
            "less_than",
            0.5,
            AlertLevel.WARNING,
            "Низкий коэффициент Шарпа: {value:.2f}"
        )
        
        # Алерт на низкий процент выигрышных сделок
        self.alert_manager.add_alert_rule(
            "win_rate",
            "less_than",
            0.4,  # 40%
            AlertLevel.WARNING,
            "Низкий процент выигрышных сделок: {value:.1%}"
        )
    
    def setup_default_handlers(self):
        """Настраивает обработчики алертов по умолчанию"""
        def log_alert_handler(alert: Alert):
            logger.warning(f"АЛЕРТ [{alert.level.value.upper()}]: {alert.message}")
        
        def critical_alert_handler(alert: Alert):
            if alert.level == AlertLevel.CRITICAL:
                logger.critical(f"КРИТИЧЕСКИЙ АЛЕРТ: {alert.message}")
                # Здесь можно добавить отправку уведомлений, остановку торговли и т.д.
        
        self.alert_manager.register_alert_handler("log", log_alert_handler)
        self.alert_manager.register_alert_handler("critical", critical_alert_handler)
    
    def add_trade(self, trade_data: Dict):
        """Добавляет сделку для анализа"""
        self.performance_analyzer.add_trade(trade_data)
    
    def get_performance_report(self) -> PerformanceReport:
        """Возвращает отчет о производительности"""
        metrics = self.performance_analyzer.calculate_performance_metrics()
        
        return PerformanceReport(
            timestamp=datetime.now(),
            total_pnl=metrics.get('total_pnl', 0),
            daily_pnl=0,  # Нужно вычислять отдельно
            win_rate=metrics.get('win_rate', 0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0),
            max_drawdown=metrics.get('max_drawdown', 0),
            current_drawdown=metrics.get('current_drawdown', 0),
            active_trades=0,  # Нужно отслеживать отдельно
            total_trades=metrics.get('total_trades', 0),
            equity=metrics.get('current_equity', 0),
            risk_metrics={
                'max_drawdown': metrics.get('max_drawdown', 0),
                'current_drawdown': metrics.get('current_drawdown', 0)
            },
            market_conditions={}  # Нужно интегрировать с анализом рынка
        )
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Возвращает данные для дашборда"""
        report = self.get_performance_report()
        active_alerts = self.alert_manager.get_active_alerts()
        current_metrics = self.metric_collector.current_metrics
        
        return {
            'performance': {
                'total_pnl': report.total_pnl,
                'win_rate': report.win_rate,
                'sharpe_ratio': report.sharpe_ratio,
                'max_drawdown': report.max_drawdown,
                'current_drawdown': report.current_drawdown,
                'equity': report.equity
            },
            'alerts': {
                'total': len(active_alerts),
                'critical': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
                'warning': len([a for a in active_alerts if a.level == AlertLevel.WARNING]),
                'recent': [{'level': a.level.value, 'message': a.message, 'timestamp': a.timestamp.isoformat()} 
                          for a in active_alerts[-5:]]
            },
            'metrics': {name: {'value': metric.value, 'trend': metric.trend, 'change_pct': metric.change_pct}
                       for name, metric in current_metrics.items()},
            'timestamp': datetime.now().isoformat()
        }

# Пример использования
if __name__ == "__main__":
    # Создаем монитор
    monitor = RealTimeMonitor(update_interval=10)
    
    # Запускаем мониторинг
    monitor.start_monitoring()
    
    # Симулируем добавление сделок
    for i in range(10):
        trade_data = {
            'id': f'trade_{i}',
            'pnl': np.random.normal(0, 100),
            'timestamp': datetime.now()
        }
        monitor.add_trade(trade_data)
        time.sleep(1)
    
    # Получаем данные дашборда
    dashboard_data = monitor.get_dashboard_data()
    print("=== ДАННЫЕ ДАШБОРДА ===")
    print(json.dumps(dashboard_data, indent=2, default=str))
    
    # Останавливаем мониторинг
    time.sleep(5)
    monitor.stop_monitoring()