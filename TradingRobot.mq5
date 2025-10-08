//+------------------------------------------------------------------+
//|                                                 TradingRobot.mq5 |
//|                                                                  |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Trading Robot"
#property link      ""
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

// Входные параметры
input double LotSize = 0.1;                    // Размер лота
input int RSI_Period = 14;                     // Период RSI
input ENUM_APPLIED_PRICE RSI_AppliedPrice = PRICE_CLOSE; // Цена для RSI
input int Stochastic_K = 5;                    // Период %K стохастика
input int Stochastic_D = 3;                    // Период %D стохастика
input int Stochastic_Slowing = 3;              // Замедление стохастика
input int ATR_Period = 14;                     // Период ATR
input double ATR_Multiplier = 2.0;             // Множитель ATR для стоп-лосса
input int Magic = 123456;                      // Магический номер

// Глобальные переменные
CTrade trade;
int handleRSI_H4;
int handleStoch_M15;
int handleATR_M15;

bool lastStochWasBelow25 = false;  // Для отслеживания перехода стохастика через 25 снизу вверх
bool lastStochWasAbove75 = false;  // Для отслеживания перехода стохастика через 75 сверху вниз

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    // Инициализация торгового объекта
    trade.SetExpertMagicNumber(Magic);
    trade.SetDeviationInPoints(10);
    trade.SetTypeFilling(ORDER_FILLING_IOC);
    
    // Проверяем доступность ORDER_FILLING_FOK, если IOC не работает
    if(!trade.SetTypeFilling(ORDER_FILLING_IOC))
    {
        trade.SetTypeFilling(ORDER_FILLING_FOK);
    }
    if(!trade.SetTypeFilling(ORDER_FILLING_FOK))
    {
        trade.SetTypeFilling(ORDER_FILLING_RETURN);
    }
    
    // Создаем индикаторы
    handleRSI_H4 = iRSI(_Symbol, PERIOD_H4, RSI_Period, RSI_AppliedPrice);
    if(handleRSI_H4 == INVALID_HANDLE)
    {
        Print("Ошибка создания индикатора RSI H4");
        return(INIT_FAILED);
    }
    
    handleStoch_M15 = iStochastic(_Symbol, PERIOD_M15, Stochastic_K, Stochastic_D, 
                                   Stochastic_Slowing, MODE_SMA, STO_LOWHIGH);
    if(handleStoch_M15 == INVALID_HANDLE)
    {
        Print("Ошибка создания индикатора Stochastic M15");
        return(INIT_FAILED);
    }
    
    handleATR_M15 = iATR(_Symbol, PERIOD_M15, ATR_Period);
    if(handleATR_M15 == INVALID_HANDLE)
    {
        Print("Ошибка создания индикатора ATR M15");
        return(INIT_FAILED);
    }
    
    Print("TradingRobot инициализирован успешно");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Освобождаем индикаторы
    if(handleRSI_H4 != INVALID_HANDLE)
        IndicatorRelease(handleRSI_H4);
    if(handleStoch_M15 != INVALID_HANDLE)
        IndicatorRelease(handleStoch_M15);
    if(handleATR_M15 != INVALID_HANDLE)
        IndicatorRelease(handleATR_M15);
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
    // Проверяем, есть ли открытые позиции
    bool hasPosition = HasOpenPosition();
    
    if(hasPosition)
    {
        // Проверяем условия выхода
        CheckExitConditions();
    }
    else
    {
        // Проверяем условия входа
        CheckEntryConditions();
    }
}

//+------------------------------------------------------------------+
//| Проверка наличия открытых позиций                                 |
//+------------------------------------------------------------------+
bool HasOpenPosition()
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionGetSymbol(i) == _Symbol)
        {
            if(PositionGetInteger(POSITION_MAGIC) == Magic)
            {
                return true;
            }
        }
    }
    return false;
}

//+------------------------------------------------------------------+
//| Получение значения RSI на H4                                      |
//+------------------------------------------------------------------+
double GetRSI_H4()
{
    double rsi[];
    ArraySetAsSeries(rsi, true);
    
    if(CopyBuffer(handleRSI_H4, 0, 0, 2, rsi) <= 0)
    {
        Print("Ошибка копирования данных RSI");
        return -1;
    }
    
    return rsi[0];
}

//+------------------------------------------------------------------+
//| Получение значений стохастика на M15                              |
//+------------------------------------------------------------------+
bool GetStochastic_M15(double &mainLine[], double &signalLine[])
{
    ArraySetAsSeries(mainLine, true);
    ArraySetAsSeries(signalLine, true);
    
    if(CopyBuffer(handleStoch_M15, 0, 0, 3, mainLine) <= 0)
    {
        Print("Ошибка копирования данных Stochastic Main");
        return false;
    }
    
    if(CopyBuffer(handleStoch_M15, 1, 0, 3, signalLine) <= 0)
    {
        Print("Ошибка копирования данных Stochastic Signal");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Получение значения ATR на M15                                     |
//+------------------------------------------------------------------+
double GetATR_M15()
{
    double atr[];
    ArraySetAsSeries(atr, true);
    
    if(CopyBuffer(handleATR_M15, 0, 0, 2, atr) <= 0)
    {
        Print("Ошибка копирования данных ATR");
        return -1;
    }
    
    return atr[0];
}

//+------------------------------------------------------------------+
//| Проверка условий входа                                            |
//+------------------------------------------------------------------+
void CheckEntryConditions()
{
    // Получаем RSI на H4
    double rsi_h4 = GetRSI_H4();
    if(rsi_h4 < 0)
        return;
    
    // Получаем стохастик на M15
    double stochMain[], stochSignal[];
    if(!GetStochastic_M15(stochMain, stochSignal))
        return;
    
    // Определяем направление тренда
    bool trendIsUp = (rsi_h4 > 50);
    bool trendIsDown = (rsi_h4 < 50);
    
    // Проверяем условия для лонга
    if(trendIsUp)
    {
        // Проверяем, был ли стохастик ниже 25 на предыдущем баре
        if(stochMain[1] < 25)
        {
            lastStochWasBelow25 = true;
        }
        
        // Проверяем, закрепился ли стохастик выше 25
        if(lastStochWasBelow25 && stochMain[0] > 25 && stochMain[0] > stochMain[1])
        {
            // Условия для входа в лонг выполнены
            OpenLongPosition();
            lastStochWasBelow25 = false;
        }
    }
    
    // Проверяем условия для шорта
    if(trendIsDown)
    {
        // Проверяем, был ли стохастик выше 75 на предыдущем баре
        if(stochMain[1] > 75)
        {
            lastStochWasAbove75 = true;
        }
        
        // Проверяем, закрепился ли стохастик ниже 75
        if(lastStochWasAbove75 && stochMain[0] < 75 && stochMain[0] < stochMain[1])
        {
            // Условия для входа в шорт выполнены
            OpenShortPosition();
            lastStochWasAbove75 = false;
        }
    }
}

//+------------------------------------------------------------------+
//| Открытие длинной позиции                                          |
//+------------------------------------------------------------------+
void OpenLongPosition()
{
    double atr = GetATR_M15();
    if(atr < 0)
        return;
    
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = ask - (atr * ATR_Multiplier);
    
    // Нормализуем стоп-лосс
    sl = NormalizeDouble(sl, _Digits);
    
    Print("Открытие LONG позиции. Ask: ", ask, " SL: ", sl, " ATR: ", atr);
    
    if(!trade.Buy(LotSize, _Symbol, ask, sl, 0, "Long Entry"))
    {
        Print("Ошибка открытия LONG позиции: ", trade.ResultRetcode());
    }
    else
    {
        Print("LONG позиция открыта успешно");
    }
}

//+------------------------------------------------------------------+
//| Открытие короткой позиции                                         |
//+------------------------------------------------------------------+
void OpenShortPosition()
{
    double atr = GetATR_M15();
    if(atr < 0)
        return;
    
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = bid + (atr * ATR_Multiplier);
    
    // Нормализуем стоп-лосс
    sl = NormalizeDouble(sl, _Digits);
    
    Print("Открытие SHORT позиции. Bid: ", bid, " SL: ", sl, " ATR: ", atr);
    
    if(!trade.Sell(LotSize, _Symbol, bid, sl, 0, "Short Entry"))
    {
        Print("Ошибка открытия SHORT позиции: ", trade.ResultRetcode());
    }
    else
    {
        Print("SHORT позиция открыта успешно");
    }
}

//+------------------------------------------------------------------+
//| Проверка условий выхода                                           |
//+------------------------------------------------------------------+
void CheckExitConditions()
{
    // Получаем стохастик на M15
    double stochMain[], stochSignal[];
    if(!GetStochastic_M15(stochMain, stochSignal))
        return;
    
    // Проверяем все позиции
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionGetSymbol(i) == _Symbol)
        {
            if(PositionGetInteger(POSITION_MAGIC) == Magic)
            {
                ulong ticket = PositionGetInteger(POSITION_TICKET);
                ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
                
                // Проверяем условия выхода для лонга
                if(posType == POSITION_TYPE_BUY && stochMain[0] >= 95)
                {
                    Print("Закрытие LONG позиции. Stochastic достиг 95: ", stochMain[0]);
                    if(!trade.PositionClose(ticket))
                    {
                        Print("Ошибка закрытия LONG позиции: ", trade.ResultRetcode());
                    }
                    else
                    {
                        Print("LONG позиция закрыта успешно");
                        lastStochWasBelow25 = false;
                    }
                }
                
                // Проверяем условия выхода для шорта
                if(posType == POSITION_TYPE_SELL && stochMain[0] <= 5)
                {
                    Print("Закрытие SHORT позиции. Stochastic достиг 5: ", stochMain[0]);
                    if(!trade.PositionClose(ticket))
                    {
                        Print("Ошибка закрытия SHORT позиции: ", trade.ResultRetcode());
                    }
                    else
                    {
                        Print("SHORT позиция закрыта успешно");
                        lastStochWasAbove75 = false;
                    }
                }
            }
        }
    }
}
//+------------------------------------------------------------------+