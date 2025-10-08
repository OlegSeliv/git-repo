//+------------------------------------------------------------------+
//|                                           TrendFollowingBot.mq5 |
//|                                  Copyright 2025, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"

//--- Входные параметры
input double   LotSize = 0.1;              // Размер лота
input int      RSI_Period = 14;            // Период RSI
input int      Stoch_K_Period = 5;         // Период %K стохастика
input int      Stoch_D_Period = 3;         // Период %D стохастика
input int      Stoch_Slowing = 3;          // Замедление стохастика
input int      ATR_Period = 14;            // Период ATR
input double   ATR_Multiplier = 2.0;       // Множитель ATR для стоп-лосса
input int      MagicNumber = 123456;       // Магический номер

//--- Глобальные переменные
int rsi_handle_h4;                         // Хендл RSI на H4
int stoch_handle_m15;                      // Хендл Stochastic на M15
int atr_handle_m15;                        // Хендл ATR на M15

double rsi_buffer[];                       // Буфер RSI
double stoch_main_buffer[];                // Основной буфер стохастика
double stoch_signal_buffer[];              // Сигнальный буфер стохастика
double atr_buffer[];                       // Буфер ATR

bool long_signal_active = false;          // Флаг активного сигнала на покупку
bool short_signal_active = false;         // Флаг активного сигнала на продажу

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- Создание индикаторов
    rsi_handle_h4 = iRSI(_Symbol, PERIOD_H4, RSI_Period, PRICE_CLOSE);
    stoch_handle_m15 = iStochastic(_Symbol, PERIOD_M15, Stoch_K_Period, Stoch_D_Period, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
    atr_handle_m15 = iATR(_Symbol, PERIOD_M15, ATR_Period);
    
    //--- Проверка создания индикаторов
    if(rsi_handle_h4 == INVALID_HANDLE || stoch_handle_m15 == INVALID_HANDLE || atr_handle_m15 == INVALID_HANDLE)
    {
        Print("Ошибка создания индикаторов");
        return(INIT_FAILED);
    }
    
    //--- Настройка буферов
    ArraySetAsSeries(rsi_buffer, true);
    ArraySetAsSeries(stoch_main_buffer, true);
    ArraySetAsSeries(stoch_signal_buffer, true);
    ArraySetAsSeries(atr_buffer, true);
    
    Print("TrendFollowingBot инициализирован успешно");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    //--- Освобождение ресурсов индикаторов
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
    //--- Получение данных индикаторов
    if(!GetIndicatorData())
        return;
    
    //--- Проверка существующих позиций
    CheckExitConditions();
    
    //--- Поиск новых сигналов только если нет открытых позиций
    if(!HasOpenPosition())
    {
        CheckEntrySignals();
    }
}

//+------------------------------------------------------------------+
//| Получение данных индикаторов                                    |
//+------------------------------------------------------------------+
bool GetIndicatorData()
{
    //--- Получение RSI H4
    if(CopyBuffer(rsi_handle_h4, 0, 0, 3, rsi_buffer) < 3)
    {
        Print("Ошибка получения данных RSI H4");
        return false;
    }
    
    //--- Получение Stochastic M15
    if(CopyBuffer(stoch_handle_m15, 0, 0, 3, stoch_main_buffer) < 3 ||
       CopyBuffer(stoch_handle_m15, 1, 0, 3, stoch_signal_buffer) < 3)
    {
        Print("Ошибка получения данных Stochastic M15");
        return false;
    }
    
    //--- Получение ATR M15
    if(CopyBuffer(atr_handle_m15, 0, 0, 2, atr_buffer) < 2)
    {
        Print("Ошибка получения данных ATR M15");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Проверка сигналов входа                                         |
//+------------------------------------------------------------------+
void CheckEntrySignals()
{
    double current_rsi = rsi_buffer[0];
    double current_stoch_main = stoch_main_buffer[0];
    double prev_stoch_main = stoch_main_buffer[1];
    double prev2_stoch_main = stoch_main_buffer[2];
    
    //--- Сигнал на покупку (лонг)
    if(current_rsi > 50.0)
    {
        // Стохастик поднимается снизу вверх и закрепляется выше 25
        if(prev2_stoch_main < 25.0 && prev_stoch_main > 25.0 && current_stoch_main > 25.0 && 
           current_stoch_main > prev_stoch_main)
        {
            if(!long_signal_active)
            {
                OpenPosition(ORDER_TYPE_BUY);
                long_signal_active = true;
                short_signal_active = false;
            }
        }
    }
    //--- Сигнал на продажу (шорт)
    else if(current_rsi < 50.0)
    {
        // Стохастик опускается сверху вниз и закрепляется ниже 75
        if(prev2_stoch_main > 75.0 && prev_stoch_main < 75.0 && current_stoch_main < 75.0 && 
           current_stoch_main < prev_stoch_main)
        {
            if(!short_signal_active)
            {
                OpenPosition(ORDER_TYPE_SELL);
                short_signal_active = true;
                long_signal_active = false;
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Проверка условий выхода                                         |
//+------------------------------------------------------------------+
void CheckExitConditions()
{
    if(!HasOpenPosition())
        return;
    
    double current_stoch_main = stoch_main_buffer[0];
    
    //--- Получение информации о позиции
    if(PositionSelect(_Symbol))
    {
        long position_type = PositionGetInteger(POSITION_TYPE);
        
        //--- Выход из лонга при достижении стохастиком уровня 95
        if(position_type == POSITION_TYPE_BUY && current_stoch_main >= 95.0)
        {
            ClosePosition();
            long_signal_active = false;
        }
        //--- Выход из шорта при достижении стохастиком уровня 5
        else if(position_type == POSITION_TYPE_SELL && current_stoch_main <= 5.0)
        {
            ClosePosition();
            short_signal_active = false;
        }
    }
}

//+------------------------------------------------------------------+
//| Открытие позиции                                                |
//+------------------------------------------------------------------+
void OpenPosition(ENUM_ORDER_TYPE order_type)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    //--- Заполнение структуры запроса
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = LotSize;
    request.type = order_type;
    request.price = (order_type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    request.deviation = 3;
    request.magic = MagicNumber;
    
    //--- Расчет стоп-лосса на основе ATR
    double atr_value = atr_buffer[0];
    double stop_loss_distance = atr_value * ATR_Multiplier;
    
    if(order_type == ORDER_TYPE_BUY)
    {
        request.sl = request.price - stop_loss_distance;
    }
    else
    {
        request.sl = request.price + stop_loss_distance;
    }
    
    //--- Нормализация стоп-лосса
    request.sl = NormalizeDouble(request.sl, _Digits);
    
    //--- Отправка ордера
    if(OrderSend(request, result))
    {
        if(result.retcode == TRADE_RETCODE_DONE)
        {
            Print("Позиция открыта успешно. Тип: ", EnumToString(order_type), 
                  ", Цена: ", request.price, ", Стоп-лосс: ", request.sl);
        }
        else
        {
            Print("Ошибка открытия позиции: ", result.retcode);
        }
    }
    else
    {
        Print("Ошибка отправки ордера");
    }
}

//+------------------------------------------------------------------+
//| Закрытие позиции                                                |
//+------------------------------------------------------------------+
void ClosePosition()
{
    if(!PositionSelect(_Symbol))
        return;
    
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    //--- Заполнение структуры запроса для закрытия
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = PositionGetDouble(POSITION_VOLUME);
    request.price = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 
                    SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    request.type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
    request.position = PositionGetInteger(POSITION_TICKET);
    request.deviation = 3;
    request.magic = MagicNumber;
    
    //--- Отправка ордера на закрытие
    if(OrderSend(request, result))
    {
        if(result.retcode == TRADE_RETCODE_DONE)
        {
            Print("Позиция закрыта успешно по сигналу стохастика");
        }
        else
        {
            Print("Ошибка закрытия позиции: ", result.retcode);
        }
    }
    else
    {
        Print("Ошибка отправки ордера на закрытие");
    }
}

//+------------------------------------------------------------------+
//| Проверка наличия открытой позиции                               |
//+------------------------------------------------------------------+
bool HasOpenPosition()
{
    return PositionSelect(_Symbol);
}

//+------------------------------------------------------------------+
//| Функция обработки событий торговли                              |
//+------------------------------------------------------------------+
void OnTrade()
{
    //--- Сброс флагов при закрытии позиции
    if(!HasOpenPosition())
    {
        long_signal_active = false;
        short_signal_active = false;
    }
}