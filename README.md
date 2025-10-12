# Адаптивный торговый робот с устойчивостью к изменениям рынка

Комплексная система для автоматической торговли, которая адаптируется к изменяющимся рыночным условиям и оптимизирует время запуска для максимальной эффективности.

## 🎯 Ключевые возможности

### 1. Устранение влияния изменений рынка
- **Адаптация к рыночным режимам**: Автоматическое определение текущего состояния рынка (тренд, боковик, волатильность)
- **Динамическая настройка параметров**: Параметры стратегии автоматически корректируются под текущие условия
- **Множественные методы детекции**: Статистические, машинное обучение и технические индикаторы
- **Риск-менеджмент**: Адаптивные стоп-лоссы и размеры позиций

### 2. Оптимальное время запуска
- **Анализ торговых сессий**: Учет особенностей азиатской, европейской и американской сессий
- **Внутридневные паттерны**: Определение лучших часов для торговли на основе исторических данных
- **Сезонные факторы**: Учет праздников, выходных и особых периодов
- **Прогноз на 24 часа вперед**: Поиск оптимальных окон для запуска

## 📁 Структура проекта

```
├── market_adaptation.py      # Модуль адаптации к рыночным условиям
├── optimal_timing.py         # Определение оптимального времени запуска
├── market_regime_detector.py # Детектор рыночных режимов
├── dynamic_parameters.py     # Динамическая оптимизация параметров
├── trading_robot.py         # Главный модуль торгового робота
└── requirements.txt         # Зависимости
```

## 🚀 Быстрый старт

### Установка

```bash
pip install -r requirements.txt
```

### Базовое использование

```python
import pandas as pd
from trading_robot import AdaptiveTradingRobot

# Создание робота
robot = AdaptiveTradingRobot(
    symbol="EURUSD",
    initial_capital=10000,
    max_risk_per_trade=0.02,
    strategy_type='trend_following'
)

# Загрузка данных (пример структуры)
price_data = pd.DataFrame({
    'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='1H'),
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# Запуск робота (автоматически выберет оптимальное время)
robot.start(price_data)

# Обработка новых данных
for _, bar in price_data.iterrows():
    signal = robot.process_bar(bar)
    
# Получение отчета
report = robot.get_performance_report()
print(report)

# Остановка робота
robot.stop()
```

## 🔧 Компоненты системы

### 1. MarketAdaptation
Адаптирует параметры торговли к текущим рыночным условиям:
- Размер позиции
- Уровни стоп-лосс и тейк-профит
- Пороги сигналов
- Частота торговли

### 2. OptimalTimingAnalyzer
Определяет лучшее время для торговли:
- Анализ торговых сессий
- Исторические паттерны эффективности
- Оценка ликвидности и волатильности
- Рекомендации по времени запуска

### 3. MarketRegimeDetector
Классифицирует текущее состояние рынка:
- Восходящий/нисходящий тренд
- Боковое движение (ranging)
- Высокая/низкая волатильность
- Переходные состояния

### 4. DynamicParameterOptimizer
Оптимизирует параметры стратегии:
- Генетические алгоритмы
- Байесовская оптимизация
- Walk-forward анализ
- Адаптивная корректировка

## 📊 Примеры использования

### Определение оптимального времени запуска

```python
from optimal_timing import OptimalTimingAnalyzer

analyzer = OptimalTimingAnalyzer(symbol="EURUSD")

# Анализ текущего времени
timing_score = analyzer.analyze_timing(
    historical_data=price_data,
    strategy_type='trend_following'
)

print(f"Рекомендация: {timing_score.recommendation}")
print(f"Score: {timing_score.score:.2f}")
print(f"Сессия: {timing_score.session}")

# Поиск лучших окон в ближайшие 24 часа
best_windows = analyzer.find_best_launch_windows(
    historical_data=price_data,
    strategy_type='trend_following',
    next_hours=24
)

for window in best_windows[:3]:
    print(f"Время: {window.timestamp}, Score: {window.score:.2f}")
```

### Адаптация к рыночным условиям

```python
from market_adaptation import MarketAdaptation

adapter = MarketAdaptation(lookback_period=100)

# Анализ условий
conditions = adapter.analyze_market_conditions(price_data)

# Адаптация параметров
base_params = {
    'position_size': 1.0,
    'stop_loss': 0.02,
    'take_profit': 0.04,
    'signal_threshold': 0.5
}

adapted_params = adapter.adapt_parameters(base_params)
print(f"Адаптированные параметры: {adapted_params}")

# Проверка возможности торговли
can_trade = adapter.should_trade(signal_strength=0.7)
print(f"Торговать: {can_trade}")
```

### Определение рыночного режима

```python
from market_regime_detector import MarketRegimeDetector

detector = MarketRegimeDetector()

# Определение режима
regime = detector.detect_regime(price_data)

print(f"Режим: {regime.regime_type}")
print(f"Уверенность: {regime.confidence:.2f}")
print(f"Продолжительность: {regime.duration} баров")
print(f"Характеристики: {regime.characteristics}")
```

## ⚙️ Настройки и конфигурация

### Параметры робота

```python
robot = AdaptiveTradingRobot(
    symbol="EURUSD",
    initial_capital=10000,
    max_risk_per_trade=0.02,  # 2% риска на сделку
    strategy_type='trend_following'  # или 'mean_reversion', 'momentum'
)

# Настройки
robot.settings = {
    'max_positions': 3,           # Макс. количество позиций
    'use_timing_filter': True,    # Использовать фильтр времени
    'use_regime_filter': True,    # Использовать фильтр режима
    'use_adaptive_parameters': True,  # Адаптивные параметры
    'min_timing_score': 0.5,      # Мин. score времени
    'reoptimize_frequency': 100,  # Частота реоптимизации
    'max_correlation': 0.7        # Макс. корреляция позиций
}
```

### Типы стратегий

1. **trend_following** - Следование за трендом
2. **mean_reversion** - Возврат к среднему
3. **momentum** - Моментум стратегия

## 📈 Преимущества системы

### Устойчивость к изменениям рынка
- **Автоматическая адаптация**: Система сама подстраивается под новые условия
- **Множественные фильтры**: Снижение количества ложных сигналов
- **Динамический риск-менеджмент**: Защита капитала в сложных условиях

### Оптимизация времени запуска
- **Увеличение прибыльности**: Вход в рынок в оптимальные моменты
- **Снижение просадок**: Избегание неблагоприятных периодов
- **Учет микроструктуры рынка**: Использование особенностей торговых сессий

## 🔍 Мониторинг и отчетность

```python
# Получение отчета о производительности
report = robot.get_performance_report()

print(f"Всего сделок: {report['total_trades']}")
print(f"Win Rate: {report['win_rate']:.2%}")
print(f"Profit Factor: {report['profit_factor']:.2f}")
print(f"Sharpe Ratio: {report['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {report['max_drawdown']:.2%}")
print(f"Общий доход: {report['total_return']:.2%}")

# Статистика по режимам
for regime, stats in report['regime_statistics'].items():
    print(f"{regime}: {stats['count']} сделок, прибыль: {stats['profit']:.2f}")
```

## 🛡️ Риск-менеджмент

Система включает многоуровневую защиту:

1. **Адаптивные стоп-лоссы**: Корректировка под волатильность
2. **Динамический размер позиций**: Уменьшение в рискованных условиях
3. **Фильтрация сигналов**: Отсев слабых и сомнительных входов
4. **Ограничение экспозиции**: Контроль общего риска портфеля
5. **Trailing stops**: Защита прибыли в выигрышных сделках

## 📝 Рекомендации по использованию

### Для устранения влияния изменений рынка:
1. Включите адаптивные параметры (`use_adaptive_parameters=True`)
2. Используйте фильтр режимов (`use_regime_filter=True`)
3. Настройте частоту реоптимизации (50-200 баров)
4. Выберите подходящую стратегию для текущего рынка

### Для оптимального времени запуска:
1. Включите временной фильтр (`use_timing_filter=True`)
2. Установите минимальный timing score (0.5-0.7)
3. Используйте функцию поиска оптимальных окон
4. Учитывайте рекомендации системы

## ⚠️ Важные замечания

1. **Тестирование**: Обязательно проводите бэктестинг на исторических данных
2. **Риски**: Никакая система не гарантирует прибыль
3. **Мониторинг**: Регулярно проверяйте работу системы
4. **Обновления**: Периодически обновляйте параметры и модели

## 📚 Дополнительные возможности

- Экспорт/импорт параметров
- Интеграция с брокерами через API
- Визуализация результатов
- Уведомления о сделках
- Логирование всех операций

## 🤝 Поддержка

При возникновении вопросов обращайтесь к документации модулей или создавайте issue в репозитории.

---

**Disclaimer**: Данная система предназначена для образовательных целей. Торговля на финансовых рынках связана с риском потери капитала. Всегда проводите собственный анализ перед принятием торговых решений.