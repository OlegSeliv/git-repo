//+------------------------------------------------------------------+
//|                                              TradingRobot_MT5.mq5|
//|                                    Copyright 2025, Trading Robot |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Trading Robot"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "Торговый робот для MT5 с стратегией на основе скользящих средних"

// Подключаем необходимые библиотеки
#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

//--- Входные параметры робота
input group "=== Основные настройки ==="
input double   InpLotSize          = 0.01;      // Размер лота
input int      InpMagicNumber      = 123456;    // Magic Number
input string   InpComment          = "MA Robot"; // Комментарий к сделкам

input group "=== Параметры стратегии ==="
input int      InpFastMA           = 10;        // Период быстрой MA
input int      InpSlowMA           = 30;        // Период медленной MA
input ENUM_MA_METHOD InpMAMethod   = MODE_SMA;  // Метод расчета MA
input ENUM_APPLIED_PRICE InpMAPrice = PRICE_CLOSE; // Цена для расчета MA

input group "=== Управление рисками ==="
input double   InpStopLoss         = 50;        // Stop Loss (в пунктах, 0 = без SL)
input double   InpTakeProfit       = 100;       // Take Profit (в пунктах, 0 = без TP)
input double   InpTrailingStop     = 30;        // Trailing Stop (в пунктах, 0 = отключен)
input double   InpMaxRiskPercent   = 2.0;       // Максимальный риск на сделку (%)
input int      InpMaxPositions     = 1;         // Максимум открытых позиций

input group "=== Временные настройки ==="
input bool     InpUseTimeFilter    = false;     // Использовать временной фильтр
input int      InpStartHour        = 9;         // Час начала торговли
input int      InpStartMinute      = 0;         // Минута начала торговли
input int      InpEndHour          = 22;        // Час окончания торговли
input int      InpEndMinute        = 0;         // Минута окончания торговли

//--- Глобальные переменные
CTrade         trade;
CSymbolInfo    symbolInfo;
CPositionInfo  positionInfo;
CAccountInfo   accountInfo;

int            handleFastMA;
int            handleSlowMA;
double         fastMABuffer[];
double         slowMABuffer[];

double         stopLossPoints;
double         takeProfitPoints;
double         trailingStopPoints;

datetime       lastBarTime = 0;
bool           isNewBar = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Инициализация символа
   if(!symbolInfo.Name(_Symbol))
   {
      Print("Ошибка инициализации символа!");
      return(INIT_FAILED);
   }
   symbolInfo.Refresh();
   
   //--- Настройка торгового класса
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetMarginMode();
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(10);
   
   //--- Создание индикаторов
   handleFastMA = iMA(_Symbol, PERIOD_CURRENT, InpFastMA, 0, InpMAMethod, InpMAPrice);
   handleSlowMA = iMA(_Symbol, PERIOD_CURRENT, InpSlowMA, 0, InpMAMethod, InpMAPrice);
   
   if(handleFastMA == INVALID_HANDLE || handleSlowMA == INVALID_HANDLE)
   {
      Print("Ошибка создания индикаторов MA!");
      return(INIT_FAILED);
   }
   
   //--- Настройка буферов индикаторов
   ArraySetAsSeries(fastMABuffer, true);
   ArraySetAsSeries(slowMABuffer, true);
   
   //--- Расчет пунктов для SL/TP/Trailing
   double point = symbolInfo.Point();
   stopLossPoints = InpStopLoss * point;
   takeProfitPoints = InpTakeProfit * point;
   trailingStopPoints = InpTrailingStop * point;
   
   //--- Вывод информации о запуске
   Print("====================================");
   Print("Торговый робот успешно запущен!");
   Print("Символ: ", _Symbol);
   Print("Таймфрейм: ", EnumToString(Period()));
   Print("Magic Number: ", InpMagicNumber);
   Print("Быстрая MA: ", InpFastMA);
   Print("Медленная MA: ", InpSlowMA);
   Print("====================================");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //--- Освобождение ресурсов индикаторов
   if(handleFastMA != INVALID_HANDLE)
      IndicatorRelease(handleFastMA);
   if(handleSlowMA != INVALID_HANDLE)
      IndicatorRelease(handleSlowMA);
      
   //--- Вывод причины деинициализации
   Print("Робот остановлен. Причина: ", GetDeinitialisationReason(reason));
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Проверка нового бара
   CheckNewBar();
   
   //--- Обновление информации о символе
   if(!symbolInfo.RefreshRates())
   {
      Print("Ошибка обновления котировок!");
      return;
   }
   
   //--- Проверка временного фильтра
   if(InpUseTimeFilter && !IsTimeToTrade())
      return;
   
   //--- Трейлинг стоп для открытых позиций
   if(InpTrailingStop > 0)
      TrailingStop();
   
   //--- Торговые операции только на новом баре
   if(!isNewBar)
      return;
   
   //--- Получение данных индикаторов
   if(!GetIndicatorData())
      return;
   
   //--- Проверка торговых сигналов
   CheckTradingSignals();
}

//+------------------------------------------------------------------+
//| Проверка нового бара                                            |
//+------------------------------------------------------------------+
void CheckNewBar()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   
   if(currentBarTime != lastBarTime)
   {
      lastBarTime = currentBarTime;
      isNewBar = true;
   }
   else
   {
      isNewBar = false;
   }
}

//+------------------------------------------------------------------+
//| Получение данных индикаторов                                    |
//+------------------------------------------------------------------+
bool GetIndicatorData()
{
   //--- Копирование данных быстрой MA
   if(CopyBuffer(handleFastMA, 0, 0, 3, fastMABuffer) != 3)
   {
      Print("Ошибка копирования данных быстрой MA!");
      return false;
   }
   
   //--- Копирование данных медленной MA
   if(CopyBuffer(handleSlowMA, 0, 0, 3, slowMABuffer) != 3)
   {
      Print("Ошибка копирования данных медленной MA!");
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Проверка торговых сигналов                                      |
//+------------------------------------------------------------------+
void CheckTradingSignals()
{
   //--- Проверка количества открытых позиций
   int positionsCount = CountPositions();
   if(positionsCount >= InpMaxPositions)
      return;
   
   //--- Определение направления тренда
   bool bullishCross = (fastMABuffer[2] <= slowMABuffer[2] && fastMABuffer[1] > slowMABuffer[1]);
   bool bearishCross = (fastMABuffer[2] >= slowMABuffer[2] && fastMABuffer[1] < slowMABuffer[1]);
   
   //--- Сигнал на покупку
   if(bullishCross)
   {
      //--- Закрытие продаж, если есть
      ClosePositions(POSITION_TYPE_SELL);
      
      //--- Открытие покупки
      OpenPosition(ORDER_TYPE_BUY);
   }
   //--- Сигнал на продажу
   else if(bearishCross)
   {
      //--- Закрытие покупок, если есть
      ClosePositions(POSITION_TYPE_BUY);
      
      //--- Открытие продажи
      OpenPosition(ORDER_TYPE_SELL);
   }
}

//+------------------------------------------------------------------+
//| Открытие позиции                                                |
//+------------------------------------------------------------------+
void OpenPosition(ENUM_ORDER_TYPE orderType)
{
   //--- Расчет размера лота с учетом риска
   double lotSize = CalculateLotSize();
   if(lotSize <= 0)
      return;
   
   //--- Определение цены открытия
   double price = (orderType == ORDER_TYPE_BUY) ? symbolInfo.Ask() : symbolInfo.Bid();
   
   //--- Расчет SL и TP
   double sl = 0, tp = 0;
   
   if(orderType == ORDER_TYPE_BUY)
   {
      if(InpStopLoss > 0)
         sl = price - stopLossPoints;
      if(InpTakeProfit > 0)
         tp = price + takeProfitPoints;
   }
   else
   {
      if(InpStopLoss > 0)
         sl = price + stopLossPoints;
      if(InpTakeProfit > 0)
         tp = price - takeProfitPoints;
   }
   
   //--- Нормализация цен
   sl = NormalizeDouble(sl, symbolInfo.Digits());
   tp = NormalizeDouble(tp, symbolInfo.Digits());
   
   //--- Открытие позиции
   bool result = false;
   
   if(orderType == ORDER_TYPE_BUY)
   {
      result = trade.Buy(lotSize, _Symbol, price, sl, tp, InpComment);
   }
   else
   {
      result = trade.Sell(lotSize, _Symbol, price, sl, tp, InpComment);
   }
   
   //--- Проверка результата
   if(result)
   {
      string orderTypeStr = (orderType == ORDER_TYPE_BUY) ? "BUY" : "SELL";
      Print("Открыта позиция ", orderTypeStr, " объемом ", lotSize, " по цене ", price);
      
      if(trade.ResultRetcode() != TRADE_RETCODE_DONE)
      {
         Print("Предупреждение: RetCode = ", trade.ResultRetcode(), ", ", trade.ResultRetcodeDescription());
      }
   }
   else
   {
      Print("Ошибка открытия позиции: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Расчет размера лота с учетом риска                              |
//+------------------------------------------------------------------+
double CalculateLotSize()
{
   double lotSize = InpLotSize;
   
   //--- Если используется управление рисками
   if(InpMaxRiskPercent > 0 && InpStopLoss > 0)
   {
      accountInfo.Refresh();
      double balance = accountInfo.Balance();
      double riskAmount = balance * InpMaxRiskPercent / 100.0;
      
      //--- Расчет размера лота на основе риска
      double tickValue = symbolInfo.TickValue();
      if(tickValue > 0)
      {
         double stopLossPips = InpStopLoss;
         lotSize = riskAmount / (stopLossPips * tickValue);
      }
   }
   
   //--- Нормализация размера лота
   double minLot = symbolInfo.LotsMin();
   double maxLot = symbolInfo.LotsMax();
   double stepLot = symbolInfo.LotsStep();
   
   lotSize = MathMax(minLot, lotSize);
   lotSize = MathMin(maxLot, lotSize);
   lotSize = MathRound(lotSize / stepLot) * stepLot;
   
   return NormalizeDouble(lotSize, 2);
}

//+------------------------------------------------------------------+
//| Закрытие позиций по типу                                        |
//+------------------------------------------------------------------+
void ClosePositions(ENUM_POSITION_TYPE positionType)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(positionInfo.SelectByIndex(i))
      {
         if(positionInfo.Symbol() == _Symbol && 
            positionInfo.Magic() == InpMagicNumber &&
            positionInfo.PositionType() == positionType)
         {
            if(trade.PositionClose(positionInfo.Ticket()))
            {
               Print("Закрыта позиция #", positionInfo.Ticket());
            }
            else
            {
               Print("Ошибка закрытия позиции #", positionInfo.Ticket(), ": ", trade.ResultRetcodeDescription());
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Подсчет открытых позиций                                        |
//+------------------------------------------------------------------+
int CountPositions()
{
   int count = 0;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(positionInfo.SelectByIndex(i))
      {
         if(positionInfo.Symbol() == _Symbol && positionInfo.Magic() == InpMagicNumber)
         {
            count++;
         }
      }
   }
   
   return count;
}

//+------------------------------------------------------------------+
//| Трейлинг стоп                                                   |
//+------------------------------------------------------------------+
void TrailingStop()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!positionInfo.SelectByIndex(i))
         continue;
         
      if(positionInfo.Symbol() != _Symbol || positionInfo.Magic() != InpMagicNumber)
         continue;
      
      double currentPrice = 0;
      double currentSL = positionInfo.StopLoss();
      double openPrice = positionInfo.PriceOpen();
      ulong ticket = positionInfo.Ticket();
      
      if(positionInfo.PositionType() == POSITION_TYPE_BUY)
      {
         currentPrice = symbolInfo.Bid();
         
         //--- Проверка условий для трейлинга покупки
         if(currentPrice - openPrice > trailingStopPoints)
         {
            double newSL = currentPrice - trailingStopPoints;
            newSL = NormalizeDouble(newSL, symbolInfo.Digits());
            
            if(newSL > currentSL)
            {
               if(trade.PositionModify(ticket, newSL, positionInfo.TakeProfit()))
               {
                  Print("Trailing Stop обновлен для BUY #", ticket, ", новый SL: ", newSL);
               }
            }
         }
      }
      else if(positionInfo.PositionType() == POSITION_TYPE_SELL)
      {
         currentPrice = symbolInfo.Ask();
         
         //--- Проверка условий для трейлинга продажи
         if(openPrice - currentPrice > trailingStopPoints)
         {
            double newSL = currentPrice + trailingStopPoints;
            newSL = NormalizeDouble(newSL, symbolInfo.Digits());
            
            if(newSL < currentSL || currentSL == 0)
            {
               if(trade.PositionModify(ticket, newSL, positionInfo.TakeProfit()))
               {
                  Print("Trailing Stop обновлен для SELL #", ticket, ", новый SL: ", newSL);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Проверка времени торговли                                       |
//+------------------------------------------------------------------+
bool IsTimeToTrade()
{
   MqlDateTime currentTime;
   TimeToStruct(TimeCurrent(), currentTime);
   
   int currentMinutes = currentTime.hour * 60 + currentTime.min;
   int startMinutes = InpStartHour * 60 + InpStartMinute;
   int endMinutes = InpEndHour * 60 + InpEndMinute;
   
   //--- Если торговля в пределах одного дня
   if(startMinutes < endMinutes)
   {
      return (currentMinutes >= startMinutes && currentMinutes < endMinutes);
   }
   //--- Если торговля переходит через полночь
   else
   {
      return (currentMinutes >= startMinutes || currentMinutes < endMinutes);
   }
}

//+------------------------------------------------------------------+
//| Получение описания причины деинициализации                      |
//+------------------------------------------------------------------+
string GetDeinitialisationReason(int reason)
{
   switch(reason)
   {
      case REASON_PROGRAM:     return "Эксперт остановлен командой";
      case REASON_REMOVE:      return "Эксперт удален с графика";
      case REASON_RECOMPILE:   return "Эксперт перекомпилирован";
      case REASON_CHARTCHANGE: return "Символ или период графика изменен";
      case REASON_CHARTCLOSE:  return "График закрыт";
      case REASON_PARAMETERS:  return "Параметры изменены";
      case REASON_ACCOUNT:     return "Другой счет активирован";
      default:                 return "Неизвестная причина";
   }
}

//+------------------------------------------------------------------+
//| Обработчик события Trade                                        |
//+------------------------------------------------------------------+
void OnTrade()
{
   //--- Можно добавить обработку торговых событий
}

//+------------------------------------------------------------------+
//| Обработчик события Timer                                        |
//+------------------------------------------------------------------+
void OnTimer()
{
   //--- Можно добавить периодические проверки
}

//+------------------------------------------------------------------+