# Система оптимизации торгового робота

Комплексная система для устранения влияния изменений рынка на результат торгового робота и поиска оптимального времени запуска советника.

## 🎯 Основные проблемы, которые решает система

1. **Влияние изменений рынка** - система автоматически адаптируется к различным рыночным условиям
2. **Оптимизация времени запуска** - находит наиболее выгодное время для торговли
3. **Управление рисками** - продвинутое управление позициями и рисками
4. **Мониторинг в реальном времени** - отслеживание производительности и автоматические корректировки

## 🏗️ Архитектура системы

### 1. Система адаптации к изменениям рынка (`market_adaptation_system.py`)

**Основные компоненты:**
- `VolatilityDetector` - детектор волатильности рынка
- `TrendDetector` - детектор тренда и его силы
- `MarketRegimeDetector` - определение режима рынка (тренд, флет, высокая/низкая волатильность)
- `AdaptiveParameterManager` - адаптация параметров торговли под текущие условия
- `MarketAdaptationSystem` - основная система адаптации

**Режимы рынка:**
- `TRENDING` - трендовый рынок
- `RANGING` - флетовый рынок
- `HIGH_VOLATILITY` - высокая волатильность
- `LOW_VOLATILITY` - низкая волатильность
- `BREAKOUT` - пробой
- `REVERSAL` - разворот

**Адаптивные параметры:**
- Размер стоп-лосса
- Размер тейк-профита
- Размер позиции
- Максимальное количество позиций
- Периоды индикаторов

### 2. Система оптимизации времени запуска (`timing_optimization_system.py`)

**Основные компоненты:**
- `MarketSessionAnalyzer` - анализ торговых сессий (Азия, Лондон, Нью-Йорк)
- `VolatilityPatternAnalyzer` - анализ паттернов волатильности по времени
- `EconomicCalendarAnalyzer` - учет экономических событий
- `TimingOptimizer` - основной оптимизатор времени

**Торговые сессии:**
- `ASIAN` - азиатская сессия (0-8 UTC)
- `LONDON` - лондонская сессия (8-16 UTC)
- `NEW_YORK` - нью-йоркская сессия (13-21 UTC)
- `OVERLAP_LONDON_NY` - пересечение Лондон-Нью-Йорк (13-16 UTC)
- `OVERLAP_ASIAN_LONDON` - пересечение Азия-Лондон (6-10 UTC)

**Фазы рынка:**
- `OPENING` - открытие сессии
- `MID_SESSION` - середина сессии
- `CLOSING` - закрытие сессии
- `OVERNIGHT` - вне основных сессий

### 3. Продвинутое управление рисками (`advanced_risk_management.py`)

**Основные компоненты:**
- `PositionSizingCalculator` - расчет размера позиций
- `DynamicStopLossManager` - динамические стоп-лоссы
- `PortfolioRiskManager` - управление рисками портфеля
- `AdvancedRiskManager` - основная система управления рисками

**Методы управления рисками:**
- Адаптивный расчет размера позиций
- Трейлинг стоп-лоссы
- Перевод в безубыток
- Ограничения по экспозиции
- Контроль последовательных убытков
- Дневные лимиты убытков

### 4. Фреймворк тестирования (`backtesting_framework.py`)

**Основные компоненты:**
- `Strategy` - базовый класс стратегий
- `BacktestEngine` - движок бэктестинга
- `ParameterOptimizer` - оптимизация параметров
- `WalkForwardAnalyzer` - Walk-Forward анализ

**Метрики производительности:**
- Общий P&L
- Процент выигрышных сделок
- Коэффициент Шарпа
- Максимальная просадка
- Profit Factor
- VaR (Value at Risk)
- Calmar Ratio
- Sortino Ratio

### 5. Система мониторинга (`realtime_monitoring_system.py`)

**Основные компоненты:**
- `MetricCollector` - сбор метрик
- `AlertManager` - управление алертами
- `PerformanceTracker` - трекинг производительности
- `RealtimeMonitor` - основной монитор

**Типы алертов:**
- `INFO` - информационные
- `WARNING` - предупреждения
- `ERROR` - ошибки
- `CRITICAL` - критические

**Метрики мониторинга:**
- Баланс счета
- P&L (общий и дневной)
- Коэффициент Шарпа
- Просадка (текущая и максимальная)
- Количество активных сделок
- Время работы системы

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install numpy pandas matplotlib seaborn psutil
```

### Базовое использование

```python
from trading_robot_optimization import OptimizedTradingRobot

# Создаем робота
robot = OptimizedTradingRobot(initial_balance=10000)

# Анализируем исторические данные
analysis = robot.analyze_market_and_timing(historical_data)

# Оптимизируем параметры стратегии
optimization = robot.optimize_strategy_parameters(
    historical_data, 
    MovingAverageCrossoverStrategy, 
    parameter_ranges
)

# Запускаем торговлю
robot.start_trading(real_time_data_callback)
```

### Запуск демонстрации

```bash
python trading_robot_optimization.py
```

## 📊 Примеры использования

### 1. Анализ рыночных условий

```python
from market_adaptation_system import MarketAdaptationSystem

# Создаем систему адаптации
adaptation = MarketAdaptationSystem()

# Анализируем условия рынка
conditions = adaptation.analyze_market_conditions(prices, volume)

print(f"Режим рынка: {conditions.regime.value}")
print(f"Волатильность: {conditions.volatility:.3f}")
print(f"Стоит ли торговать: {adaptation.should_trade()}")

# Получаем адаптированные параметры
params = adaptation.get_adaptive_parameters()
print(f"Параметры: {params}")
```

### 2. Оптимизация времени торговли

```python
from timing_optimization_system import TimingOptimizer

# Создаем оптимизатор времени
optimizer = TimingOptimizer()

# Оптимизируем время
analysis = optimizer.optimize_timing(price_data)

print(f"Лучший час: {analysis.best_hour}:00 UTC")
print(f"Лучшая сессия: {analysis.best_session.value}")
print(f"Ожидаемая доходность: {analysis.expected_return:.2%}")

# Получаем расписание торговли
schedule = optimizer.get_trading_schedule(analysis)
print(f"Расписание: {schedule}")
```

### 3. Управление рисками

```python
from advanced_risk_management import AdvancedRiskManager

# Создаем менеджер рисков
risk_manager = AdvancedRiskManager(initial_balance=10000)

# Вычисляем размер позиции
position_size = risk_manager.calculate_position_size(
    symbol="EURUSD",
    entry_price=1.2000,
    stop_loss=1.1950,
    volatility=0.15
)

print(f"Размер позиции: {position_size:.2f} лотов")

# Проверяем, можно ли открыть позицию
can_trade = risk_manager.can_open_position("EURUSD")
print(f"Можно торговать: {can_trade}")
```

### 4. Бэктестинг стратегии

```python
from backtesting_framework import BacktestEngine, MovingAverageCrossoverStrategy

# Создаем стратегию
strategy = MovingAverageCrossoverStrategy(fast_period=10, slow_period=20)

# Запускаем бэктест
engine = BacktestEngine(initial_capital=10000)
result = engine.run_backtest(strategy, data)

print(f"Общий P&L: {result.total_pnl:.2f}")
print(f"Коэффициент Шарпа: {result.sharpe_ratio:.2f}")
print(f"Максимальная просадка: {result.max_drawdown:.1%}")
```

### 5. Мониторинг в реальном времени

```python
from realtime_monitoring_system import RealtimeMonitor

# Создаем монитор
monitor = RealtimeMonitor(initial_balance=10000)

# Запускаем мониторинг
monitor.start_monitoring(update_interval=60)

# Получаем данные дашборда
dashboard_data = monitor.get_dashboard_data()
print(f"Текущий баланс: ${dashboard_data['performance']['current_balance']:.2f}")
print(f"Активных алертов: {len(dashboard_data['alerts'])}")

# Останавливаем мониторинг
monitor.stop_monitoring()
```

## 🔧 Настройка и конфигурация

### Настройка алертов

```python
# Добавляем пользовательский алерт
monitor.add_custom_alert(
    metric_name='current_drawdown',
    condition='greater_than',
    threshold=0.05,
    level=AlertLevel.WARNING,
    message="Просадка превысила 5%"
)
```

### Настройка параметров адаптации

```python
# Настраиваем параметры для разных режимов рынка
regime_parameters = {
    MarketRegime.TRENDING: {
        'stop_loss_pct': 0.03,
        'take_profit_pct': 0.06,
        'position_size': 0.15
    },
    MarketRegime.RANGING: {
        'stop_loss_pct': 0.015,
        'take_profit_pct': 0.03,
        'position_size': 0.08
    }
}
```

### Настройка расписания торговли

```python
# Создаем кастомное расписание
custom_schedule = {
    'primary_hours': [9, 10, 11, 14, 15, 16],
    'secondary_hours': [8, 12, 13, 17],
    'avoid_hours': [0, 1, 2, 3, 4, 5, 6, 7, 22, 23],
    'session_focus': 'london',
    'phase_focus': 'mid_session'
}
```

## 📈 Метрики и аналитика

### Ключевые метрики производительности

1. **Финансовые метрики:**
   - Общий P&L
   - Дневной P&L
   - Процент выигрышных сделок
   - Profit Factor

2. **Рисковые метрики:**
   - Максимальная просадка
   - Текущая просадка
   - VaR (Value at Risk)
   - Коэффициент Шарпа

3. **Операционные метрики:**
   - Количество сделок
   - Средняя длительность сделки
   - Активные позиции
   - Время работы системы

### Алерты и уведомления

Система автоматически отслеживает:
- Превышение лимитов просадки
- Дневные убытки
- Снижение коэффициента Шарпа
- Слишком много активных позиций
- Системные ошибки

## 🛠️ Расширение функциональности

### Создание собственной стратегии

```python
from backtesting_framework import Strategy, TradeDirection

class MyCustomStrategy(Strategy):
    def __init__(self, param1: int, param2: float):
        parameters = {'param1': param1, 'param2': param2}
        super().__init__("MyStrategy", parameters)
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # Ваша логика генерации сигналов
        pass
    
    def should_enter(self, data: pd.DataFrame, index: int) -> Tuple[bool, TradeDirection]:
        # Ваша логика входа
        pass
    
    def should_exit(self, trade: Trade, data: pd.DataFrame, index: int) -> Tuple[bool, str]:
        # Ваша логика выхода
        pass
```

### Добавление новых индикаторов

```python
def calculate_custom_indicator(prices: List[float], period: int) -> List[float]:
    """Ваш пользовательский индикатор"""
    # Логика расчета индикатора
    return indicator_values
```

## 🔍 Диагностика и отладка

### Логирование

Система использует стандартный модуль `logging` Python:

```python
import logging

# Настройка уровня логирования
logging.basicConfig(level=logging.DEBUG)

# В коде
logger = logging.getLogger(__name__)
logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
```

### Экспорт данных

```python
# Экспорт метрик в JSON
filename = monitor.export_metrics("my_metrics.json")

# Экспорт результатов бэктестинга
import json
with open("backtest_results.json", "w") as f:
    json.dump(result.__dict__, f, indent=2)
```

## 📚 Дополнительные ресурсы

### Рекомендуемая литература

1. "Quantitative Trading" - Ernest Chan
2. "Algorithmic Trading" - Ernie Chan
3. "Evidence-Based Technical Analysis" - David Aronson
4. "The Evaluation and Optimization of Trading Strategies" - Robert Pardo

### Полезные ссылки

- [QuantConnect](https://www.quantconnect.com/) - платформа для алгоритмической торговли
- [Zipline](https://github.com/quantopian/zipline) - библиотека для бэктестинга
- [Backtrader](https://www.backtrader.com/) - фреймворк для бэктестинга
- [TA-Lib](https://ta-lib.org/) - библиотека технических индикаторов

## ⚠️ Важные замечания

1. **Тестирование:** Всегда тестируйте стратегии на исторических данных перед использованием в реальной торговле
2. **Риски:** Торговля на финансовых рынках сопряжена с высокими рисками
3. **Мониторинг:** Постоянно отслеживайте производительность системы
4. **Обновления:** Регулярно обновляйте параметры в соответствии с изменениями рынка
5. **Резервные копии:** Делайте резервные копии конфигураций и данных

## 🤝 Поддержка

Для вопросов и предложений создавайте issues в репозитории или обращайтесь к разработчикам.

## 📄 Лицензия

MIT License - см. файл LICENSE для подробностей.

---

**Удачной торговли! 📈**