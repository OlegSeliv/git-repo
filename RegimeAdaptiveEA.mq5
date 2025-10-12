// RegimeAdaptiveEA.mq5
// Robust EA with regime detection (trend vs range), volatility targeting, and custom optimization
#property strict
#property version   "1.0.0"
#property description "Regime-aware EA: trades trend or range with ATR risk, spread/session filters, and custom optimization"

#include <Trade/Trade.mqh>

// ----------------------------
// Types and configuration
// ----------------------------

enum RegimeType
{
   REGIME_UNKNOWN = 0,
   REGIME_TREND   = 1,
   REGIME_RANGE   = 2
};

enum OptimizationMode
{
   OptimizeNetProfit = 0,
   OptimizeSharpe    = 1,
   OptimizeCustom    = 2
};

enum ProfitProfile
{
   Conservative = 0,
   Balanced     = 1,
   Aggressive   = 2
};

// ----------------------------
// Inputs
// ----------------------------

input string            InpSymbol                 = "";            // Symbol (empty = current chart)
input ENUM_TIMEFRAMES   InpSignalTF               = PERIOD_M5;     // Signal timeframe
input ENUM_TIMEFRAMES   InpRegimeTF               = PERIOD_H1;     // Regime detection timeframe
input ulong             InpMagic                  = 20251012;      // Magic number

// Trading toggles
input bool              InpTradeTrend             = true;          // Enable trend strategy
input bool              InpTradeRange             = true;          // Enable range strategy
input bool              InpSignalsOnBarClose      = true;          // Generate signals on bar close
input int               InpMinBarsBetweenSignals  = 1;             // Min bars between signals per regime

// Risk and position sizing
input double            InpRiskPerTradePercent    = 0.50;          // Risk per trade, % of equity
input ProfitProfile     InpProfitProfile          = Balanced;      // Profile adjusts risk scaling
input bool              InpUseEquityForRisk       = true;          // Use equity (true) or balance (false)

// Volatility and stops (multipliers of ATR on Signal TF)
input int               InpATRPeriod              = 14;            // ATR period (Signal TF)
input double            InpStopATRTrend           = 2.50;          // Trend: Stop size in ATR
input double            InpTrailATRTrend          = 2.00;          // Trend: Trailing stop in ATR (0=disabled)
input double            InpTakeATRTrend           = 0.00;          // Trend: Take profit in ATR (0=disabled)
input double            InpStopATRRange           = 1.50;          // Range: Stop size in ATR
input double            InpTakeATRRange           = 2.00;          // Range: Take profit in ATR

// Trend/Range detection
input int               InpADXPeriod              = 14;            // ADX period (Regime TF)
input double            InpADXTrendThreshold      = 22.0;          // ADX >= this => trend candidate
input double            InpADXRangeThreshold      = 18.0;          // ADX <= this => range candidate
input int               InpBBPeriod               = 20;            // Bollinger Bands period (Regime TF)
input double            InpBBDev                  = 2.0;           // Bollinger Bands deviation (Regime TF)
input double            InpRangeMaxBBWtoATR       = 1.5;           // Range if BBWidth <= k * ATR (Regime TF)

// Signal indicators (Signal TF)
input int               InpFastMAPeriod           = 20;            // Fast EMA period
input int               InpSlowMAPeriod           = 50;            // Slow EMA period
input int               InpRSIPeriod              = 14;            // RSI period (Signal TF)
input double            InpRSILongBelow           = 35.0;          // Range: Long if RSI <= this
input double            InpRSIShortAbove          = 65.0;          // Range: Short if RSI >= this

// Market quality filters
input int               InpMaxSpreadPoints        = 300;           // Max allowed spread (points)
input double            InpMinAtrToSpreadRatio    = 3.0;           // ATR / spread ratio must be >= this
input bool              InpUseSessionFilter       = false;         // Enable session hours filter
input int               InpSessionStartHour       = 7;             // Session start hour (server time)
input int               InpSessionEndHour         = 22;            // Session end hour (server time)

// Execution
input uint              InpOrderDeviationPoints   = 20;            // Max slippage in points

// Optimization target
input OptimizationMode  InpOptimizationMode       = OptimizeCustom;// Custom optimization selection
input double            InpCustomWeightSharpe     = 0.7;           // Custom: weight of Sharpe (0..1)
input double            InpCustomWeightPF         = 0.3;           // Custom: weight of Profit Factor (0..1)
input double            InpDrawdownPenaltyPower   = 2.0;           // Custom: drawdown penalty power
input double            InpMaxDDRefPercent        = 50.0;          // Custom: reference DD% for scaling penalty

// ----------------------------
// Globals
// ----------------------------

CTrade                  g_trade;
string                  g_symbol;
int                     g_digits = 0;
double                  g_point  = 0.0;

datetime                g_lastSignalBarTime = 0;
int                     g_barsSinceLastSignal = 999999;

// Indicator handles
int hADX_Regime = INVALID_HANDLE;
int hATR_Regime = INVALID_HANDLE;
int hBB_Regime  = INVALID_HANDLE; // Bands: buffers 0=upper,1=middle,2=lower

int hATR_Signal = INVALID_HANDLE;
int hEMA_Fast   = INVALID_HANDLE;
int hEMA_Slow   = INVALID_HANDLE;
int hRSI_Signal = INVALID_HANDLE;
int hBB_Signal  = INVALID_HANDLE; // For range entries on Signal TF

// Regime smoothing
double g_regimeScoreEMA = 0.0; // >0 => trend bias, <0 => range bias
const double REGIME_ALPHA = 0.25; // smoothing factor

// ----------------------------
// Utility helpers
// ----------------------------

bool GetLatestBufferValue(const int handle, const int bufferIndex, double &value)
{
   if(handle == INVALID_HANDLE) return false;
   double tmp[2];
   int copied = CopyBuffer(handle, bufferIndex, 0, 2, tmp);
   if(copied <= 0) return false;
   value = tmp[0];
   return (value != EMPTY_VALUE);
}

bool GetPrevAndCurr(const int handle, const int bufferIndex, double &prevValue, double &currValue)
{
   if(handle == INVALID_HANDLE) return false;
   double tmp[3];
   int copied = CopyBuffer(handle, bufferIndex, 0, 3, tmp);
   if(copied < 2) return false;
   currValue = tmp[0];
   prevValue = tmp[1];
   return (currValue != EMPTY_VALUE && prevValue != EMPTY_VALUE);
}

bool EnsureIndicatorsReady(const int handle, const string name)
{
   if(handle == INVALID_HANDLE)
   {
      PrintFormat("[Init] %s handle is invalid", name);
      return false;
   }
   int barsReady = BarsCalculated(handle);
   if(barsReady <= 0)
   {
      PrintFormat("[Init] %s not ready (BarsCalculated=%d)", name, barsReady);
      return false;
   }
   return true;
}

bool IsNewSignalBar()
{
   datetime t = iTime(g_symbol, InpSignalTF, 0);
   if(t != g_lastSignalBarTime)
   {
      g_lastSignalBarTime = t;
      g_barsSinceLastSignal++;
      return true;
   }
   return false;
}

bool SessionOk()
{
   if(!InpUseSessionFilter) return true;
   datetime now = TimeCurrent();
   int hour = TimeHour(now);
   if(InpSessionStartHour <= InpSessionEndHour)
      return (hour >= InpSessionStartHour && hour < InpSessionEndHour);
   // Overnight wraparound
   return (hour >= InpSessionStartHour || hour < InpSessionEndHour);
}

bool SpreadOk(double &spreadPointsOut)
{
   MqlTick tick;
   if(!SymbolInfoTick(g_symbol, tick)) return false;
   double spreadPrice = tick.ask - tick.bid;
   spreadPointsOut = spreadPrice / g_point;
   if(spreadPointsOut > InpMaxSpreadPoints) return false;
   return true;
}

double AtrToSpreadRatio()
{
   double atr;
   if(!GetLatestBufferValue(hATR_Signal, 0, atr)) return 0.0;
   MqlTick tick;
   if(!SymbolInfoTick(g_symbol, tick)) return 0.0;
   double spreadPrice = tick.ask - tick.bid;
   if(spreadPrice <= 0.0) return 0.0;
   return (atr / spreadPrice);
}

double RiskScalingByProfile()
{
   switch(InpProfitProfile)
   {
      case Conservative: return 0.7;
      case Aggressive:   return 1.4;
      default:           return 1.0; // Balanced
   }
}

double ComputePositionSizeLots(const double stopDistancePrice)
{
   if(stopDistancePrice <= 0.0) return 0.0;
   double equityOrBalance = InpUseEquityForRisk ? AccountInfoDouble(ACCOUNT_EQUITY)
                                                : AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = equityOrBalance * (InpRiskPerTradePercent / 100.0) * RiskScalingByProfile();

   double tickValue = 0.0, tickSize = 0.0;
   if(!SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE, tickValue)) return 0.0;
   if(!SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE,  tickSize))  return 0.0;
   if(tickValue <= 0.0 || tickSize <= 0.0) return 0.0;

   double riskPerLot = stopDistancePrice * (tickValue / tickSize);
   if(riskPerLot <= 0.0) return 0.0;

   double rawLots = riskAmount / riskPerLot;

   double volMin=0.0, volMax=0.0, volStep=0.0;
   SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN,  volMin);
   SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX,  volMax);
   SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP, volStep);

   if(volStep <= 0.0) volStep = 0.01; // fallback
   double normLots = MathFloor(rawLots / volStep) * volStep;
   normLots = MathMax(normLots, volMin);
   if(volMax > 0.0) normLots = MathMin(normLots, volMax);
   return normLots;
}

bool SelectOurPosition(POSITION_TYPE &posType, double &volume, double &priceOpen, double &sl, double &tp, ulong &ticket)
{
   if(!PositionSelect(g_symbol)) return false;
   long magic = (long)PositionGetInteger(POSITION_MAGIC);
   if((ulong)magic != InpMagic) return false;

   posType   = (POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   volume    = PositionGetDouble(POSITION_VOLUME);
   priceOpen = PositionGetDouble(POSITION_PRICE_OPEN);
   sl        = PositionGetDouble(POSITION_SL);
   tp        = PositionGetDouble(POSITION_TP);
   ticket    = (ulong)PositionGetInteger(POSITION_TICKET);
   return true;
}

bool ModifyTrailingStopTrend()
{
   if(InpTrailATRTrend <= 0.0) return true;
   POSITION_TYPE posType; double vol, priceOpen, sl, tp; ulong ticket;
   if(!SelectOurPosition(posType, vol, priceOpen, sl, tp, ticket)) return true;

   double atr;
   if(!GetLatestBufferValue(hATR_Signal, 0, atr)) return false;
   MqlTick tick; if(!SymbolInfoTick(g_symbol, tick)) return false;

   double newSL = sl;
   if(posType == POSITION_TYPE_BUY)
   {
      double candidate = tick.bid - InpTrailATRTrend * atr;
      if(sl <= 0.0 || candidate > sl)
         newSL = candidate;
   }
   else if(posType == POSITION_TYPE_SELL)
   {
      double candidate = tick.ask + InpTrailATRTrend * atr;
      if(sl <= 0.0 || candidate < sl)
         newSL = candidate;
   }
   newSL = NormalizeDouble(newSL, g_digits);
   if(newSL != sl)
   {
      g_trade.SetExpertMagicNumber(InpMagic);
      g_trade.SetDeviationInPoints((int)InpOrderDeviationPoints);
      if(!g_trade.PositionModify(g_symbol, newSL, tp))
         PrintFormat("[Trail] PositionModify failed. SL=%.5f TP=%.5f, err=%d", newSL, tp, GetLastError());
   }
   return true;
}

// ----------------------------
// Regime detection
// ----------------------------

RegimeType DetectRegime()
{
   double adx;
   if(!GetLatestBufferValue(hADX_Regime, 0, adx)) return REGIME_UNKNOWN;

   double atrReg;
   if(!GetLatestBufferValue(hATR_Regime, 0, atrReg)) return REGIME_UNKNOWN;

   double bbUpper, bbLower;
   if(!GetLatestBufferValue(hBB_Regime, 0, bbUpper)) return REGIME_UNKNOWN;
   if(!GetLatestBufferValue(hBB_Regime, 2, bbLower)) return REGIME_UNKNOWN;
   double bbWidth = bbUpper - bbLower;

   int signalBars = iBars(g_symbol, InpSignalTF);
   int regimeBars = iBars(g_symbol, InpRegimeTF);
   if(signalBars < MathMax(InpSlowMAPeriod + 5, 60) || regimeBars < MathMax(InpBBPeriod + 5, 100))
      return REGIME_UNKNOWN;

   bool isTrendCandidate = (adx >= InpADXTrendThreshold);
   bool isRangeCandidate = (adx <= InpADXRangeThreshold) && (bbWidth <= InpRangeMaxBBWtoATR * atrReg);

   int score = 0;
   if(isTrendCandidate) score += 1;
   if(isRangeCandidate) score -= 1;

   g_regimeScoreEMA = REGIME_ALPHA * (double)score + (1.0 - REGIME_ALPHA) * g_regimeScoreEMA;

   if(g_regimeScoreEMA > 0.5)  return REGIME_TREND;
   if(g_regimeScoreEMA < -0.5) return REGIME_RANGE;
   return REGIME_UNKNOWN;
}

// ----------------------------
// Signal logic
// ----------------------------

bool GetEMAs(double &prevFast, double &currFast, double &prevSlow, double &currSlow)
{
   if(!GetPrevAndCurr(hEMA_Fast, 0, prevFast, currFast)) return false;
   if(!GetPrevAndCurr(hEMA_Slow, 0, prevSlow, currSlow)) return false;
   return true;
}

bool TrendEntrySignal(bool &wantLong, bool &wantShort)
{
   wantLong = false; wantShort = false;
   double pf, cf, ps, cs;
   if(!GetEMAs(pf, cf, ps, cs)) return false;

   bool crossUp   = (pf <= ps && cf > cs);
   bool crossDown = (pf >= ps && cf < cs);

   if(crossUp)   wantLong = true;
   if(crossDown) wantShort = true;
   return (wantLong || wantShort);
}

bool RangeEntrySignal(bool &wantLong, bool &wantShort)
{
   wantLong = false; wantShort = false;
   double rsi; if(!GetLatestBufferValue(hRSI_Signal, 0, rsi)) return false;

   double upper, middle, lower;
   if(!GetLatestBufferValue(hBB_Signal, 0, upper)) return false;
   if(!GetLatestBufferValue(hBB_Signal, 1, middle)) return false;
   if(!GetLatestBufferValue(hBB_Signal, 2, lower)) return false;

   MqlTick tick; if(!SymbolInfoTick(g_symbol, tick)) return false;
   double price = (tick.bid + tick.ask) * 0.5;

   bool nearLower = (price <= lower);
   bool nearUpper = (price >= upper);

   if(nearLower && rsi <= InpRSILongBelow)  wantLong = true;
   if(nearUpper && rsi >= InpRSIShortAbove) wantShort = true;
   return (wantLong || wantShort);
}

// ----------------------------
// Order placement helpers
// ----------------------------

bool OpenPosition(const bool isLong, const double stopATR, const double takeATR)
{
   double atr; if(!GetLatestBufferValue(hATR_Signal, 0, atr)) return false;
   double stopDistancePrice = stopATR * atr;
   double volumeLots = ComputePositionSizeLots(stopDistancePrice);
   if(volumeLots <= 0.0) { Print("[Trade] Computed volume is zero"); return false; }

   MqlTick tick; if(!SymbolInfoTick(g_symbol, tick)) return false;

   double sl = 0.0, tp = 0.0;
   if(isLong)
   {
      sl = NormalizeDouble(tick.bid - stopDistancePrice, g_digits);
      if(takeATR > 0.0) tp = NormalizeDouble(tick.bid + takeATR * atr, g_digits);
   }
   else
   {
      sl = NormalizeDouble(tick.ask + stopDistancePrice, g_digits);
      if(takeATR > 0.0) tp = NormalizeDouble(tick.ask - takeATR * atr, g_digits);
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints((int)InpOrderDeviationPoints);

   bool ok = false;
   if(isLong)
      ok = g_trade.Buy(volumeLots, g_symbol, 0.0, sl, tp);
   else
      ok = g_trade.Sell(volumeLots, g_symbol, 0.0, sl, tp);

   if(!ok)
   {
      PrintFormat("[Trade] Entry failed (isLong=%d) err=%d", (int)isLong, GetLastError());
      return false;
   }
   g_barsSinceLastSignal = 0;
   return true;
}

bool CloseExistingPositionIfOpposite(const bool wantLong, const bool wantShort)
{
   POSITION_TYPE posType; double vol, priceOpen, sl, tp; ulong ticket;
   if(!SelectOurPosition(posType, vol, priceOpen, sl, tp, ticket)) return true;

   if((posType == POSITION_TYPE_BUY && wantShort) || (posType == POSITION_TYPE_SELL && wantLong))
   {
      g_trade.SetExpertMagicNumber(InpMagic);
      g_trade.SetDeviationInPoints((int)InpOrderDeviationPoints);
      if(!g_trade.PositionClose(g_symbol))
      {
         PrintFormat("[Trade] PositionClose failed err=%d", GetLastError());
         return false;
      }
   }
   return true;
}

// ----------------------------
// MT5 standard functions
// ----------------------------

int OnInit()
{
   g_symbol = (InpSymbol == "" ? _Symbol : InpSymbol);
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   g_point  = SymbolInfoDouble(g_symbol, SYMBOL_POINT);

   hADX_Regime = iADX(g_symbol, InpRegimeTF, InpADXPeriod);
   hATR_Regime = iATR(g_symbol, InpRegimeTF, InpATRPeriod);
   hBB_Regime  = iBands(g_symbol, InpRegimeTF, InpBBPeriod, 0,  PRICE_CLOSE, InpBBDev);

   hATR_Signal = iATR(g_symbol, InpSignalTF, InpATRPeriod);
   hEMA_Fast   = iMA(g_symbol, InpSignalTF, InpFastMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   hEMA_Slow   = iMA(g_symbol, InpSignalTF, InpSlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   hRSI_Signal = iRSI(g_symbol, InpSignalTF, InpRSIPeriod, PRICE_CLOSE);
   hBB_Signal  = iBands(g_symbol, InpSignalTF, InpBBPeriod, 0, PRICE_CLOSE, InpBBDev);

   bool ok = true;
   ok = ok && EnsureIndicatorsReady(hADX_Regime, "ADX(Regime)");
   ok = ok && EnsureIndicatorsReady(hATR_Regime, "ATR(Regime)");
   ok = ok && EnsureIndicatorsReady(hBB_Regime,  "BB(Regime)");
   ok = ok && EnsureIndicatorsReady(hATR_Signal, "ATR(Signal)");
   ok = ok && EnsureIndicatorsReady(hEMA_Fast,   "EMA Fast");
   ok = ok && EnsureIndicatorsReady(hEMA_Slow,   "EMA Slow");
   ok = ok && EnsureIndicatorsReady(hRSI_Signal, "RSI(Signal)");
   ok = ok && EnsureIndicatorsReady(hBB_Signal,  "BB(Signal)");

   if(!ok)
   {
      Print("[Init] Indicators not ready");
      return INIT_FAILED;
   }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_lastSignalBarTime = iTime(g_symbol, InpSignalTF, 0);
   g_barsSinceLastSignal = 999999;
   g_regimeScoreEMA = 0.0;

   PrintFormat("[Init] RegimeAdaptiveEA initialized on %s (SignalTF=%d, RegimeTF=%d)", g_symbol, (int)InpSignalTF, (int)InpRegimeTF);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   // Nothing to clean explicitly
}

void OnTick()
{
   double spreadPoints;
   if(!SpreadOk(spreadPoints)) return;
   if(AtrToSpreadRatio() < InpMinAtrToSpreadRatio) return;
   if(!SessionOk()) return;

   bool newBar = IsNewSignalBar();
   if(InpSignalsOnBarClose && !newBar) { ModifyTrailingStopTrend(); return; }

   RegimeType regime = DetectRegime();
   ModifyTrailingStopTrend();

   if(g_barsSinceLastSignal < InpMinBarsBetweenSignals) return;

   bool wantLong=false, wantShort=false;

   if(regime == REGIME_TREND && InpTradeTrend)
   {
     if(!TrendEntrySignal(wantLong, wantShort)) return;
     if(!CloseExistingPositionIfOpposite(wantLong, wantShort)) return;
     if(wantLong)
        OpenPosition(true,  InpStopATRTrend, InpTakeATRTrend);
     else if(wantShort)
        OpenPosition(false, InpStopATRTrend, InpTakeATRTrend);
     return;
   }

   if(regime == REGIME_RANGE && InpTradeRange)
   {
     if(!RangeEntrySignal(wantLong, wantShort)) return;
     if(!CloseExistingPositionIfOpposite(wantLong, wantShort)) return;
     if(wantLong)
        OpenPosition(true,  InpStopATRRange, InpTakeATRRange);
     else if(wantShort)
        OpenPosition(false, InpStopATRRange, InpTakeATRRange);
     return;
   }
}

// ----------------------------
// Custom optimization criterion
// ----------------------------

double OnTester()
{
   if(InpOptimizationMode == OptimizeNetProfit)
   {
      return TesterStatistics(STAT_PROFIT);
   }
   else if(InpOptimizationMode == OptimizeSharpe)
   {
      return TesterStatistics(STAT_SHARPE_RATIO);
   }
   else
   {
      double sharpe = TesterStatistics(STAT_SHARPE_RATIO);
      double pf     = TesterStatistics(STAT_PROFIT_FACTOR);
      double ddRel  = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
      if(!MathIsValidNumber(sharpe)) sharpe = 0.0;
      if(!MathIsValidNumber(pf))     pf     = 0.0;
      if(!MathIsValidNumber(ddRel))  ddRel  = 100.0;

      double wS = MathMax(0.0, MathMin(1.0, InpCustomWeightSharpe));
      double wP = MathMax(0.0, MathMin(1.0, InpCustomWeightPF));
      double mix = wS * sharpe + wP * MathMin(pf, 3.0);

      double ref = MathMax(1.0, InpMaxDDRefPercent);
      double ddPenaltyBase = MathMax(0.0, (ref - ddRel) / ref); // 1.0 if dd=0, 0.0 if dd>=ref
      double ddPenalty = MathPow(ddPenaltyBase, MathMax(0.5, InpDrawdownPenaltyPower));

      return mix * ddPenalty;
   }
}
