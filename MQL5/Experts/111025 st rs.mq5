#property version   "1.00"
#property strict
#property description "MTF Stoch/RSI EA with ATR SL, trailing, auto lot"

#include <Trade/Trade.mqh>

// Reuse the same EA implementation under a simpler file name
// (Copied from MTF_Stoch_RSI_ATR_Trailing.mq5)

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

// Sounds removed

CTrade Trade;
MqlTick g_tick;
datetime g_lastSignalBarTimeBuy = 0;
datetime g_lastSignalBarTimeSell = 0;

int hStochEntry = INVALID_HANDLE;
int hStochF1    = INVALID_HANDLE;
int hStochF2    = INVALID_HANDLE;
int hRSIF1      = INVALID_HANDLE;
int hRSIF2      = INVALID_HANDLE;
int hATR_H1     = INVALID_HANDLE;

string g_symbol;
int    g_digits;
double g_point;

double CurrentSpreadPoints(){ SymbolInfoTick(g_symbol, g_tick); return (g_tick.ask - g_tick.bid) / g_point; }

bool CopyTwo(const int handle, const int buffer, double &prev, double &curr){ double v[3]; if(CopyBuffer(handle,buffer,0,3,v)<2) return false; curr=v[0]; prev=v[1]; return true; }

bool IsRSIAbove(const int handle, double level){ double p,c; if(!CopyTwo(handle,0,p,c)) return false; return c>level; }
bool IsRSIBelow(const int handle, double level){ double p,c; if(!CopyTwo(handle,0,p,c)) return false; return c<level; }

bool GetATR(double &atr){ double v[2]; int c=CopyBuffer(hATR_H1,0,0,2,v); if(c<1) return false; atr=v[0]; return true; }

bool CreateIndicators(){
  if(hStochEntry!=INVALID_HANDLE) IndicatorRelease(hStochEntry);
  if(hStochF1   !=INVALID_HANDLE) IndicatorRelease(hStochF1);
  if(hStochF2   !=INVALID_HANDLE) IndicatorRelease(hStochF2);
  if(hRSIF1     !=INVALID_HANDLE) IndicatorRelease(hRSIF1);
  if(hRSIF2     !=INVALID_HANDLE) IndicatorRelease(hRSIF2);
  if(hATR_H1    !=INVALID_HANDLE) IndicatorRelease(hATR_H1);
  hStochEntry=iStochastic(g_symbol,InpTF_EntryTF,InpKPeriod,InpDPeriod,InpSlowing,InpMAType,InpPriceField);
  hStochF1   =iStochastic(g_symbol,InpTF_Filter1,InpKPeriod,InpDPeriod,InpSlowing,InpMAType,InpPriceField);
  hStochF2   =iStochastic(g_symbol,InpTF_Filter2,InpKPeriod,InpDPeriod,InpSlowing,InpMAType,InpPriceField);
  hRSIF1     =iRSI(g_symbol,InpTF_Filter1,InpRSIPeriod,PRICE_CLOSE);
  hRSIF2     =iRSI(g_symbol,InpTF_Filter2,InpRSIPeriod,PRICE_CLOSE);
  hATR_H1    =iATR(g_symbol,PERIOD_H1,InpATRPeriod);
  if(hStochEntry==INVALID_HANDLE||hStochF1==INVALID_HANDLE||hStochF2==INVALID_HANDLE||hRSIF1==INVALID_HANDLE||hRSIF2==INVALID_HANDLE||hATR_H1==INVALID_HANDLE){ Print("[EA] Failed to create indicators:",GetLastError()); return false; }
  return true;
}

double NormalizeLot(double lot){ double step=SymbolInfoDouble(g_symbol,SYMBOL_VOLUME_STEP); double minv=SymbolInfoDouble(g_symbol,SYMBOL_VOLUME_MIN); double maxv=SymbolInfoDouble(g_symbol,SYMBOL_VOLUME_MAX); lot=MathMax(minv,MathMin(maxv,MathFloor(lot/step)*step)); return lot; }

double CalcAutoLot(double stopLossPoints){ if(stopLossPoints<=0) return NormalizeLot(InpMinLot); if(!InpAutoLotByBalance) return NormalizeLot(InpMinLot); double balance=AccountInfoDouble(ACCOUNT_BALANCE); double risk=balance*(InpRiskPerTradePct/100.0); double tv=SymbolInfoDouble(g_symbol,SYMBOL_TRADE_TICK_VALUE); double ts=SymbolInfoDouble(g_symbol,SYMBOL_TRADE_TICK_SIZE); if(tv<=0.0 || ts<=0.0) return NormalizeLot(InpMinLot); double moneyPerLot=(stopLossPoints*g_point/ts)*tv; if(moneyPerLot<=0) return NormalizeLot(InpMinLot); double lots=risk/moneyPerLot; if(lots<InpMinLot) lots=InpMinLot; return NormalizeLot(lots); }

bool M5_LongSignal(bool &crossed){ crossed=false; double k[3]; if(CopyBuffer(hStochEntry,0,0,3,k)<3) return false; double prev=k[1], cur=k[0]; if(prev<30.0 && cur>=30.0) crossed=true; double k1p,k1c,k2p,k2c; if(!CopyTwo(hStochF1,0,k1p,k1c)) return false; if(!CopyTwo(hStochF2,0,k2p,k2c)) return false; double r1p,r1c,r2p,r2c; if(!CopyTwo(hRSIF1,0,r1p,r1c)) return false; if(!CopyTwo(hRSIF2,0,r2p,r2c)) return false; bool dirOk=(k1c>k1p)&&(k2c>k2p); bool rsiOk=(r1c>50.0)&&(r2c>50.0); return dirOk&&rsiOk; }

bool M5_ShortSignal(bool &crossed){ crossed=false; double k[3]; if(CopyBuffer(hStochEntry,0,0,3,k)<3) return false; double prev=k[1], cur=k[0]; if(prev>80.0 && cur<=80.0) crossed=true; double k1p,k1c,k2p,k2c; if(!CopyTwo(hStochF1,0,k1p,k1c)) return false; if(!CopyTwo(hStochF2,0,k2p,k2c)) return false; double r1p,r1c,r2p,r2c; if(!CopyTwo(hRSIF1,0,r1p,r1c)) return false; if(!CopyTwo(hRSIF2,0,r2p,r2c)) return false; bool dirOk=(k1c<k1p)&&(k2c<k2p); bool rsiOk=(r1c<50.0)&&(r2c<50.0); return dirOk&&rsiOk; }

void ApplyTrailingStops(){ if(!InpUseTrailing) return; double atr; if(!GetATR(atr)) return; double dist=atr*InpTrailATRMult; if(!PositionSelect(g_symbol)) return; long type=(long)PositionGetInteger(POSITION_TYPE); double sl=PositionGetDouble(POSITION_SL); double pc=PositionGetDouble(POSITION_PRICE_CURRENT); double newSL=sl; if(type==POSITION_TYPE_BUY){ double cand=pc-dist; if(sl<cand-InpTrailStepPoints*g_point) newSL=cand; } else if(type==POSITION_TYPE_SELL){ double cand=pc+dist; if(sl==0.0 || sl>cand+InpTrailStepPoints*g_point) newSL=cand; } if(newSL!=sl && newSL>0) Trade.PositionModify(g_symbol,newSL,PositionGetDouble(POSITION_TP)); }

bool CanTradeNow(){ if(!SymbolInfoTick(g_symbol,g_tick)) return false; if(CurrentSpreadPoints()>InpMaxSpreadPoints) return false; return true; }

void TryOpenPositions(){ if(!CanTradeNow()) return; datetime bar=iTime(g_symbol,InpTF_EntryTF,0); double atr; if(!GetATR(atr)) return; double slPoints=(atr*InpAtrMultiplier)/g_point; bool crossed; if(InpAllowLong && M5_LongSignal(crossed)){ if(!InpOneTradePerSignal || (bar!=g_lastSignalBarTimeBuy && crossed)){ double ask=g_tick.ask; double sl=ask-atr*InpAtrMultiplier; double lot=CalcAutoLot(slPoints); Trade.SetDeviationInPoints(InpSlippagePoints); if(Trade.Buy(lot,g_symbol,ask,sl,0.0,"MTF Long")){ g_lastSignalBarTimeBuy=bar; } } }
  if(InpAllowShort && M5_ShortSignal(crossed)){ if(!InpOneTradePerSignal || (bar!=g_lastSignalBarTimeSell && crossed)){ double bid=g_tick.bid; double sl=bid+atr*InpAtrMultiplier; double lot=CalcAutoLot(slPoints); Trade.SetDeviationInPoints(InpSlippagePoints); if(Trade.Sell(lot,g_symbol,bid,sl,0.0,"MTF Short")){ g_lastSignalBarTimeSell=bar; } } } }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){ /* sounds removed */ }

int OnInit(){ g_symbol=_Symbol; g_digits=(int)SymbolInfoInteger(g_symbol,SYMBOL_DIGITS); g_point=SymbolInfoDouble(g_symbol,SYMBOL_POINT); Trade.SetAsyncMode(false); if(!CreateIndicators()) return INIT_FAILED; return INIT_SUCCEEDED; }

void OnDeinit(const int reason){ if(hStochEntry!=INVALID_HANDLE) IndicatorRelease(hStochEntry); if(hStochF1!=INVALID_HANDLE) IndicatorRelease(hStochF1); if(hStochF2!=INVALID_HANDLE) IndicatorRelease(hStochF2); if(hRSIF1!=INVALID_HANDLE) IndicatorRelease(hRSIF1); if(hRSIF2!=INVALID_HANDLE) IndicatorRelease(hRSIF2); if(hATR_H1!=INVALID_HANDLE) IndicatorRelease(hATR_H1); }

void OnTick(){ if(!SymbolInfoTick(g_symbol,g_tick)) return; ApplyTrailingStops(); TryOpenPositions(); }
