#property copyright ""
#property version   "1.00"
#property strict
#property description "MTF Stochastic/RSI entries, ATR SL, trailing, dynamic lot, sounds"
#property script_show_inputs

#include <Trade/Trade.mqh>

//=== Inputs ===
input ENUM_TIMEFRAMES InpTF_EntryTF = PERIOD_M5;     // Entry timeframe
input ENUM_TIMEFRAMES InpTF_Filter1 = PERIOD_H1;     // Filter timeframe 1 (H1)
input ENUM_TIMEFRAMES InpTF_Filter2 = PERIOD_H4;     // Filter timeframe 2 (H4)

input int      InpKPeriod = 14;                      // Stochastic K period
input int      InpDPeriod = 3;                       // Stochastic D period
input int      InpSlowing = 3;                       // Stochastic slowing
input ENUM_MA_METHOD InpMAType = MODE_SMA;           // Stochastic MA method
input ENUM_STO_PRICE InpPriceField = STO_LOWHIGH;    // Stochastic price field

input int      InpRSIPeriod = 14;                    // RSI period

input double   InpAtrMultiplier = 2.0;               // ATR SL multiplier
input int      InpATRPeriod = 14;                    // ATR period (for H1)

input double   InpMinLot = 0.01;                     // Minimum lot size
input double   InpRiskPerTradePct = 1.0;             // Risk per trade (%) if using balance risk
input bool     InpAutoLotByBalance = true;           // Auto lot sizing by risk/balance

input bool     InpUseTrailing = true;                // Enable trailing stop
input double   InpTrailATRMult = 2.0;                // Trailing ATR multiplier (H1 ATR)
input int      InpTrailStepPoints = 50;              // Minimum modification step in points

input double   InpMaxSpreadPoints = 50;              // Max spread filter (points)
input int      InpSlippagePoints = 10;               // Slippage (points)

input bool     InpAllowLong = true;                  // Allow long entries
input bool     InpAllowShort = true;                 // Allow short entries

input bool     InpOneTradePerSignal = true;          // Avoid re-entering on same bar

input bool     InpEnableSounds = true;               // Enable sound alerts
input string   InpSoundEntry = "alert.wav";          // Sound for entry
input string   InpSoundExit  = "alert2.wav";         // Sound for exit

//=== Globals ===
CTrade Trade;
MqlTick g_tick;
datetime g_lastSignalBarTimeBuy = 0;
datetime g_lastSignalBarTimeSell = 0;

// Indicator handles
int hStochEntry = INVALID_HANDLE;
int hStochF1    = INVALID_HANDLE;
int hStochF2    = INVALID_HANDLE;
int hRSIF1      = INVALID_HANDLE;
int hRSIF2      = INVALID_HANDLE;
int hATR_H1     = INVALID_HANDLE;

//--- symbol & digits
string g_symbol;
int    g_digits;
double g_point;

//=== Helper: spread in points ===
double CurrentSpreadPoints()
{
   SymbolInfoTick(g_symbol, g_tick);
   double spread = (g_tick.ask - g_tick.bid) / g_point;
   return spread;
}

//=== Helper: copy last two values for any indicator ===
bool CopyTwo(const int handle, const int buffer, const ENUM_TIMEFRAMES tf, double &prev, double &curr)
{
   double vals[3];
   ArraySetAsSeries(vals, true);
   int copied = CopyBuffer(handle, buffer, 0, 3, vals);
   if(copied < 2) return false;
   curr = vals[0];
   prev = vals[1];
   return true;
}

//=== Helper: direction for stochastic (upward/downward) ===
bool IsStochUp(const int handle)
{
   double prevK, currK;
   if(!CopyTwo(handle, 0, InpTF_EntryTF, prevK, currK)) return false;
   return currK > prevK;
}

bool IsStochDown(const int handle)
{
   double prevK, currK;
   if(!CopyTwo(handle, 0, InpTF_EntryTF, prevK, currK)) return false;
   return currK < prevK;
}

//=== Helper: RSI value above/below threshold ===
bool IsRSIAbove(const int handle, double level)
{
   double prev, curr;
   if(!CopyTwo(handle, 0, InpTF_Filter1, prev, curr)) return false;
   return curr > level;
}

bool IsRSIBelow(const int handle, double level)
{
   double prev, curr;
   if(!CopyTwo(handle, 0, InpTF_Filter1, prev, curr)) return false;
   return curr < level;
}

//=== Helper: get ATR(H1) current value ===
bool GetATR(double &atr)
{
   double v[2];
   ArraySetAsSeries(v, true);
   int copied = CopyBuffer(hATR_H1, 0, 0, 2, v);
   if(copied < 1) return false;
   atr = v[0];
   return true;
}

//=== Create/refresh indicator handles ===
bool CreateIndicators()
{
   if(hStochEntry != INVALID_HANDLE) IndicatorRelease(hStochEntry);
   if(hStochF1    != INVALID_HANDLE) IndicatorRelease(hStochF1);
   if(hStochF2    != INVALID_HANDLE) IndicatorRelease(hStochF2);
   if(hRSIF1      != INVALID_HANDLE) IndicatorRelease(hRSIF1);
   if(hRSIF2      != INVALID_HANDLE) IndicatorRelease(hRSIF2);
   if(hATR_H1     != INVALID_HANDLE) IndicatorRelease(hATR_H1);

   hStochEntry = iStochastic(g_symbol, InpTF_EntryTF, InpKPeriod, InpDPeriod, InpSlowing, InpMAType, InpPriceField);
   hStochF1    = iStochastic(g_symbol, InpTF_Filter1, InpKPeriod, InpDPeriod, InpSlowing, InpMAType, InpPriceField);
   hStochF2    = iStochastic(g_symbol, InpTF_Filter2, InpKPeriod, InpDPeriod, InpSlowing, InpMAType, InpPriceField);
   hRSIF1      = iRSI(g_symbol, InpTF_Filter1, InpRSIPeriod, PRICE_CLOSE);
   hRSIF2      = iRSI(g_symbol, InpTF_Filter2, InpRSIPeriod, PRICE_CLOSE);
   hATR_H1     = iATR(g_symbol, PERIOD_H1, InpATRPeriod);

   if(hStochEntry==INVALID_HANDLE || hStochF1==INVALID_HANDLE || hStochF2==INVALID_HANDLE ||
      hRSIF1==INVALID_HANDLE || hRSIF2==INVALID_HANDLE || hATR_H1==INVALID_HANDLE)
   {
      Print("[EA] Failed to create indicator handles. Error:", GetLastError());
      return false;
   }
   return true;
}

//=== Lot sizing ===
double NormalizeLot(double lot)
{
   double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
   double minv = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double maxv = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   lot = MathMax(minv, MathMin(maxv, MathFloor(lot/step)*step));
   return lot;
}

double CalcAutoLot(double stopLossPoints)
{
   if(!InpAutoLotByBalance) return NormalizeLot(InpMinLot);
   if(stopLossPoints <= 0) return NormalizeLot(InpMinLot);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * (InpRiskPerTradePct/100.0);

   // Tick value per lot
   double tick_value = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size  = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   double point      = g_point;

   // Monetary loss for 1 lot at given SL distance:
   double money_per_lot = (stopLossPoints*point/tick_size) * tick_value;
   if(money_per_lot <= 0.0) return NormalizeLot(InpMinLot);
   double lots = riskMoney / money_per_lot;
   lots = MathMax(lots, InpMinLot);
   return NormalizeLot(lots);
}

//=== Entry checks ===
bool M5_LongSignal(bool &crossedNow)
{
   crossedNow = false;
   // Need last two K values on entry TF
   double k[3];
   ArraySetAsSeries(k, true);
   if(CopyBuffer(hStochEntry, 0, 0, 3, k) < 3) return false;
   double prev = k[1];
   double curr = k[0];

   // Cross up through 30 this bar
   if(prev < 30.0 && curr >= 30.0) crossedNow = true;

   // Direction filters (H1, H4 stochastic up) and RSI>50
   double k1_prev, k1_curr, k2_prev, k2_curr;
   if(!CopyTwo(hStochF1, 0, InpTF_Filter1, k1_prev, k1_curr)) return false;
   if(!CopyTwo(hStochF2, 0, InpTF_Filter2, k2_prev, k2_curr)) return false;

   double r1_prev, r1_curr, r2_prev, r2_curr; // not used prev, but fetched
   if(!CopyTwo(hRSIF1, 0, InpTF_Filter1, r1_prev, r1_curr)) return false;
   if(!CopyTwo(hRSIF2, 0, InpTF_Filter2, r2_prev, r2_curr)) return false;

   bool dirOk = (k1_curr > k1_prev) && (k2_curr > k2_prev);
   bool rsiOk = (r1_curr > 50.0) && (r2_curr > 50.0);

   return dirOk && rsiOk;
}

bool M5_ShortSignal(bool &crossedNow)
{
   crossedNow = false;
   double k[3];
   ArraySetAsSeries(k, true);
   if(CopyBuffer(hStochEntry, 0, 0, 3, k) < 3) return false;
   double prev = k[1];
   double curr = k[0];

   // Cross down through 80 this bar
   if(prev > 80.0 && curr <= 80.0) crossedNow = true;

   double k1_prev, k1_curr, k2_prev, k2_curr;
   if(!CopyTwo(hStochF1, 0, InpTF_Filter1, k1_prev, k1_curr)) return false;
   if(!CopyTwo(hStochF2, 0, InpTF_Filter2, k2_prev, k2_curr)) return false;

   double r1_prev, r1_curr, r2_prev, r2_curr;
   if(!CopyTwo(hRSIF1, 0, InpTF_Filter1, r1_prev, r1_curr)) return false;
   if(!CopyTwo(hRSIF2, 0, InpTF_Filter2, r2_prev, r2_curr)) return false;

   bool dirOk = (k1_curr < k1_prev) && (k2_curr < k2_prev);
   bool rsiOk = (r1_curr < 50.0) && (r2_curr < 50.0);

   return dirOk && rsiOk;
}

//=== Trailing stop helper ===
void ApplyTrailingStops()
{
   if(!InpUseTrailing) return;

   double atr;
   if(!GetATR(atr)) return;
   double trailDist = atr * InpTrailATRMult;

   int total = PositionsTotal();
   for(int i=0; i<total; ++i)
   {
      string sym = PositionGetSymbol(i);
      if(sym != g_symbol) continue;
      if(!PositionSelect(sym)) continue;

      long type = (long)PositionGetInteger(POSITION_TYPE);
      double sl  = PositionGetDouble(POSITION_SL);
      double price_open = PositionGetDouble(POSITION_PRICE_OPEN);
      double price_current = PositionGetDouble(POSITION_PRICE_CURRENT);

      double newSL = sl;
      if(type == POSITION_TYPE_BUY)
      {
         double candidate = price_current - trailDist;
         if(sl < candidate - InpTrailStepPoints*g_point)
            newSL = candidate;
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double candidate = price_current + trailDist;
         if(sl == 0.0 || sl > candidate + InpTrailStepPoints*g_point)
            newSL = candidate;
      }

      if(newSL != sl && newSL > 0)
      {
         Trade.PositionSelect(g_symbol);
         Trade.PositionModify(g_symbol, newSL, PositionGetDouble(POSITION_TP));
      }
   }
}

//=== Check if we can trade and spread filter ===
bool CanTradeNow()
{
   if(!SymbolInfoTick(g_symbol, g_tick)) return false;
   if(CurrentSpreadPoints() > InpMaxSpreadPoints) return false;
   return true;
}

//=== Entry executor ===
void TryOpenPositions()
{
   if(!CanTradeNow()) return;

   // Avoid duplicate entries if requested
   datetime barTime = iTime(g_symbol, InpTF_EntryTF, 0);

   double atr;
   if(!GetATR(atr)) return;
   double slPoints = (atr * InpAtrMultiplier) / g_point;

   bool crossed;

   // Long
   if(InpAllowLong && M5_LongSignal(crossed))
   {
      if(!InpOneTradePerSignal || (barTime != g_lastSignalBarTimeBuy && crossed))
      {
         double ask = g_tick.ask;
         double sl = ask - atr*InpAtrMultiplier;
         double lot = CalcAutoLot(slPoints);
         Trade.SetDeviationInPoints(InpSlippagePoints);
         bool ok = Trade.Buy(lot, g_symbol, ask, sl, 0.0, "MTF Long");
         if(ok)
         {
            if(InpEnableSounds) PlaySound(InpSoundEntry);
            g_lastSignalBarTimeBuy = barTime;
         }
      }
   }

   // Short
   if(InpAllowShort && M5_ShortSignal(crossed))
   {
      if(!InpOneTradePerSignal || (barTime != g_lastSignalBarTimeSell && crossed))
      {
         double bid = g_tick.bid;
         double sl = bid + atr*InpAtrMultiplier;
         double lot = CalcAutoLot(slPoints);
         Trade.SetDeviationInPoints(InpSlippagePoints);
         bool ok = Trade.Sell(lot, g_symbol, bid, sl, 0.0, "MTF Short");
         if(ok)
         {
            if(InpEnableSounds) PlaySound(InpSoundEntry);
            g_lastSignalBarTimeSell = barTime;
         }
      }
   }
}

//=== Trade transaction for exit sounds ===
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(!InpEnableSounds) return;
   if(trans.type==TRADE_TRANSACTION_DEAL_ADD)
   {
      if(HistoryDealSelect(trans.deal))
      {
         long deal_type = HistoryDealGetInteger(trans.deal, DEAL_TYPE);
         if(deal_type==DEAL_SL || deal_type==DEAL_TP || deal_type==DEAL_PROFIT || deal_type==DEAL_CLOSE_BY)
         {
            PlaySound(InpSoundExit);
         }
      }
   }
}

//=== Standard EA callbacks ===
int OnInit()
{
   g_symbol = _Symbol;
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   g_point  = SymbolInfoDouble(g_symbol, SYMBOL_POINT);

   Trade.SetAsyncMode(false);

   if(!CreateIndicators()) return(INIT_FAILED);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   if(hStochEntry != INVALID_HANDLE) IndicatorRelease(hStochEntry);
   if(hStochF1    != INVALID_HANDLE) IndicatorRelease(hStochF1);
   if(hStochF2    != INVALID_HANDLE) IndicatorRelease(hStochF2);
   if(hRSIF1      != INVALID_HANDLE) IndicatorRelease(hRSIF1);
   if(hRSIF2      != INVALID_HANDLE) IndicatorRelease(hRSIF2);
   if(hATR_H1     != INVALID_HANDLE) IndicatorRelease(hATR_H1);
}

void OnTick()
{
   if(!SymbolInfoTick(g_symbol, g_tick)) return;
   ApplyTrailingStops();
   TryOpenPositions();
}
