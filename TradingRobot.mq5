//+------------------------------------------------------------------+
//|                                                 TradingRobot.mq5 |
//|                                  Copyright 2025, Trading Expert |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Trading Expert"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "Торговый робот на основе скользящих средних"

//--- Входные параметры
input group "=== Основные настройки ==="
input double   LotSize = 0.1;                    // Размер лота
input int      MagicNumber = 12345;               // Магический номер
input string   TradeComment = "TradingRobot";     // Комментарий к сделкам

input group "=== Параметры стратегии ==="
input int      FastMA_Period = 10;               // Период быстрой MA
input int      SlowMA_Period = 20;               // Период медленной MA
input ENUM_MA_METHOD MA_Method = MODE_EMA;       // Метод расчета MA
input ENUM_APPLIED_PRICE MA_Price = PRICE_CLOSE; // Цена для расчета MA

input group "=== Управление рисками ==="
input double   StopLoss = 50;                    // Стоп-лосс в пунктах
input double   TakeProfit = 100;                 // Тейк-профит в пунктах
input double   MaxRiskPercent = 2.0;             // Максимальный риск в %
input int      MaxOpenPositions = 1;             // Максимальное количество позиций

input group "=== Временные фильтры ==="
input int      StartHour = 9;                    // Час начала торговли
input int      EndHour = 17;                     // Час окончания торговли
input bool     TradeOnFriday = true;             // Торговать в пятницу

//--- Глобальные переменные
int fastMA_handle;
int slowMA_handle;
double fastMA[];
double slowMA[];
CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- Создание индикаторов
    fastMA_handle = iMA(_Symbol, _Period, FastMA_Period, 0, MA_Method, MA_Price);
    slowMA_handle = iMA(_Symbol, _Period, SlowMA_Period, 0, MA_Method, MA_Price);
    
    if(fastMA_handle == INVALID_HANDLE || slowMA_handle == INVALID_HANDLE)
    {
        Print("Ошибка создания индикаторов!");
        return(INIT_FAILED);
    }
    
    //--- Настройка массивов
    ArraySetAsSeries(fastMA, true);
    ArraySetAsSeries(slowMA, true);
    
    //--- Настройка торгового объекта
    trade.SetExpertMagicNumber(MagicNumber);
    trade.SetDeviationInPoints(10);
    trade.SetTypeFilling(ORDER_FILLING_FOK);
    
    Print("Торговый робот инициализирован успешно!");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    //--- Освобождение ресурсов
    if(fastMA_handle != INVALID_HANDLE)
        IndicatorRelease(fastMA_handle);
    if(slowMA_handle != INVALID_HANDLE)
        IndicatorRelease(slowMA_handle);
    
    Print("Торговый робот остановлен. Причина: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    //--- Проверка времени торговли
    if(!IsTradeTime())
        return;
    
    //--- Получение данных индикаторов
    if(!GetIndicatorData())
        return;
    
    //--- Проверка сигналов
    CheckTradingSignals();
}

//+------------------------------------------------------------------+
//| Проверка времени торговли                                        |
//+------------------------------------------------------------------+
bool IsTradeTime()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    
    //--- Проверка дня недели
    if(dt.day_of_week == 5 && !TradeOnFriday) // Пятница
        return false;
    
    //--- Проверка времени
    if(dt.hour < StartHour || dt.hour >= EndHour)
        return false;
    
    return true;
}

//+------------------------------------------------------------------+
//| Получение данных индикаторов                                     |
//+------------------------------------------------------------------+
bool GetIndicatorData()
{
    //--- Копирование данных быстрой MA
    if(CopyBuffer(fastMA_handle, 0, 0, 3, fastMA) < 3)
    {
        Print("Ошибка получения данных быстрой MA");
        return false;
    }
    
    //--- Копирование данных медленной MA
    if(CopyBuffer(slowMA_handle, 0, 0, 3, slowMA) < 3)
    {
        Print("Ошибка получения данных медленной MA");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Проверка торговых сигналов                                       |
//+------------------------------------------------------------------+
void CheckTradingSignals()
{
    //--- Проверка максимального количества позиций
    if(CountOpenPositions() >= MaxOpenPositions)
        return;
    
    //--- Сигнал на покупку: быстрая MA пересекает медленную снизу вверх
    if(fastMA[1] > slowMA[1] && fastMA[2] <= slowMA[2])
    {
        OpenBuyPosition();
    }
    //--- Сигнал на продажу: быстрая MA пересекает медленную сверху вниз
    else if(fastMA[1] < slowMA[1] && fastMA[2] >= slowMA[2])
    {
        OpenSellPosition();
    }
}

//+------------------------------------------------------------------+
//| Открытие позиции на покупку                                      |
//+------------------------------------------------------------------+
void OpenBuyPosition()
{
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = 0, tp = 0;
    
    //--- Расчет стоп-лосса и тейк-профита
    if(StopLoss > 0)
        sl = ask - StopLoss * _Point;
    if(TakeProfit > 0)
        tp = ask + TakeProfit * _Point;
    
    //--- Расчет размера лота с учетом риска
    double lotSize = CalculateLotSize(ask, sl);
    
    //--- Открытие позиции
    if(trade.Buy(lotSize, _Symbol, ask, sl, tp, TradeComment))
    {
        Print("Открыта позиция BUY. Лот: ", lotSize, " SL: ", sl, " TP: ", tp);
    }
    else
    {
        Print("Ошибка открытия позиции BUY: ", trade.ResultRetcode());
    }
}

//+------------------------------------------------------------------+
//| Открытие позиции на продажу                                      |
//+------------------------------------------------------------------+
void OpenSellPosition()
{
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = 0, tp = 0;
    
    //--- Расчет стоп-лосса и тейк-профита
    if(StopLoss > 0)
        sl = bid + StopLoss * _Point;
    if(TakeProfit > 0)
        tp = bid - TakeProfit * _Point;
    
    //--- Расчет размера лота с учетом риска
    double lotSize = CalculateLotSize(bid, sl);
    
    //--- Открытие позиции
    if(trade.Sell(lotSize, _Symbol, bid, sl, tp, TradeComment))
    {
        Print("Открыта позиция SELL. Лот: ", lotSize, " SL: ", sl, " TP: ", tp);
    }
    else
    {
        Print("Ошибка открытия позиции SELL: ", trade.ResultRetcode());
    }
}

//+------------------------------------------------------------------+
//| Расчет размера лота с учетом риска                               |
//+------------------------------------------------------------------+
double CalculateLotSize(double price, double stopLoss)
{
    if(stopLoss == 0)
        return LotSize;
    
    //--- Расчет риска в валюте депозита
    double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double riskAmount = accountBalance * MaxRiskPercent / 100.0;
    
    //--- Расчет стоимости пункта
    double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    double pointValue = tickValue * _Point / tickSize;
    
    //--- Расчет размера лота
    double stopLossPoints = MathAbs(price - stopLoss) / _Point;
    double calculatedLot = riskAmount / (stopLossPoints * pointValue);
    
    //--- Проверка ограничений брокера
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
    
    calculatedLot = MathMax(calculatedLot, minLot);
    calculatedLot = MathMin(calculatedLot, maxLot);
    calculatedLot = NormalizeDouble(calculatedLot / lotStep, 0) * lotStep;
    
    return calculatedLot;
}

//+------------------------------------------------------------------+
//| Подсчет открытых позиций                                         |
//+------------------------------------------------------------------+
int CountOpenPositions()
{
    int count = 0;
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(PositionGetTicket(i) > 0)
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            {
                count++;
            }
        }
    }
    return count;
}

//+------------------------------------------------------------------+
//| Функция обработки торговых событий                               |
//+------------------------------------------------------------------+
void OnTrade()
{
    //--- Логирование торговых операций
    Print("Торговое событие: ", TimeCurrent());
}

//+------------------------------------------------------------------+