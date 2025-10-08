#property copyright ""
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input double InpLots               = 0.10;      // Default lot size
input int    InpRSIPeriod          = 14;        // RSI period (H4)
input int    InpStoK               = 14;        // Stochastic %K (M15)
input int    InpStoD               = 3;         // Stochastic %D (M15)
input int    InpStoSlowing         = 3;         // Stochastic slowing
input int    InpATRPeriod          = 14;        // ATR period (M15)
input double InpATRMultiplier      = 2.0;       // Stop Loss = ATR * multiplier
input int    InpDeviationPoints    = 10;        // Max slippage in points
input long   InpMagic              = 20251008;  // Magic number

#define RSI_TF PERIOD_H4
#define STO_TF PERIOD_M15
#define ATR_TF PERIOD_M15

CTrade trade;

int      rsiHandle = INVALID_HANDLE;
int      stoHandle = INVALID_HANDLE;
int      atrHandle = INVALID_HANDLE;
datetime lastEntryBarTime = 0; // Prevent multiple entries within same M15 bar

int getSymbolTradeMode() {
  long mode = (long)SYMBOL_TRADE_MODE_DISABLED;
  if (!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE, mode))
    return (int)SYMBOL_TRADE_MODE_DISABLED;
  return (int)mode;
}

double normalizeVolume(double volume) {
  double volMin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
  double volMax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
  double volStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
  if (volStep > 0.0) {
    volume = MathFloor(volume / volStep) * volStep;
  }
  if (volume < volMin) volume = volMin;
  if (volume > volMax) volume = volMax;
  // Normalize to 2 decimals is usually fine for most symbols; step normalization above dominates
  return NormalizeDouble(volume, 2);
}

bool ensureIndicatorDataReady() {
  if (rsiHandle == INVALID_HANDLE || stoHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE)
    return false;
  if (BarsCalculated(rsiHandle) <= 0) return false;
  if (BarsCalculated(stoHandle) <= 0) return false;
  if (BarsCalculated(atrHandle) <= 0) return false;
  return true;
}

bool getRSIH4(double &rsiClosed) {
  double buf[1];
  if (CopyBuffer(rsiHandle, 0, 1, 1, buf) != 1)
    return false;
  rsiClosed = buf[0];
  return true;
}

bool getStochasticM15(double &kShift1, double &kShift2) {
  double k[2];
  // shift 1 (last closed M15 bar) and shift 2 (previous closed bar)
  if (CopyBuffer(stoHandle, 0, 1, 2, k) != 2)
    return false;
  kShift1 = k[0];
  kShift2 = k[1];
  return true;
}

bool getATRm15(double &atrClosed) {
  double a[1];
  if (CopyBuffer(atrHandle, 0, 1, 1, a) != 1)
    return false;
  atrClosed = a[0];
  return true;
}

bool hasOpenPosition(string symbol) {
  if (PositionSelect(symbol))
    return true;
  return false;
}

int positionType(string symbol) {
  if (!PositionSelect(symbol))
    return -1;
  return (int)PositionGetInteger(POSITION_TYPE); // POSITION_TYPE_BUY or POSITION_TYPE_SELL
}

double normalizePrice(double price) {
  return NormalizeDouble(price, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
}

double minStopDistancePricePoints() {
  // Minimum stop level in points
  return (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
}

bool placeBuy(double lots, double sl) {
  trade.SetExpertMagicNumber(InpMagic);
  trade.SetDeviationInPoints(InpDeviationPoints);
  double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  sl = normalizePrice(sl);
  return trade.Buy(lots, _Symbol, ask, sl, 0.0, "RSI_H4_Stoch_M15_Long");
}

bool placeSell(double lots, double sl) {
  trade.SetExpertMagicNumber(InpMagic);
  trade.SetDeviationInPoints(InpDeviationPoints);
  double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
  sl = normalizePrice(sl);
  return trade.Sell(lots, _Symbol, bid, sl, 0.0, "RSI_H4_Stoch_M15_Short");
}

void tryEnterPositions() {
  if (hasOpenPosition(_Symbol))
    return;

  // Prevent multiple entries within the same M15 bar
  datetime barTime0 = iTime(_Symbol, STO_TF, 0);
  if (barTime0 == 0)
    return;
  if (lastEntryBarTime == barTime0)
    return;

  int tradeMode = getSymbolTradeMode();
  bool allowLong  = (tradeMode == SYMBOL_TRADE_MODE_FULL || tradeMode == SYMBOL_TRADE_MODE_LONGONLY);
  bool allowShort = (tradeMode == SYMBOL_TRADE_MODE_FULL || tradeMode == SYMBOL_TRADE_MODE_SHORTONLY);
  if (!(allowLong || allowShort))
    return; // disabled or closeonly

  double rsiH4;
  double k1, k2;
  double atrVal;
  if (!getRSIH4(rsiH4)) return;
  if (!getStochasticM15(k1, k2)) return;
  if (!getATRm15(atrVal)) return;

  // Entry logic:
  // Long filter: RSI(H4) > 50, Stoch K crosses up through 25 and closes above (k2 < 25, k1 >= 25, and rising)
  bool longSignal = (rsiH4 > 50.0) && (k2 < 25.0) && (k1 >= 25.0) && (k1 > k2);

  // Short filter: RSI(H4) < 50, Stoch K crosses down through 75 and closes below (k2 > 75, k1 <= 75, and falling)
  bool shortSignal = (rsiH4 < 50.0) && (k2 > 75.0) && (k1 <= 75.0) && (k1 < k2);

  if (!longSignal && !shortSignal)
    return;

  // Compute SL = price +/- ATR*multiplier (based on M15 ATR of last closed bar)
  double priceAsk = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  double priceBid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
  double point    = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
  double stopsPts = minStopDistancePricePoints();

  double lots = normalizeVolume(InpLots);

  if (longSignal && allowLong) {
    double sl = priceAsk - (InpATRMultiplier * atrVal);
    // Enforce minimal stop distance
    if ((priceAsk - sl) < (stopsPts * point))
      sl = priceAsk - (stopsPts + 1) * point;
    if (placeBuy(lots, sl)) {
      lastEntryBarTime = barTime0;
    }
  }

  if (shortSignal && allowShort) {
    double sl = priceBid + (InpATRMultiplier * atrVal);
    // Enforce minimal stop distance
    if ((sl - priceBid) < (stopsPts * point))
      sl = priceBid + (stopsPts + 1) * point;
    if (placeSell(lots, sl)) {
      lastEntryBarTime = barTime0;
    }
  }
}

void manageExit() {
  if (!hasOpenPosition(_Symbol))
    return;

  double k1, k2;
  if (!getStochasticM15(k1, k2))
    return;

  int ptype = positionType(_Symbol);
  if (ptype == POSITION_TYPE_BUY) {
    // Exit long when Stoch K on M15 reaches >= 95 on closed bar
    if (k1 >= 95.0) {
      trade.SetExpertMagicNumber(InpMagic);
      trade.SetDeviationInPoints(InpDeviationPoints);
      trade.PositionClose(_Symbol);
    }
  } else if (ptype == POSITION_TYPE_SELL) {
    // Exit short when Stoch K on M15 reaches <= 5 on closed bar
    if (k1 <= 5.0) {
      trade.SetExpertMagicNumber(InpMagic);
      trade.SetDeviationInPoints(InpDeviationPoints);
      trade.PositionClose(_Symbol);
    }
  }
}

int OnInit() {
  trade.SetExpertMagicNumber(InpMagic);
  trade.SetDeviationInPoints(InpDeviationPoints);

  rsiHandle = iRSI(_Symbol, RSI_TF, InpRSIPeriod, PRICE_CLOSE);
  if (rsiHandle == INVALID_HANDLE) {
    Print("Failed to create RSI handle");
    return INIT_FAILED;
  }

  stoHandle = iStochastic(_Symbol, STO_TF, InpStoK, InpStoD, InpStoSlowing, MODE_SMA, STO_LOWHIGH);
  if (stoHandle == INVALID_HANDLE) {
    Print("Failed to create Stochastic handle");
    return INIT_FAILED;
  }

  atrHandle = iATR(_Symbol, ATR_TF, InpATRPeriod);
  if (atrHandle == INVALID_HANDLE) {
    Print("Failed to create ATR handle");
    return INIT_FAILED;
  }

  return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
  if (rsiHandle != INVALID_HANDLE) {
    IndicatorRelease(rsiHandle);
    rsiHandle = INVALID_HANDLE;
  }
  if (stoHandle != INVALID_HANDLE) {
    IndicatorRelease(stoHandle);
    stoHandle = INVALID_HANDLE;
  }
  if (atrHandle != INVALID_HANDLE) {
    IndicatorRelease(atrHandle);
    atrHandle = INVALID_HANDLE;
  }
}

void OnTick() {
  if (!ensureIndicatorDataReady())
    return;

  // Only operate on symbols that allow trading (mode not disabled/closeonly)
  int mode = getSymbolTradeMode();
  if (!(mode == SYMBOL_TRADE_MODE_FULL || mode == SYMBOL_TRADE_MODE_LONGONLY || mode == SYMBOL_TRADE_MODE_SHORTONLY))
    return;

  // Basic safety: avoid trading during no-price or spread anomalies
  double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
  double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  if (bid <= 0 || ask <= 0)
    return;
  double spreadPoints = (ask - bid) / SymbolInfoDouble(_Symbol, SYMBOL_POINT);
  // Optional: skip if spread extremely high (e.g., > 10x stops level)
  double stopsPts = minStopDistancePricePoints();
  if (stopsPts > 0 && spreadPoints > 10.0 * stopsPts)
    return;

  manageExit();
  tryEnterPositions();
}

