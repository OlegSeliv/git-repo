//+------------------------------------------------------------------+
//|                                            RSI_Stochastic_EA.mq5 |
//|                                  Copyright 2024, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"

//--- Входные параметры
input double   LotSize = 0.1;           // Размер лота
input int      RSI_Period = 14;         // Период RSI
input int      Stochastic_K = 5;        // Период %K стохастика
input int      Stochastic_D = 3;        // Период %D стохастика
input int      Stochastic_Slowing = 3;  // Замедление стохастика
input int      ATR_Period = 14;         // Период ATR
input double   ATR_Multiplier = 2.0;    // Множитель ATR для стоп-лосса
input int      MagicNumber = 123456;    // Магический номер
input string   Comment = "RSI_Stoch_EA"; // Комментарий к сделкам

//--- Глобальные переменные
int rsi_handle_h4;
int stoch_handle_m15;
int atr_handle_m15;
datetime last_bar_time = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- Создание хендлов индикаторов
    rsi_handle_h4 = iRSI(_Symbol, PERIOD_H4, RSI_Period, PRICE_CLOSE);
    stoch_handle_m15 = iStochastic(_Symbol, PERIOD_M15, Stochastic_K, Stochastic_D, Stochastic_Slowing, MODE_SMA, STO_LOWHIGH);
    atr_handle_m15 = iATR(_Symbol, PERIOD_M15, ATR_Period);
    
    //--- Проверка создания хендлов
    if(rsi_handle_h4 == INVALID_HANDLE)
    {
        Print("Ошибка создания RSI хендла для H4");
        return(INIT_FAILED);
    }
    
    if(stoch_handle_m15 == INVALID_HANDLE)
    {
        Print("Ошибка создания Stochastic хендла для M15");
        return(INIT_FAILED);
    }
    
    if(atr_handle_m15 == INVALID_HANDLE)
    {
        Print("Ошибка создания ATR хендла для M15");
        return(INIT_FAILED);
    }
    
    Print("Эксперт успешно инициализирован");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    //--- Освобождение хендлов
    if(rsi_handle_h4 != INVALID_HANDLE)
        IndicatorRelease(rsi_handle_h4);
    if(stoch_handle_m15 != INVALID_HANDLE)
        IndicatorRelease(stoch_handle_m15);
    if(atr_handle_m15 != INVALID_HANDLE)
        IndicatorRelease(atr_handle_m15);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    //--- Проверка нового бара
    datetime current_bar_time = iTime(_Symbol, PERIOD_M15, 0);
    if(current_bar_time == last_bar_time)
        return;
    last_bar_time = current_bar_time;
    
    //--- Получение данных индикаторов
    double rsi_h4[];
    double stoch_main[], stoch_signal[];
    double atr_m15[];
    
    ArraySetAsSeries(rsi_h4, true);
    ArraySetAsSeries(stoch_main, true);
    ArraySetAsSeries(stoch_signal, true);
    ArraySetAsSeries(atr_m15, true);
    
    //--- Копирование данных
    if(CopyBuffer(rsi_handle_h4, 0, 0, 3, rsi_h4) < 3)
        return;
    if(CopyBuffer(stoch_handle_m15, 0, 0, 3, stoch_main) < 3)
        return;
    if(CopyBuffer(stoch_handle_m15, 1, 0, 3, stoch_signal) < 3)
        return;
    if(CopyBuffer(atr_handle_m15, 0, 0, 3, atr_m15) < 3)
        return;
    
    //--- Анализ тренда по RSI на H4
    bool bullish_trend = rsi_h4[0] > 50;
    bool bearish_trend = rsi_h4[0] < 50;
    
    //--- Проверка существующих позиций
    CheckExitConditions(stoch_main, stoch_signal);
    
    //--- Поиск входов только если нет открытых позиций
    if(PositionsTotal() == 0)
    {
        if(bullish_trend)
        {
            CheckLongEntry(stoch_main, stoch_signal, atr_m15);
        }
        else if(bearish_trend)
        {
            CheckShortEntry(stoch_main, stoch_signal, atr_m15);
        }
    }
}

//+------------------------------------------------------------------+
//| Проверка условий входа в лонг                                   |
//+------------------------------------------------------------------+
void CheckLongEntry(double &stoch_main[], double &stoch_signal[], double &atr_m15[])
{
    //--- Условие: стохастик поднимается снизу вверх и закрепляется выше 25
    bool stoch_rising = stoch_main[1] < stoch_main[0]; // Текущий выше предыдущего
    bool stoch_above_25 = stoch_main[0] > 25;
    bool stoch_was_below_25 = stoch_main[1] <= 25; // Предыдущий был ниже или равен 25
    
    if(stoch_rising && stoch_above_25 && stoch_was_below_25)
    {
        OpenLongPosition(atr_m15[0]);
    }
}

//+------------------------------------------------------------------+
//| Проверка условий входа в шорт                                   |
//+------------------------------------------------------------------+
void CheckShortEntry(double &stoch_main[], double &stoch_signal[], double &atr_m15[])
{
    //--- Условие: стохастик опускается сверху вниз и закрепляется ниже 75
    bool stoch_falling = stoch_main[1] > stoch_main[0]; // Текущий ниже предыдущего
    bool stoch_below_75 = stoch_main[0] < 75;
    bool stoch_was_above_75 = stoch_main[1] >= 75; // Предыдущий был выше или равен 75
    
    if(stoch_falling && stoch_below_75 && stoch_was_above_75)
    {
        OpenShortPosition(atr_m15[0]);
    }
}

//+------------------------------------------------------------------+
//| Открытие лонг позиции                                            |
//+------------------------------------------------------------------+
void OpenLongPosition(double atr_value)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = ask - (atr_value * ATR_Multiplier);
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = LotSize;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.magic = MagicNumber;
    request.comment = Comment;
    
    if(OrderSend(request, result))
    {
        Print("Лонг позиция открыта. Тикет: ", result.order);
    }
    else
    {
        Print("Ошибка открытия лонг позиции: ", result.retcode);
    }
}

//+------------------------------------------------------------------+
//| Открытие шорт позиции                                            |
//+------------------------------------------------------------------+
void OpenShortPosition(double atr_value)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = bid + (atr_value * ATR_Multiplier);
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = LotSize;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.magic = MagicNumber;
    request.comment = Comment;
    
    if(OrderSend(request, result))
    {
        Print("Шорт позиция открыта. Тикет: ", result.order);
    }
    else
    {
        Print("Ошибка открытия шорт позиции: ", result.retcode);
    }
}

//+------------------------------------------------------------------+
//| Проверка условий выхода из позиций                              |
//+------------------------------------------------------------------+
void CheckExitConditions(double &stoch_main[], double &stoch_signal[])
{
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
        {
            ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            
            if(pos_type == POSITION_TYPE_BUY)
            {
                //--- Выход из лонга при достижении стохастиком уровня 95
                if(stoch_main[0] >= 95)
                {
                    ClosePosition(i);
                }
            }
            else if(pos_type == POSITION_TYPE_SELL)
            {
                //--- Выход из шорта при достижении стохастиком уровня 5
                if(stoch_main[0] <= 5)
                {
                    ClosePosition(i);
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Закрытие позиции                                                |
//+------------------------------------------------------------------+
void ClosePosition(int pos_index)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    ulong ticket = PositionGetTicket(pos_index);
    ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = PositionGetDouble(POSITION_VOLUME);
    request.type = (pos_type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
    request.position = ticket;
    request.magic = MagicNumber;
    request.comment = Comment + "_Close";
    
    if(pos_type == POSITION_TYPE_BUY)
        request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    else
        request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    
    if(OrderSend(request, result))
    {
        Print("Позиция закрыта. Тикет: ", ticket);
    }
    else
    {
        Print("Ошибка закрытия позиции: ", result.retcode);
    }
}

//+------------------------------------------------------------------+