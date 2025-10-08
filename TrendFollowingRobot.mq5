//+------------------------------------------------------------------+
//|                                         TrendFollowingRobot.mq5 |
//|                                             Trading Robot MT5   |
//|                                                                  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025"
#property link      ""
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input parameters
input double   LotSize = 0.1;           // Размер лота
input int      RSI_Period = 14;         // Период RSI
input int      Stochastic_K = 5;        // Период %K стохастика
input int      Stochastic_D = 3;        // Период %D стохастика
input int      Stochastic_Slowing = 3;  // Замедление стохастика
input int      ATR_Period = 14;         // Период ATR
input int      MagicNumber = 123456;    // Магический номер

//--- Global variables
CTrade trade;
CPositionInfo position;

//--- Indicator handles
int handle_RSI_H4;
int handle_Stochastic_M15;
int handle_ATR_M15;

//--- Buffers for indicator values
double RSI_Buffer[];
double Stochastic_Main[];
double Stochastic_Signal[];
double ATR_Buffer[];

//--- Previous values for tracking crosses
double prev_stoch_main = 0;
double prev_stoch_signal = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Set magic number for trade operations
   trade.SetExpertMagicNumber(MagicNumber);
   
   //--- Initialize RSI on H4 timeframe
   handle_RSI_H4 = iRSI(_Symbol, PERIOD_H4, RSI_Period, PRICE_CLOSE);
   if(handle_RSI_H4 == INVALID_HANDLE)
   {
      Print("Ошибка создания индикатора RSI на H4");
      return(INIT_FAILED);
   }
   
   //--- Initialize Stochastic on M15 timeframe
   handle_Stochastic_M15 = iStochastic(_Symbol, PERIOD_M15, 
                                        Stochastic_K, Stochastic_D, Stochastic_Slowing,
                                        MODE_SMA, STO_LOWHIGH);
   if(handle_Stochastic_M15 == INVALID_HANDLE)
   {
      Print("Ошибка создания индикатора Stochastic на M15");
      return(INIT_FAILED);
   }
   
   //--- Initialize ATR on M15 timeframe
   handle_ATR_M15 = iATR(_Symbol, PERIOD_M15, ATR_Period);
   if(handle_ATR_M15 == INVALID_HANDLE)
   {
      Print("Ошибка создания индикатора ATR на M15");
      return(INIT_FAILED);
   }
   
   //--- Set arrays as series
   ArraySetAsSeries(RSI_Buffer, true);
   ArraySetAsSeries(Stochastic_Main, true);
   ArraySetAsSeries(Stochastic_Signal, true);
   ArraySetAsSeries(ATR_Buffer, true);
   
   Print("Робот успешно инициализирован");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   //--- Release indicator handles
   if(handle_RSI_H4 != INVALID_HANDLE)
      IndicatorRelease(handle_RSI_H4);
   if(handle_Stochastic_M15 != INVALID_HANDLE)
      IndicatorRelease(handle_Stochastic_M15);
   if(handle_ATR_M15 != INVALID_HANDLE)
      IndicatorRelease(handle_ATR_M15);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Check if we are on M15 timeframe or higher
   if(Period() > PERIOD_M15)
   {
      Comment("Робот работает только на таймфрейме M15 или ниже");
      return;
   }
   
   //--- Get indicator values
   if(!GetIndicatorValues())
      return;
   
   //--- Check for exit conditions first
   CheckExitConditions();
   
   //--- Check if we already have an open position
   bool hasPosition = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(position.SelectByIndex(i))
      {
         if(position.Symbol() == _Symbol && position.Magic() == MagicNumber)
         {
            hasPosition = true;
            break;
         }
      }
   }
   
   //--- If no position, check for entry signals
   if(!hasPosition)
   {
      CheckEntrySignals();
   }
   
   //--- Update previous stochastic values
   prev_stoch_main = Stochastic_Main[0];
   prev_stoch_signal = Stochastic_Signal[0];
}

//+------------------------------------------------------------------+
//| Get indicator values                                             |
//+------------------------------------------------------------------+
bool GetIndicatorValues()
{
   //--- Copy RSI values from H4
   if(CopyBuffer(handle_RSI_H4, 0, 0, 2, RSI_Buffer) <= 0)
   {
      Print("Ошибка копирования данных RSI");
      return false;
   }
   
   //--- Copy Stochastic values from M15
   if(CopyBuffer(handle_Stochastic_M15, 0, 0, 3, Stochastic_Main) <= 0)
   {
      Print("Ошибка копирования данных Stochastic Main");
      return false;
   }
   
   if(CopyBuffer(handle_Stochastic_M15, 1, 0, 3, Stochastic_Signal) <= 0)
   {
      Print("Ошибка копирования данных Stochastic Signal");
      return false;
   }
   
   //--- Copy ATR values from M15
   if(CopyBuffer(handle_ATR_M15, 0, 0, 2, ATR_Buffer) <= 0)
   {
      Print("Ошибка копирования данных ATR");
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Check entry signals                                              |
//+------------------------------------------------------------------+
void CheckEntrySignals()
{
   double rsi_value = RSI_Buffer[0];
   double stoch_current = Stochastic_Main[0];
   double stoch_prev = Stochastic_Main[1];
   
   //--- Check for LONG entry
   if(rsi_value > 50) // RSI на H4 выше 50
   {
      // Проверяем, что стохастик поднимается снизу вверх и закрепляется выше 25
      if(stoch_prev <= 25 && stoch_current > 25 && stoch_current > stoch_prev)
      {
         // Дополнительная проверка на устойчивость сигнала
         if(Stochastic_Main[2] < stoch_prev) // Подтверждение восходящего движения
         {
            OpenLongPosition();
         }
      }
   }
   
   //--- Check for SHORT entry
   if(rsi_value < 50) // RSI на H4 ниже 50
   {
      // Проверяем, что стохастик опускается сверху вниз и закрепляется ниже 75
      if(stoch_prev >= 75 && stoch_current < 75 && stoch_current < stoch_prev)
      {
         // Дополнительная проверка на устойчивость сигнала
         if(Stochastic_Main[2] > stoch_prev) // Подтверждение нисходящего движения
         {
            OpenShortPosition();
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Open long position                                               |
//+------------------------------------------------------------------+
void OpenLongPosition()
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double atr = ATR_Buffer[0];
   
   //--- Calculate stop loss (2 ATR below entry)
   double stopLoss = NormalizeDouble(ask - 2 * atr, _Digits);
   
   //--- No take profit - exit by stochastic signal
   double takeProfit = 0;
   
   //--- Open buy position
   if(trade.Buy(LotSize, _Symbol, ask, stopLoss, takeProfit, "Long by RSI+Stoch"))
   {
      Print("Открыта длинная позиция: Price=", ask, " SL=", stopLoss);
   }
   else
   {
      Print("Ошибка открытия длинной позиции: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Open short position                                              |
//+------------------------------------------------------------------+
void OpenShortPosition()
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double atr = ATR_Buffer[0];
   
   //--- Calculate stop loss (2 ATR above entry)
   double stopLoss = NormalizeDouble(bid + 2 * atr, _Digits);
   
   //--- No take profit - exit by stochastic signal
   double takeProfit = 0;
   
   //--- Open sell position
   if(trade.Sell(LotSize, _Symbol, bid, stopLoss, takeProfit, "Short by RSI+Stoch"))
   {
      Print("Открыта короткая позиция: Price=", bid, " SL=", stopLoss);
   }
   else
   {
      Print("Ошибка открытия короткой позиции: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Check exit conditions                                            |
//+------------------------------------------------------------------+
void CheckExitConditions()
{
   double stoch_current = Stochastic_Main[0];
   
   //--- Check all positions
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(position.SelectByIndex(i))
      {
         if(position.Symbol() == _Symbol && position.Magic() == MagicNumber)
         {
            //--- Exit LONG position when stochastic reaches 95
            if(position.PositionType() == POSITION_TYPE_BUY)
            {
               if(stoch_current >= 95)
               {
                  if(trade.PositionClose(position.Ticket()))
                  {
                     Print("Закрыта длинная позиция по сигналу стохастика >= 95");
                  }
                  else
                  {
                     Print("Ошибка закрытия длинной позиции: ", trade.ResultRetcode());
                  }
               }
            }
            
            //--- Exit SHORT position when stochastic reaches 5
            if(position.PositionType() == POSITION_TYPE_SELL)
            {
               if(stoch_current <= 5)
               {
                  if(trade.PositionClose(position.Ticket()))
                  {
                     Print("Закрыта короткая позиция по сигналу стохастика <= 5");
                  }
                  else
                  {
                     Print("Ошибка закрытия короткой позиции: ", trade.ResultRetcode());
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Tester function                                                  |
//+------------------------------------------------------------------+
double OnTester()
{
   double profit = TesterStatistics(STAT_PROFIT);
   return(profit);
}

//+------------------------------------------------------------------+