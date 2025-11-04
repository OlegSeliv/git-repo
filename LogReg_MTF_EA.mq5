#property copyright "Converted by GPT-5 Codex"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input double           InpLots            = 0.10;           // Размер позиции
input int              InpLength          = 100;            // Длина выборки логарифмической регрессии
input ENUM_TIMEFRAMES  InpHTF             = PERIOD_H4;      // Старший таймфрейм для фильтра
input bool             InpUseHTFFilter    = true;           // Использовать фильтр HTF
input bool             InpAllowBuy        = true;           // Разрешить покупки
input bool             InpAllowSell       = true;           // Разрешить продажи
input double           InpStopLossPoints  = 0.0;            // Стоп-лосс в пунктах (0 = без SL)
input double           InpTakeProfitPoints= 0.0;            // Тейк-профит в пунктах (0 = без TP)
input uint             InpMaxSpreadPoints = 50;             // Максимальный спред в пунктах
input ulong            InpMagic           = 560015;         // Магик-номер
input bool             InpUseSound        = true;           // Воспроизводить звук при входе
input string           InpSoundFile       = "alert.wav";    // Файл звукового сигнала
input bool             InpPrintLog        = true;           // Логировать события

CTrade trade;

datetime g_lastBarTime = 0;

bool CalcEnd(const double &price[], int shift, int len, int available, double &end_val)
{
   if(len < 2 || shift < 0)
      return false;

   if(shift + len > available)
      return false;

   double sumX    = 0.0;
   double sumY    = 0.0;
   double sumXSqr = 0.0;
   double sumXY   = 0.0;

   for(int i = 0; i < len; ++i)
   {
      double price_val = price[shift + i];
      if(price_val <= 0.0)
         return false;

      double log_val = MathLog(price_val);
      double per     = i + 1.0;

      sumX    += per;
      sumY    += log_val;
      sumXSqr += per * per;
      sumXY   += log_val * per;
   }

   double denom = len * sumXSqr - sumX * sumX;
   if(MathAbs(denom) < DBL_EPSILON)
      return false;

   double slope     = (len * sumXY - sumX * sumY) / denom;
   double average   = sumY / len;
   double intercept = average - slope * sumX / len + slope;

   end_val = MathExp(intercept);
   return MathIsValidNumber(end_val);
}

bool GetDiff(const double &price[], int len, int available, int shift, double &diff)
{
   double end_curr, end_curr3;
   if(!CalcEnd(price, shift, len, available, end_curr))
      return false;
   if(!CalcEnd(price, shift + 3, len, available, end_curr3))
      return false;

   diff = end_curr - end_curr3;
   return true;
}

bool GetHTFDirection(int len, bool &htf_up, bool &htf_down)
{
   const int needed = len + 8;
   double htf_close[];
   ArraySetAsSeries(htf_close, true);

   int copied = CopyClose(_Symbol, InpHTF, 0, needed, htf_close);
   if(copied < len + 4)
      return false;

   double end_curr, end_prev3;
   if(!CalcEnd(htf_close, 1, len, copied, end_curr))
      return false;
   if(!CalcEnd(htf_close, 1 + 3, len, copied, end_prev3))
      return false;

   htf_up   = (end_curr > end_prev3);
   htf_down = (end_curr < end_prev3);
   return true;
}

void PrintLog(const string text)
{
   if(InpPrintLog)
      Print(text);
}

bool CheckSpread()
{
   double spreadPoints = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   return (spreadPoints <= InpMaxSpreadPoints);
}

void ClosePositionIfOpposite(bool want_buy)
{
   if(!PositionSelect(_Symbol))
      return;

   long pos_type = PositionGetInteger(POSITION_TYPE);
   if((want_buy && pos_type == POSITION_TYPE_SELL) || (!want_buy && pos_type == POSITION_TYPE_BUY))
   {
      PrintLog(StringFormat("Закрываю позицию %s перед открытием %s", pos_type == POSITION_TYPE_BUY ? "BUY" : "SELL", want_buy ? "BUY" : "SELL"));
      trade.PositionClose(_Symbol);
   }
}

void OpenTrade(bool is_buy)
{
   if(!CheckSpread())
   {
      PrintLog("Спред превышает допустимый предел, пропуск входа");
      return;
   }

   if(PositionSelect(_Symbol))
   {
      long pos_type = PositionGetInteger(POSITION_TYPE);
      if((is_buy && pos_type == POSITION_TYPE_BUY) || (!is_buy && pos_type == POSITION_TYPE_SELL))
      {
         PrintLog("Позиция в ту же сторону уже открыта, вход пропущен");
         return;
      }
   }

   double price = is_buy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = 0.0;
   double tp = 0.0;
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   if(InpStopLossPoints > 0.0)
   {
      sl = is_buy ? price - InpStopLossPoints * point : price + InpStopLossPoints * point;
      sl = NormalizeDouble(sl, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   }

   if(InpTakeProfitPoints > 0.0)
   {
      tp = is_buy ? price + InpTakeProfitPoints * point : price - InpTakeProfitPoints * point;
      tp = NormalizeDouble(tp, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(10);

   bool result = is_buy ? trade.Buy(InpLots, _Symbol, price, sl, tp) : trade.Sell(InpLots, _Symbol, price, sl, tp);

   if(result)
   {
      PrintLog(StringFormat("Открыта позиция %s Lot=%.2f по цене %.5f", is_buy ? "BUY" : "SELL", InpLots, price));
      if(InpUseSound && InpSoundFile != "")
         PlaySound(InpSoundFile);
   }
   else
   {
      PrintLog(StringFormat("Не удалось открыть позицию %s. Ошибка %d", is_buy ? "BUY" : "SELL", GetLastError()));
   }
}

void OnTick()
{
   datetime bar_time = iTime(_Symbol, _Period, 0);
   if(bar_time == g_lastBarTime)
      return;

   if(iBarShift(_Symbol, _Period, g_lastBarTime, false) == 0)
      return;

   g_lastBarTime = bar_time;

   const int needed = InpLength + 8;
   double close_arr[];
   ArraySetAsSeries(close_arr, true);

   int copied = CopyClose(_Symbol, _Period, 0, needed, close_arr);
   if(copied < InpLength + 4)
   {
      PrintLog("Недостаточно данных для расчета регрессии");
      return;
   }

   double diff_curr, diff_prev;
   if(!GetDiff(close_arr, InpLength, copied, 1, diff_curr))
      return;
   if(!GetDiff(close_arr, InpLength, copied, 2, diff_prev))
      return;

   bool up_sig_raw = (diff_prev <= 0.0 && diff_curr > 0.0);
   bool dn_sig_raw = (diff_prev >= 0.0 && diff_curr < 0.0);

   bool allow_up = InpAllowBuy;
   bool allow_dn = InpAllowSell;

   if(InpUseHTFFilter)
   {
      bool htf_up = false, htf_dn = false;
      if(!GetHTFDirection(InpLength, htf_up, htf_dn))
         return;

      allow_up = allow_up && htf_up;
      allow_dn = allow_dn && htf_dn;
   }

   if(up_sig_raw && allow_up)
   {
      ClosePositionIfOpposite(true);
      OpenTrade(true);
   }

   if(dn_sig_raw && allow_dn)
   {
      ClosePositionIfOpposite(false);
      OpenTrade(false);
   }
}

void OnDeinit(const int reason)
{
   trade.PositionClose(_Symbol);
}
