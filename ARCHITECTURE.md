# Архитектура торгового робота

Этот документ описывает внутреннюю структуру и логику работы торгового робота для MT5.

## 📐 Структура кода

### Основные компоненты

```
TradingRobot.mq5
├── Входные параметры (Input Parameters)
├── Глобальные переменные (Global Variables)
├── OnInit() - Инициализация
├── OnDeinit() - Деинициализация
├── OnTick() - Основной цикл
└── Вспомогательные функции (Helper Functions)
```

## 🔄 Жизненный цикл робота

### 1. Инициализация (OnInit)
```mql5
OnInit()
├── Создание индикаторов (handleFastMA, handleSlowMA)
├── Настройка массивов (ArraySetAsSeries)
├── Инициализация переменных (lastBarTime)
└── Вывод информации в лог
```

**Что происходит:**
- Создаются хэндлы индикаторов MA
- Настраивается индексация массивов (как в терминале)
- Запоминается время последнего бара

### 2. Основной цикл (OnTick)
```mql5
OnTick()
├── CheckNewBar() - Проверка нового бара
├── CopyBuffer() - Копирование данных индикаторов
├── TrailingStopAll() - Трейлинг-стоп (если включен)
├── GetTradeSignal() - Получение торгового сигнала
└── OpenBuy() / OpenSell() - Открытие позиции
```

**Логика работы:**
1. Проверяется, сформировался ли новый бар
2. Если да - копируются данные индикаторов
3. Применяется трейлинг-стоп к открытым позициям
4. Анализируются торговые сигналы
5. При наличии сигнала и отсутствии позиции - открывается сделка

### 3. Деинициализация (OnDeinit)
```mql5
OnDeinit()
├── Освобождение индикаторов (IndicatorRelease)
└── Вывод информации о причине остановки
```

## 📊 Торговая логика

### Стратегия пересечения Moving Average

**Сигнал на покупку (BUY):**
```
Условие: fastMA[1] > slowMA[1] && fastMA[2] <= slowMA[2]
Описание: Быстрая MA пересекает медленную снизу вверх
```

**Сигнал на продажу (SELL):**
```
Условие: fastMA[1] < slowMA[1] && fastMA[2] >= slowMA[2]
Описание: Быстрая MA пересекает медленную сверху вниз
```

**Индексация:**
- `[0]` - текущий бар (формируется)
- `[1]` - предыдущий закрытый бар
- `[2]` - позапрошлый закрытый бар

### Управление позициями

**Открытие позиции:**
```
IsPositionOpen() == false
    └── GetTradeSignal() != 0
        ├── signal == 1 → OpenBuy()
        └── signal == -1 → OpenSell()
```

**Защита от множественных позиций:**
- Проверяется наличие открытой позиции по символу и MagicNumber
- Новая позиция открывается только если нет активных

## 💰 Управление рисками

### Фиксированный лот
```mql5
Когда UseAutoLot = false
    └── Размер лота = LotSize (например, 0.1)
```

### Автоматический расчет лота
```mql5
Когда UseAutoLot = true
    └── Расчет:
        1. riskMoney = Balance × RiskPercent / 100
        2. lots = riskMoney / (StopLoss × Point / TickSize × TickValue)
        3. Нормализация: lots = floor(lots / LotStep) × LotStep
        4. Ограничение: max(MinLot, min(lots, MaxLot))
```

**Пример:**
- Баланс: $10,000
- Риск: 2% = $200
- Stop Loss: 100 пунктов
- Tick Value: $1
- Результат: 2 лота (риск ровно $200)

### Stop Loss и Take Profit

**Для BUY:**
```mql5
SL = Ask - StopLoss × Point
TP = Ask + TakeProfit × Point
```

**Для SELL:**
```mql5
SL = Bid + StopLoss × Point
TP = Bid - TakeProfit × Point
```

## 🎯 Трейлинг-стоп

### Алгоритм для BUY позиций
```mql5
Если (Bid - OpenPrice) > TrailingStop × Point:
    NewSL = Bid - TrailingStop × Point
    
    Если NewSL > OldSL:
        Если (NewSL - OldSL) >= TrailingStep × Point:
            ModifyPosition(NewSL)
```

### Алгоритм для SELL позиций
```mql5
Если (OpenPrice - Ask) > TrailingStop × Point:
    NewSL = Ask + TrailingStop × Point
    
    Если NewSL < OldSL:
        Если (OldSL - NewSL) >= TrailingStep × Point:
            ModifyPosition(NewSL)
```

**Принцип работы:**
1. Позиция должна быть в прибыли больше чем TrailingStop
2. Новый SL лучше старого (для BUY выше, для SELL ниже)
3. Изменение SL больше минимального шага (TrailingStep)
4. SL двигается только в направлении прибыли

## 🔧 Ключевые функции

### CheckNewBar()
**Назначение:** Определяет формирование нового бара
```mql5
currentBarTime = iTime(Symbol, Period, 0)
if currentBarTime != lastBarTime:
    isNewBar = true
    lastBarTime = currentBarTime
```

### GetTradeSignal()
**Назначение:** Анализирует индикаторы и возвращает сигнал
```mql5
Возвращает:
    1  - сигнал на покупку
   -1  - сигнал на продажу
    0  - нет сигнала
```

### IsPositionOpen()
**Назначение:** Проверяет наличие открытой позиции
```mql5
Цикл по всем позициям:
    Если (Symbol == _Symbol && Magic == MagicNumber):
        return true
return false
```

### CalculateLotSize()
**Назначение:** Рассчитывает размер лота
```mql5
Если UseAutoLot == false:
    return LotSize
Иначе:
    return рассчитанный лот на основе риска
```

## 🔍 Логирование

Робот выводит в лог следующие события:

**Инициализация:**
- Параметры запуска (символ, таймфрейм, периоды MA)

**Торговые сигналы:**
- Обнаружение сигнала на покупку/продажу
- Значения индикаторов в момент сигнала

**Торговые операции:**
- Успешное открытие позиции (тикет, цена, объем)
- Ошибки при открытии (код, описание)
- Модификация позиций (трейлинг-стоп)

**Ошибки:**
- Проблемы с индикаторами
- Ошибки копирования данных

## 🛠️ Возможности модификации

### 1. Добавление новых индикаторов

```mql5
// В OnInit():
int handleRSI = iRSI(_Symbol, _Period, 14, PRICE_CLOSE);

// В OnTick():
double rsi[];
CopyBuffer(handleRSI, 0, 0, 3, rsi);

// В GetTradeSignal():
if(fastMA[1] > slowMA[1] && rsi[1] < 30)
    return 1; // Покупка при перепроданности
```

### 2. Добавление фильтра по времени

```mql5
bool IsTradeTime()
{
    MqlDateTime time;
    TimeToStruct(TimeCurrent(), time);
    
    // Торговля только с 9:00 до 18:00
    if(time.hour >= 9 && time.hour < 18)
        return true;
    
    return false;
}
```

### 3. Закрытие позиций по обратному сигналу

```mql5
// В OnTick() после GetTradeSignal():
if(signal == 1 && PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
    ClosePosition(); // Закрыть SELL, открыть BUY

if(signal == -1 && PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
    ClosePosition(); // Закрыть BUY, открыть SELL
```

### 4. Усреднение позиций

```mql5
void AddToPosition(ENUM_POSITION_TYPE type)
{
    if(type == POSITION_TYPE_BUY)
        OpenBuy();
    else
        OpenSell();
}
```

### 5. Частичное закрытие прибыльных позиций

```mql5
void PartialClose(double percent)
{
    double currentVolume = PositionGetDouble(POSITION_VOLUME);
    double closeVolume = NormalizeDouble(currentVolume * percent, 2);
    
    // Код закрытия части позиции
}
```

## ⚡ Оптимизация производительности

### Рекомендации:

1. **Не пересоздавать индикаторы на каждом тике**
   - Создавать в OnInit()
   - Использовать повторно в OnTick()

2. **Торговать только на новых барах**
   - Проверка через CheckNewBar()
   - Экономия ресурсов

3. **Минимизировать количество обращений к серверу**
   - Кэшировать данные позиций
   - Группировать операции

4. **Правильная индексация массивов**
   - ArraySetAsSeries(array, true)
   - Индексация как в терминале

## 🐛 Отладка

### Полезные функции для отладки:

```mql5
// Вывод значений индикаторов
Print("FastMA[1]=", fastMA[1], " SlowMA[1]=", slowMA[1]);

// Вывод информации о позиции
Print("Position: ", PositionGetInteger(POSITION_TYPE),
      " Volume: ", PositionGetDouble(POSITION_VOLUME),
      " Profit: ", PositionGetDouble(POSITION_PROFIT));

// Вывод параметров символа
Print("Point: ", _Point, " Digits: ", _Digits,
      " Spread: ", SymbolInfoInteger(_Symbol, SYMBOL_SPREAD));
```

## 📚 Дополнительные ресурсы

- [Документация MQL5](https://www.mql5.com/ru/docs)
- [Форум MQL5](https://www.mql5.com/ru/forum)
- [CodeBase MQL5](https://www.mql5.com/ru/code)

---

**Примечание:** Этот документ предназначен для программистов, желающих понять и модифицировать код робота.