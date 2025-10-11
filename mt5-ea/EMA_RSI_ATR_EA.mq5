// EMA + RSI ATR Risk EA for MetaTrader 5
// Version: 1.0.0
// Date: 2025-10-08

#property copyright "Public Domain"
#property version   "1.0.0"
#property strict

#include <Trade/Trade.mqh>

//============================
// Inputs
//============================
input string InpSymbol              = "";               // Symbol (empty = current)
input ENUM_TIMEFRAMES InpTimeframe  = PERIOD_CURRENT;   // Timeframe (current = chart)

// Signal: EMA crossover + RSI filter
input int    InpFastMAPeriod        = 20;               // Fast EMA period
input int    InpSlowMAPeriod        = 50;               // Slow EMA period
input int    InpRSIPeriod           = 14;               // RSI period
input double InpRSIBuyAbove         = 55.0;             // Buy only if RSI >= value
input double InpRSISellBelow        = 45.0;             // Sell only if RSI <= value
input bool   InpAllowLong           = true;             // Allow long trades
input bool   InpAllowShort          = true;             // Allow short trades

// Risk and exits
input bool   InpUseFixedLots        = false;            // Use fixed lot size
input double InpFixedLots           = 0.10;             // Fixed lot size
input double InpRiskPercent         = 1.0;              // Risk % of equity per trade
input int    InpATRPeriod           = 14;               // ATR period
input double InpATRSLMultiplier     = 2.0;              // SL = ATR * multiplier
input double InpRewardRiskRatio     = 1.5;              // TP = R:R * SL distance
input bool   InpUseStopLoss         = true;             // Place Stop Loss
input bool   InpUseTakeProfit       = true;             // Place Take Profit

// Trailing stop (ATR-based)
input bool   InpEnableTrailing      = true;             // Enable ATR trailing stop
input double InpTrailATRMultiplier  = 1.0;              // Trail distance = ATR * multiplier
input bool   InpTrailEveryTick      = true;             // Adjust trailing on every tick

// Filters
input bool   InpUseNewBarOnly       = true;             // Trade only on new bar
input bool   InpOneTradePerBar      = true;             // At most 1 entry per bar
input bool   InpUseSpreadFilter     = true;             // Enforce max spread
input int    InpMaxSpreadPoints     = 30;               // Max spread (points)
input bool   InpUseTradingHours     = false;            // Restrict trading hours
input int    InpTradeStartHour      = 0;                // Start hour (0-23)
input int    InpTradeEndHour        = 23;               // End hour (0-23)

// Trade and misc
input long   InpMagicNumber         = 20251008;         // Magic number
input string InpTradeComment        = "EMA_RSI_ATR_EA"; // Trade comment
input int    InpDeviationPoints     = 10;               // Max deviation (points)
input bool   InpAllowReversalNetting= true;             // In netting, close & reverse on opposite signal
input bool   InpOnePositionPerSymbol= true;             // Keep only one position per symbol
input bool   InpDebug               = false;            // Enable debug logs

//============================
// Globals
//============================
CTrade trade;

int      g_handleFastMA = INVALID_HANDLE;
int      g_handleSlowMA = INVALID_HANDLE;
int      g_handleRSI    = INVALID_HANDLE;
int      g_handleATR    = INVALID_HANDLE;

datetime g_lastBarTime  = 0;
datetime g_lastTradeBar = 0;

//============================
// Utilities
//============================
string getSymbol()
{
  if(InpSymbol == NULL || StringTrim(InpSymbol) == "")
    return(_Symbol);
  return(StringTrim(InpSymbol));
}

ENUM_TIMEFRAMES getTimeframe()
{
  if(InpTimeframe == PERIOD_CURRENT)
    return((ENUM_TIMEFRAMES)Period());
  return(InpTimeframe);
}

bool isHedgingAccount()
{
  ENUM_ACCOUNT_MARGIN_MODE m = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
  return(m == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
}

void logDebug(string msg)
{
  if(InpDebug)
    Print("[DEBUG] ", msg);
}

bool getTick(string symbol, MqlTick &tick)
{
  if(!SymbolInfoTick(symbol, tick))
  {
    PrintFormat("Failed SymbolInfoTick(%s).", symbol);
    return(false);
  }
  return(true);
}

bool isNewBar(string symbol, ENUM_TIMEFRAMES tf)
{
  datetime t0[];
  if(CopyTime(symbol, tf, 0, 2, t0) != 2)
    return(false);
  if(g_lastBarTime == 0)
  {
    g_lastBarTime = t0[0];
    return(true); // first run, consider as new bar to initialize
  }
  if(t0[0] != g_lastBarTime)
  {
    g_lastBarTime = t0[0];
    return(true);
  }
  return(false);
}

bool spreadOk(string symbol)
{
  if(!InpUseSpreadFilter) return(true);
  MqlTick t;
  if(!getTick(symbol, t)) return(false);
  double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
  int spreadPoints = (int)MathRound((t.ask - t.bid) / point);
  if(spreadPoints <= InpMaxSpreadPoints) return(true);
  logDebug(StringFormat("Spread too high: %d > %d", spreadPoints, InpMaxSpreadPoints));
  return(false);
}

bool tradingHoursOk()
{
  if(!InpUseTradingHours) return(true);
  MqlDateTime tm;
  TimeToStruct(TimeCurrent(), tm);
  int h = tm.hour;
  if(InpTradeStartHour <= InpTradeEndHour)
  {
    return(h >= InpTradeStartHour && h <= InpTradeEndHour);
  }
  // Overnight window (e.g., 22 -> 6)
  return(h >= InpTradeStartHour || h <= InpTradeEndHour);
}

int countPositionsForSymbol(string symbol)
{
  int total = PositionsTotal();
  int count = 0;
  for(int i = 0; i < total; ++i)
  {
    ulong ticket = PositionGetTicket(i);
    if(ticket == 0) continue;
    if(!PositionSelectByTicket(ticket)) continue;
    string ps = PositionGetString(POSITION_SYMBOL);
    long   mg = PositionGetInteger(POSITION_MAGIC);
    if(ps == symbol && mg == InpMagicNumber)
      count++;
  }
  return(count);
}

bool hasPosition(string symbol, ENUM_POSITION_TYPE type)
{
  int total = PositionsTotal();
  for(int i = 0; i < total; ++i)
  {
    ulong ticket = PositionGetTicket(i);
    if(ticket == 0) continue;
    if(!PositionSelectByTicket(ticket)) continue;
    string ps = PositionGetString(POSITION_SYMBOL);
    long   mg = PositionGetInteger(POSITION_MAGIC);
    ENUM_POSITION_TYPE pt = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    if(ps == symbol && mg == InpMagicNumber && pt == type)
      return(true);
  }
  return(false);
}

bool closeAllForSymbol(string symbol)
{
  bool ok = true;
  int total = PositionsTotal();
  for(int i = total - 1; i >= 0; --i)
  {
    ulong ticket = PositionGetTicket(i);
    if(ticket == 0) continue;
    if(!PositionSelectByTicket(ticket)) continue;
    string ps = PositionGetString(POSITION_SYMBOL);
    long   mg = PositionGetInteger(POSITION_MAGIC);
    if(ps != symbol || mg != InpMagicNumber) continue;
    if(!trade.PositionClose(ticket))
    {
      PrintFormat("Failed to close position %I64u on %s. Retcode=%d", ticket, symbol, trade.ResultRetcode());
      ok = false;
    }
  }
  return(ok);
}

bool copyIndicators(string symbol, ENUM_TIMEFRAMES tf,
                    double &emaFast1, double &emaFast2,
                    double &emaSlow1, double &emaSlow2,
                    double &rsi1,     double &rsi2,
                    double &atr1)
{
  // We use bar shifts 1 and 2 (last two closed bars)
  double bufFast[3], bufSlow[3], bufRSI[3], bufATR[3];
  ArrayInitialize(bufFast, 0.0); ArrayInitialize(bufSlow, 0.0);
  ArrayInitialize(bufRSI,  0.0); ArrayInitialize(bufATR,  0.0);

  int copied1 = CopyBuffer(g_handleFastMA, 0, 1, 3, bufFast);
  int copied2 = CopyBuffer(g_handleSlowMA, 0, 1, 3, bufSlow);
  int copied3 = CopyBuffer(g_handleRSI,    0, 1, 3, bufRSI);
  int copied4 = CopyBuffer(g_handleATR,    0, 1, 3, bufATR);
  if(copied1 < 3 || copied2 < 3 || copied3 < 3 || copied4 < 3)
  {
    logDebug("Not enough indicator data yet.");
    return(false);
  }

  emaFast1 = bufFast[0]; // last closed bar
  emaFast2 = bufFast[1]; // previous closed bar
  emaSlow1 = bufSlow[0];
  emaSlow2 = bufSlow[1];
  rsi1     = bufRSI[0];
  rsi2     = bufRSI[1];
  atr1     = bufATR[0];
  return(true);
}

enum TradeSignal { SIGNAL_NONE, SIGNAL_BUY, SIGNAL_SELL };

TradeSignal detectSignal(double emaFast1, double emaFast2,
                         double emaSlow1, double emaSlow2,
                         double rsi1)
{
  bool crossUp   = (emaFast2 <= emaSlow2 && emaFast1 > emaSlow1);
  bool crossDown = (emaFast2 >= emaSlow2 && emaFast1 < emaSlow1);

  if(crossUp && InpAllowLong && rsi1 >= InpRSIBuyAbove)
    return(SIGNAL_BUY);
  if(crossDown && InpAllowShort && rsi1 <= InpRSISellBelow)
    return(SIGNAL_SELL);
  return(SIGNAL_NONE);
}

int minimalStopsLevelPoints(string symbol)
{
  long stops = 0;
  if(!SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL, stops))
    return(0);
  return((int)stops);
}

double normalizePrice(string symbol, double price)
{
  int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
  return(NormalizeDouble(price, digits));
}

double normalizeVolume(string symbol, double vol)
{
  double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
  double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
  double step   = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

  if(vol < minLot) vol = minLot;
  if(vol > maxLot) vol = maxLot;
  if(step > 0.0)
    vol = MathFloor(vol / step) * step;
  return(NormalizeDouble(vol, (int)MathMax(0, (int)MathRound(-MathLog10(step)))));
}

bool calcSLTPPrices(string symbol, bool isBuy, int slPoints, int tpPoints,
                    double &sl, double &tp)
{
  MqlTick t;
  if(!getTick(symbol, t)) return(false);
  double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
  if(isBuy)
  {
    sl = InpUseStopLoss  ? normalizePrice(symbol, t.ask - slPoints * point) : 0.0;
    tp = InpUseTakeProfit? normalizePrice(symbol, t.ask + tpPoints * point) : 0.0;
  }
  else
  {
    sl = InpUseStopLoss  ? normalizePrice(symbol, t.bid + slPoints * point) : 0.0;
    tp = InpUseTakeProfit? normalizePrice(symbol, t.bid - tpPoints * point) : 0.0;
  }
  return(true);
}

double calcRiskBasedVolume(string symbol, bool isBuy, int slPoints)
{
  if(InpUseFixedLots)
    return(normalizeVolume(symbol, InpFixedLots));

  double equity = AccountInfoDouble(ACCOUNT_EQUITY);
  double riskMoney = equity * MathMax(0.0, InpRiskPercent) / 100.0;
  if(riskMoney <= 0.0)
    return(normalizeVolume(symbol, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN)));

  MqlTick t;
  if(!getTick(symbol, t))
    return(normalizeVolume(symbol, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN)));

  double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
  double entry = isBuy ? t.ask : t.bid;
  double slPrice = isBuy ? (entry - slPoints * point) : (entry + slPoints * point);

  double plForOneLot = 0.0;
  if(!OrderCalcProfit(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
                      symbol, 1.0, entry, slPrice, plForOneLot))
  {
    Print("OrderCalcProfit failed; fallback to min lot");
    return(normalizeVolume(symbol, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN)));
  }

  double lossOneLot = MathAbs(plForOneLot);
  if(lossOneLot <= 0.0)
    return(normalizeVolume(symbol, SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN)));

  double lots = riskMoney / lossOneLot;
  return(normalizeVolume(symbol, lots));
}

bool openTrade(string symbol, TradeSignal sig, int slPoints, int tpPoints)
{
  bool isBuy = (sig == SIGNAL_BUY);
  double sl=0.0, tp=0.0;
  if(!calcSLTPPrices(symbol, isBuy, slPoints, tpPoints, sl, tp))
    return(false);

  double volume = calcRiskBasedVolume(symbol, isBuy, slPoints);
  if(volume <= 0.0)
  {
    Print("Volume calculation failed");
    return(false);
  }

  trade.SetExpertMagicNumber(InpMagicNumber);
  trade.SetDeviationInPoints(InpDeviationPoints);

  bool result = false;
  if(isBuy)
    result = trade.Buy(volume, symbol, 0.0, sl, tp, InpTradeComment);
  else
    result = trade.Sell(volume, symbol, 0.0, sl, tp, InpTradeComment);

  if(!result)
  {
    PrintFormat("Order send failed. Retcode=%d, Comment=%s", trade.ResultRetcode(), trade.ResultComment());
    return(false);
  }
  return(true);
}

void updateTrailingStops(string symbol)
{
  if(!InpEnableTrailing) return;

  // Use latest ATR value (bar shift 1) as trailing reference
  double atrBuf[2];
  if(CopyBuffer(g_handleATR, 0, 1, 2, atrBuf) < 1)
    return;
  double atr = atrBuf[0];
  if(atr <= 0.0) return;

  double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
  int trailPoints = (int)MathMax(1.0, MathCeil((atr / point) * InpTrailATRMultiplier));

  int total = PositionsTotal();
  for(int i = 0; i < total; ++i)
  {
    ulong ticket = PositionGetTicket(i);
    if(ticket == 0) continue;
    if(!PositionSelectByTicket(ticket)) continue;
    string ps = PositionGetString(POSITION_SYMBOL);
    long   mg = PositionGetInteger(POSITION_MAGIC);
    if(ps != symbol || mg != InpMagicNumber) continue;

    ENUM_POSITION_TYPE pt = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double priceOpen = PositionGetDouble(POSITION_PRICE_OPEN);
    double sl        = PositionGetDouble(POSITION_SL);
    double priceCurrent = (pt == POSITION_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_BID)
                                                    : SymbolInfoDouble(symbol, SYMBOL_ASK);

    // Only trail when in profit
    if(pt == POSITION_TYPE_BUY)
    {
      double newSL = normalizePrice(symbol, priceCurrent - trailPoints * point);
      if(newSL > sl && newSL < priceCurrent)
      {
        trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
      }
    }
    else if(pt == POSITION_TYPE_SELL)
    {
      double newSL = normalizePrice(symbol, priceCurrent + trailPoints * point);
      if((sl == 0.0 || newSL < sl) && newSL > priceCurrent)
      {
        trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP));
      }
    }
  }
}

//============================
// Expert lifecycle
//============================
int OnInit()
{
  string symbol = getSymbol();
  ENUM_TIMEFRAMES tf = getTimeframe();

  if(!SymbolSelect(symbol, true))
  {
    PrintFormat("Failed to select symbol %s", symbol);
    return(INIT_FAILED);
  }

  g_handleFastMA = iMA(symbol, tf, InpFastMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
  g_handleSlowMA = iMA(symbol, tf, InpSlowMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
  g_handleRSI    = iRSI(symbol, tf, InpRSIPeriod, PRICE_CLOSE);
  g_handleATR    = iATR(symbol, tf, InpATRPeriod);

  if(g_handleFastMA == INVALID_HANDLE || g_handleSlowMA == INVALID_HANDLE ||
     g_handleRSI == INVALID_HANDLE    || g_handleATR == INVALID_HANDLE)
  {
    Print("Failed to create indicator handles");
    return(INIT_FAILED);
  }

  trade.SetExpertMagicNumber(InpMagicNumber);
  trade.SetDeviationInPoints(InpDeviationPoints);

  g_lastBarTime  = 0;
  g_lastTradeBar = 0;
  return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
  if(g_handleFastMA != INVALID_HANDLE) IndicatorRelease(g_handleFastMA);
  if(g_handleSlowMA != INVALID_HANDLE) IndicatorRelease(g_handleSlowMA);
  if(g_handleRSI    != INVALID_HANDLE) IndicatorRelease(g_handleRSI);
  if(g_handleATR    != INVALID_HANDLE) IndicatorRelease(g_handleATR);
}

void OnTick()
{
  string symbol = getSymbol();
  ENUM_TIMEFRAMES tf = getTimeframe();

  // Trailing can run on every tick if enabled
  if(InpEnableTrailing && InpTrailEveryTick)
    updateTrailingStops(symbol);

  if(InpUseNewBarOnly)
  {
    if(!isNewBar(symbol, tf))
      return;
  }

  if(!spreadOk(symbol) || !tradingHoursOk())
    return;

  // Fetch indicators for signal
  double emaFast1, emaFast2, emaSlow1, emaSlow2, rsi1, rsi2, atr1;
  if(!copyIndicators(symbol, tf, emaFast1, emaFast2, emaSlow1, emaSlow2, rsi1, rsi2, atr1))
    return;

  TradeSignal sig = detectSignal(emaFast1, emaFast2, emaSlow1, emaSlow2, rsi1);
  if(sig == SIGNAL_NONE)
    return;

  // One trade per bar guard
  if(InpOneTradePerBar && g_lastTradeBar == g_lastBarTime)
  {
    logDebug("One trade per bar already taken.");
    return;
  }

  // Enforce one position per symbol if requested
  int posCount = countPositionsForSymbol(symbol);
  if(InpOnePositionPerSymbol && posCount > 0)
  {
    // In netting: close and reverse if allowed
    if(!isHedgingAccount() && InpAllowReversalNetting)
    {
      closeAllForSymbol(symbol);
    }
    else
    {
      logDebug("Position exists and OnePositionPerSymbol=true; skipping new entry.");
      return;
    }
  }

  // Compute SL/TP distances from ATR
  double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
  int slPoints = (int)MathMax(1.0, MathCeil((atr1 / point) * InpATRSLMultiplier));
  int minStops = minimalStopsLevelPoints(symbol);
  if(slPoints < minStops) slPoints = minStops;
  int tpPoints = (int)MathMax(1.0, MathCeil(slPoints * InpRewardRiskRatio));

  // Execute order
  if(openTrade(symbol, sig, slPoints, tpPoints))
  {
    g_lastTradeBar = g_lastBarTime;
    // Update trailing right after entry if trailing is bar-based
    if(InpEnableTrailing && !InpTrailEveryTick)
      updateTrailingStops(symbol);
  }
}

