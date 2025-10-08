//+------------------------------------------------------------------+
//|                                                StochRsiTrendEA.mq5|
//|                           Expert Advisor: RSI(H4) + Stoch(M15) EA |
//|  Direction: RSI(H4) > 50 -> long setups; < 50 -> short setups     |
//|  Entries: Stochastic(M15) crosses/holds beyond 25/75              |
//|  Exits: Long when Stoch >= 95; Short when Stoch <= 5              |
//|  Stop Loss: 2 x ATR(M15)                                          |
//+------------------------------------------------------------------+
#property strict
#property description "EA opens trades with RSI(H4) trend filter and Stochastic(M15) entries."
#property description "Stop-loss = 2 x ATR(M15). Optional Stochastic exits and ATR trailing stop."
#property version   "1.00"

#include <Trade/Trade.mqh>

//------------------------------ Inputs ---------------------------------
input double InpLotSize                = 0.10;     // Default lot size
input int    InpRSIPeriod              = 14;       // RSI period (trend filter)
input ENUM_TIMEFRAMES InpTrendTimeframe= PERIOD_H4;// RSI timeframe

input int    InpStochKPeriod           = 5;        // Stochastic K period
input int    InpStochDPeriod           = 3;        // Stochastic D period
input int    InpStochSlowing           = 3;        // Stochastic slowing
input ENUM_MA_METHOD InpStochMaMethod  = MODE_SMA; // Stochastic MA method
input ENUM_STO_PRICE InpStochPrice     = STO_LOWHIGH; // Stochastic price field
input ENUM_TIMEFRAMES InpSignalTimeframe = PERIOD_M15; // Stochastic/ATR timeframe

input int    InpATRPeriod              = 14;       // ATR period

input double InpRSITrendLevel          = 50.0;     // RSI threshold for trend
input double InpLongEntryLevel         = 25.0;     // Stochastic level for long entries
input double InpShortEntryLevel        = 75.0;     // Stochastic level for short entries
input double InpExitLongLevel          = 95.0;     // Exit long when Stoch >= level
input double InpExitShortLevel         = 5.0;      // Exit short when Stoch <= level

// Trailing stop and exits
input bool   InpEnableTrailingStop     = true;     // Enable ATR-based trailing stop
input double InpTrailAtrMult           = 3.0;      // ATR multiple for trailing (chandelier-style)
input bool   InpTrailUseBarClose       = true;     // Use last closed bar price instead of Bid/Ask
input int    InpMinTrailStepPoints     = 10;       // Minimal improvement to move SL (points)
input bool   InpEnableStochExit        = false;    // Enable Stochastic extremum exit (95/5)

input int    InpDeviationPoints        = 30;       // Max slippage (points)
input ulong  InpMagicNumber            = 20251008; // Magic number

//------------------------------ Globals --------------------------------
int      g_rsiHandle   = INVALID_HANDLE;
int      g_stochHandle = INVALID_HANDLE;
int      g_atrHandle   = INVALID_HANDLE;

CTrade   g_trade;
datetime g_lastSignalBarTime = 0; // last processed bar time on signal timeframe (e.g., M15)

//--------------------------- Helper Functions --------------------------
bool CopySingleBufferValue(const int handle, const int bufferIndex, const int shift, double &value)
{
   double temp[1];
   int copied = CopyBuffer(handle, bufferIndex, shift, 1, temp);
   if(copied != 1 || temp[0] == EMPTY_VALUE)
      return false;
   value = temp[0];
   return true;
}

bool CopyTwoStochValues(const int handle, const int bufferIndex, const int startShift, double &v1, double &v2)
{
   // Fetch two consecutive values starting at startShift
   double temp[2];
   int copied = CopyBuffer(handle, bufferIndex, startShift, 2, temp);
   if(copied != 2)
      return false;
   v1 = temp[0]; // value at shift = startShift (e.g., last closed bar => shift=1)
   v2 = temp[1]; // value at shift = startShift+1
   return true;
}

bool IsNewSignalBar()
{
   datetime currentBarTime = iTime(_Symbol, InpSignalTimeframe, 0);
   if(currentBarTime == 0)
      return false;
   if(currentBarTime != g_lastSignalBarTime)
   {
      g_lastSignalBarTime = currentBarTime;
      return true;
   }
   return false;
}

bool HasOpenPositionForSymbol()
{
   if(!PositionSelect(_Symbol))
      return false;
   // If selected, there is an open position on this symbol
   return true;
}

long CurrentPositionType()
{
   if(!PositionSelect(_Symbol))
      return -1;
   return (long)PositionGetInteger(POSITION_TYPE);
}

bool ClosePositionIfExitSignal(const double stochK_lastClosed)
{
   if(!PositionSelect(_Symbol))
      return false;

   long posType = (long)PositionGetInteger(POSITION_TYPE);
   if(posType == POSITION_TYPE_BUY)
   {
      if(stochK_lastClosed >= InpExitLongLevel)
      {
         bool closed = g_trade.PositionClose(_Symbol);
         if(!closed)
            Print("Close BUY failed. Error: ", _LastError);
         else
            Print("BUY closed by Stochastic >= ", InpExitLongLevel);
         return closed;
      }
   }
   else if(posType == POSITION_TYPE_SELL)
   {
      if(stochK_lastClosed <= InpExitShortLevel)
      {
         bool closed = g_trade.PositionClose(_Symbol);
         if(!closed)
            Print("Close SELL failed. Error: ", _LastError);
         else
            Print("SELL closed by Stochastic <= ", InpExitShortLevel);
         return closed;
      }
   }
   return false;
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price, (int)_Digits);
}

double ComputeValidSLDistancePoints(const double desiredDistancePoints)
{
   long stopsLevel = 0;
   if(!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel))
      stopsLevel = 0;
   double minDistance = (double)stopsLevel;
   if(desiredDistancePoints < minDistance)
      return minDistance; // ensure broker minimal stop distance
   return desiredDistancePoints;
}

bool PlaceOrderWithATRSL(const bool isBuy, const double atrValue)
{
   // ATR is in price units; SL distance = 2 * ATR
   double slDistancePrice = 2.0 * atrValue;
   double price = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(price <= 0.0)
      return false;

   double desiredDistancePoints = slDistancePrice / _Point; // convert to points
   double validDistancePoints   = ComputeValidSLDistancePoints(desiredDistancePoints);
   double slPrice = isBuy ? price - validDistancePoints * _Point
                          : price + validDistancePoints * _Point;
   slPrice = NormalizePrice(slPrice);

   // Use CTrade for simplified order placement
   bool result = false;
   if(isBuy)
   {
      result = g_trade.Buy(InpLotSize, _Symbol, 0.0 /* market */, slPrice, 0.0 /* no TP */);
      if(!result) Print("Buy failed. Error: ", _LastError);
      else Print("Buy placed. SL=", DoubleToString(slPrice, (int)_Digits));
   }
   else
   {
      result = g_trade.Sell(InpLotSize, _Symbol, 0.0 /* market */, slPrice, 0.0 /* no TP */);
      if(!result) Print("Sell failed. Error: ", _LastError);
      else Print("Sell placed. SL=", DoubleToString(slPrice, (int)_Digits));
   }
   return result;
}

bool UpdateTrailingStop(const double atrValue)
{
   if(!InpEnableTrailingStop)
      return false;
   if(!PositionSelect(_Symbol))
      return false;

   long posType = (long)PositionGetInteger(POSITION_TYPE);
   double currSL = PositionGetDouble(POSITION_SL);
   double currTP = PositionGetDouble(POSITION_TP);

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(bid <= 0.0 || ask <= 0.0)
      return false;

   // Base price for trailing reference: last closed bar price on signal TF or live Bid/Ask
   double basePrice = 0.0;
   if(InpTrailUseBarClose)
      basePrice = iClose(_Symbol, InpSignalTimeframe, 1);
   else
      basePrice = (posType == POSITION_TYPE_BUY ? bid : ask);
   if(basePrice <= 0.0 || atrValue <= 0.0)
      return false;

   long stopsLevel = 0;
   if(!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL, stopsLevel))
      stopsLevel = 0;

   double minMovePrice = (double)InpMinTrailStepPoints * _Point; // minimal improvement to update SL

   if(posType == POSITION_TYPE_BUY)
   {
      // Candidate trailing stop using chandelier-like formula
      double candidateSL = basePrice - InpTrailAtrMult * atrValue;
      double maxAllowedSL = bid - (double)stopsLevel * _Point; // must be below current price with stops level
      double newSL = MathMin(candidateSL, maxAllowedSL);
      newSL = NormalizePrice(newSL);

      if(newSL <= 0.0)
         return false;

      // Only tighten (raise) stop loss
      if(currSL == 0.0 || newSL > currSL + minMovePrice)
      {
         bool ok = g_trade.PositionModify(_Symbol, newSL, currTP);
         if(!ok)
            Print("Trailing SL BUY modify failed. Error: ", _LastError);
         else
            Print("Trailing SL BUY updated to ", DoubleToString(newSL, (int)_Digits));
         return ok;
      }
   }
   else if(posType == POSITION_TYPE_SELL)
   {
      double candidateSL = basePrice + InpTrailAtrMult * atrValue;
      double minAllowedSL = ask + (double)stopsLevel * _Point; // must be above current price by stops level
      double newSL = MathMax(candidateSL, minAllowedSL);
      newSL = NormalizePrice(newSL);

      if(newSL <= 0.0)
         return false;

      // Only tighten (lower) stop loss for short
      if(currSL == 0.0 || newSL < currSL - minMovePrice)
      {
         bool ok = g_trade.PositionModify(_Symbol, newSL, currTP);
         if(!ok)
            Print("Trailing SL SELL modify failed. Error: ", _LastError);
         else
            Print("Trailing SL SELL updated to ", DoubleToString(newSL, (int)_Digits));
         return ok;
      }
   }
   return false;
}

//------------------------------ Events ---------------------------------
int OnInit()
{
   g_trade.SetExpertMagicNumber((long)InpMagicNumber);
   g_trade.SetDeviationInPoints(InpDeviationPoints);

   g_rsiHandle   = iRSI(_Symbol, InpTrendTimeframe, InpRSIPeriod, PRICE_CLOSE);
   g_stochHandle = iStochastic(_Symbol, InpSignalTimeframe, InpStochKPeriod, InpStochDPeriod,
                               InpStochSlowing, InpStochMaMethod, InpStochPrice);
   g_atrHandle   = iATR(_Symbol, InpSignalTimeframe, InpATRPeriod);

   if(g_rsiHandle == INVALID_HANDLE || g_stochHandle == INVALID_HANDLE || g_atrHandle == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles. RSI:", g_rsiHandle, " Stoch:", g_stochHandle, " ATR:", g_atrHandle);
      return(INIT_FAILED);
   }

   g_lastSignalBarTime = iTime(_Symbol, InpSignalTimeframe, 0);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(g_rsiHandle != INVALID_HANDLE)   IndicatorRelease(g_rsiHandle);
   if(g_stochHandle != INVALID_HANDLE) IndicatorRelease(g_stochHandle);
   if(g_atrHandle != INVALID_HANDLE)   IndicatorRelease(g_atrHandle);
}

void OnTick()
{
   if(!IsNewSignalBar())
      return; // operate on closed bars of the signal timeframe

   // Fetch RSI(H4) last closed bar
   double rsiLastClosed = 0.0;
   if(!CopySingleBufferValue(g_rsiHandle, 0, 1, rsiLastClosed))
   {
      Print("Failed to fetch RSI value.");
      return;
   }

   // Fetch Stochastic(M15) %K values for last two closed bars: shift 1 and 2
   double stochK1 = 0.0, stochK2 = 0.0;
   if(!CopyTwoStochValues(g_stochHandle, 0 /* %K */, 1, stochK1, stochK2))
   {
      Print("Failed to fetch Stochastic %K values.");
      return;
   }

   // Fetch ATR(M15) last closed bar value for trailing/initial SL
   double atrLastClosed = 0.0;
   if(!CopySingleBufferValue(g_atrHandle, 0, 1, atrLastClosed))
   {
      Print("Failed to fetch ATR value.");
      return;
   }

   // Attempt exit first if a position is open
   if(HasOpenPositionForSymbol())
   {
      // 1) Apply/update trailing stop first to avoid contradiction with exits
      UpdateTrailingStop(atrLastClosed);
      // 2) Optional Stochastic exit logic (can be disabled to favor trailing)
      if(InpEnableStochExit)
         ClosePositionIfExitSignal(stochK1);
      return; // manage one action per bar
   }

   // No open position: check trend and entry conditions
   // Long setup: RSI(H4) > 50, Stoch rising from below and holding above 25
   bool allowLong = (rsiLastClosed > InpRSITrendLevel);
   if(allowLong)
   {
      bool stochCrossedUp = (stochK2 <= InpLongEntryLevel) && (stochK1 > InpLongEntryLevel) && (stochK1 > stochK2);
      if(stochCrossedUp)
      {
         PlaceOrderWithATRSL(true /* buy */, atrLastClosed);
         return;
      }
   }

   // Short setup: RSI(H4) < 50, Stoch falling from above and holding below 75
   bool allowShort = (rsiLastClosed < InpRSITrendLevel);
   if(allowShort)
   {
      bool stochCrossedDown = (stochK2 >= InpShortEntryLevel) && (stochK1 < InpShortEntryLevel) && (stochK1 < stochK2);
      if(stochCrossedDown)
      {
         PlaceOrderWithATRSL(false /* sell */, atrLastClosed);
         return;
      }
   }
}

