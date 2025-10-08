//+------------------------------------------------------------------+
//|                                                 TradingRobot.mq5 |
//|                                  Copyright 2025, Your Name       |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025"
#property link      ""
#property version   "1.00"
#property strict

//--- Входные параметры
input group "=== Параметры стратегии ==="
input int      FastMA_Period = 10;              // Период быстрой MA
input int      SlowMA_Period = 30;              // Период медленной MA
input ENUM_MA_METHOD MA_Method = MODE_SMA;      // Метод MA
input ENUM_APPLIED_PRICE MA_Price = PRICE_CLOSE; // Применяемая цена

input group "=== Управление рисками ==="
input double   LotSize = 0.1;                   // Размер лота
input bool     UseAutoLot = false;              // Использовать автоматический расчет лота
input double   RiskPercent = 2.0;               // Риск на сделку (%)
input int      StopLoss = 100;                  // Стоп-лосс (пункты)
input int      TakeProfit = 200;                // Тейк-профит (пункты)

input group "=== Дополнительные настройки ==="
input int      MagicNumber = 123456;            // Магический номер
input string   TradeComment = "MA Robot";       // Комментарий к сделкам
input int      Slippage = 10;                   // Проскальзывание
input bool     UseTrailingStop = false;         // Использовать трейлинг-стоп
input int      TrailingStop = 50;               // Трейлинг-стоп (пункты)
input int      TrailingStep = 10;               // Шаг трейлинга (пункты)

//--- Глобальные переменные
int handleFastMA;
int handleSlowMA;
double fastMA[];
double slowMA[];
bool isNewBar = false;
datetime lastBarTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Создание индикаторов
   handleFastMA = iMA(_Symbol, _Period, FastMA_Period, 0, MA_Method, MA_Price);
   handleSlowMA = iMA(_Symbol, _Period, SlowMA_Period, 0, MA_Method, MA_Price);
   
   if(handleFastMA == INVALID_HANDLE || handleSlowMA == INVALID_HANDLE)
   {
      Print("Ошибка создания индикаторов!");
      return(INIT_FAILED);
   }
   
   //--- Настройка массивов
   ArraySetAsSeries(fastMA, true);
   ArraySetAsSeries(slowMA, true);
   
   //--- Инициализация
   lastBarTime = iTime(_Symbol, _Period, 0);
   
   Print("Торговый робот успешно инициализирован");
   Print("Символ: ", _Symbol);
   Print("Таймфрейм: ", EnumToString(_Period));
   Print("Быстрая MA: ", FastMA_Period);
   Print("Медленная MA: ", SlowMA_Period);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //--- Освобождение индикаторов
   if(handleFastMA != INVALID_HANDLE)
      IndicatorRelease(handleFastMA);
   if(handleSlowMA != INVALID_HANDLE)
      IndicatorRelease(handleSlowMA);
   
   Print("Торговый робот остановлен. Причина: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Проверка на новый бар
   CheckNewBar();
   
   if(!isNewBar)
      return;
   
   //--- Копирование данных индикаторов
   if(CopyBuffer(handleFastMA, 0, 0, 3, fastMA) < 0)
   {
      Print("Ошибка копирования данных быстрой MA");
      return;
   }
   
   if(CopyBuffer(handleSlowMA, 0, 0, 3, slowMA) < 0)
   {
      Print("Ошибка копирования данных медленной MA");
      return;
   }
   
   //--- Трейлинг-стоп для открытых позиций
   if(UseTrailingStop)
      TrailingStopAll();
   
   //--- Проверка торговых сигналов
   int signal = GetTradeSignal();
   
   //--- Открытие позиции по сигналу
   if(signal == 1) // Сигнал на покупку
   {
      if(!IsPositionOpen())
         OpenBuy();
   }
   else if(signal == -1) // Сигнал на продажу
   {
      if(!IsPositionOpen())
         OpenSell();
   }
}

//+------------------------------------------------------------------+
//| Проверка нового бара                                             |
//+------------------------------------------------------------------+
void CheckNewBar()
{
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   
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
//| Получение торгового сигнала                                      |
//+------------------------------------------------------------------+
int GetTradeSignal()
{
   //--- Пересечение скользящих средних
   // Сигнал на покупку: быстрая MA пересекает медленную снизу вверх
   if(fastMA[1] > slowMA[1] && fastMA[2] <= slowMA[2])
   {
      Print("Сигнал на покупку! FastMA: ", fastMA[1], " SlowMA: ", slowMA[1]);
      return 1;
   }
   
   // Сигнал на продажу: быстрая MA пересекает медленную сверху вниз
   if(fastMA[1] < slowMA[1] && fastMA[2] >= slowMA[2])
   {
      Print("Сигнал на продажу! FastMA: ", fastMA[1], " SlowMA: ", slowMA[1]);
      return -1;
   }
   
   return 0;
}

//+------------------------------------------------------------------+
//| Проверка наличия открытой позиции                                |
//+------------------------------------------------------------------+
bool IsPositionOpen()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Открытие позиции на покупку                                      |
//+------------------------------------------------------------------+
void OpenBuy()
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl = 0;
   double tp = 0;
   
   //--- Расчет стоп-лосс и тейк-профит
   if(StopLoss > 0)
      sl = NormalizeDouble(ask - StopLoss * _Point, _Digits);
   
   if(TakeProfit > 0)
      tp = NormalizeDouble(ask + TakeProfit * _Point, _Digits);
   
   //--- Расчет размера лота
   double lots = CalculateLotSize(StopLoss);
   
   //--- Создание запроса
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = lots;
   request.type = ORDER_TYPE_BUY;
   request.price = ask;
   request.sl = sl;
   request.tp = tp;
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = TradeComment;
   
   //--- Отправка ордера
   if(OrderSend(request, result))
   {
      if(result.retcode == TRADE_RETCODE_DONE)
      {
         Print("Позиция BUY открыта успешно. Тикет: ", result.order, 
               " Цена: ", result.price, " Объем: ", lots);
      }
      else
      {
         Print("Ошибка открытия позиции BUY. Код: ", result.retcode, 
               " Описание: ", result.comment);
      }
   }
   else
   {
      Print("Ошибка отправки ордера BUY. Код ошибки: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Открытие позиции на продажу                                      |
//+------------------------------------------------------------------+
void OpenSell()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = 0;
   double tp = 0;
   
   //--- Расчет стоп-лосс и тейк-профит
   if(StopLoss > 0)
      sl = NormalizeDouble(bid + StopLoss * _Point, _Digits);
   
   if(TakeProfit > 0)
      tp = NormalizeDouble(bid - TakeProfit * _Point, _Digits);
   
   //--- Расчет размера лота
   double lots = CalculateLotSize(StopLoss);
   
   //--- Создание запроса
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = lots;
   request.type = ORDER_TYPE_SELL;
   request.price = bid;
   request.sl = sl;
   request.tp = tp;
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = TradeComment;
   
   //--- Отправка ордера
   if(OrderSend(request, result))
   {
      if(result.retcode == TRADE_RETCODE_DONE)
      {
         Print("Позиция SELL открыта успешно. Тикет: ", result.order, 
               " Цена: ", result.price, " Объем: ", lots);
      }
      else
      {
         Print("Ошибка открытия позиции SELL. Код: ", result.retcode, 
               " Описание: ", result.comment);
      }
   }
   else
   {
      Print("Ошибка отправки ордера SELL. Код ошибки: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Расчет размера лота                                              |
//+------------------------------------------------------------------+
double CalculateLotSize(int stopLossPips)
{
   if(!UseAutoLot || stopLossPips == 0)
      return NormalizeDouble(LotSize, 2);
   
   //--- Получение параметров счета
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * RiskPercent / 100.0;
   
   //--- Получение параметров символа
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   //--- Расчет размера лота
   double lots = riskMoney / (stopLossPips * _Point / tickSize * tickValue);
   
   //--- Нормализация размера лота
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(lots, minLot);
   lots = MathMin(lots, maxLot);
   
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
//| Трейлинг-стоп для всех позиций                                   |
//+------------------------------------------------------------------+
void TrailingStopAll()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         {
            ulong ticket = PositionGetInteger(POSITION_TICKET);
            ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            double posOpenPrice = PositionGetDouble(POSITION_PRICE_OPEN);
            double posSL = PositionGetDouble(POSITION_SL);
            
            if(posType == POSITION_TYPE_BUY)
            {
               double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
               double newSL = NormalizeDouble(bid - TrailingStop * _Point, _Digits);
               
               if(bid - posOpenPrice > TrailingStop * _Point)
               {
                  if(newSL > posSL || posSL == 0)
                  {
                     if(newSL - posSL >= TrailingStep * _Point || posSL == 0)
                        ModifyPosition(ticket, newSL, PositionGetDouble(POSITION_TP));
                  }
               }
            }
            else if(posType == POSITION_TYPE_SELL)
            {
               double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
               double newSL = NormalizeDouble(ask + TrailingStop * _Point, _Digits);
               
               if(posOpenPrice - ask > TrailingStop * _Point)
               {
                  if(newSL < posSL || posSL == 0)
                  {
                     if(posSL - newSL >= TrailingStep * _Point || posSL == 0)
                        ModifyPosition(ticket, newSL, PositionGetDouble(POSITION_TP));
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Модификация позиции                                              |
//+------------------------------------------------------------------+
bool ModifyPosition(ulong ticket, double sl, double tp)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.sl = sl;
   request.tp = tp;
   
   if(OrderSend(request, result))
   {
      if(result.retcode == TRADE_RETCODE_DONE)
      {
         Print("Позиция ", ticket, " модифицирована. SL: ", sl, " TP: ", tp);
         return true;
      }
      else
      {
         Print("Ошибка модификации позиции ", ticket, ". Код: ", result.retcode);
         return false;
      }
   }
   
   return false;
}

//+------------------------------------------------------------------+