#property strict

input double           InpLots             = 0.10;          // Размер позиции
input int              InpLength           = 100;           // Длина выборки логарифмической регрессии
input int              InpHTF              = PERIOD_H4;     // Старший таймфрейм для фильтра
input bool             InpUseHTFFilter     = true;          // Использовать фильтр HTF
input bool             InpAllowBuy         = true;          // Разрешить покупки
input bool             InpAllowSell        = true;          // Разрешить продажи
input double           InpStopLossPoints   = 0.0;           // Стоп-лосс (0 = без SL)
input double           InpTakeProfitPoints = 0.0;           // Тейк-профит (0 = без TP)
input int              InpMaxSpreadPoints  = 50;            // Максимальный спред (в пунктах)
input int              InpSlippage         = 3;             // Допустимое проскальзывание
input int              InpMagic            = 560015;        // Магик-номер
input bool             InpUseSound         = true;          // Воспроизводить звук при входе
input string           InpSoundFile        = "alert.wav";   // Файл звукового сигнала
input bool             InpPrintLog         = true;          // Логировать события

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

   int copied = CopyClose(Symbol(), InpHTF, 0, needed, htf_close);
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
   RefreshRates();
   double spreadPoints = (Ask - Bid) / Point;
   return (spreadPoints <= InpMaxSpreadPoints);
}

bool HasPosition(bool isBuy)
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;

      if(OrderSymbol() != Symbol() || OrderMagicNumber() != InpMagic)
         continue;

      if((isBuy && OrderType() == OP_BUY) || (!isBuy && OrderType() == OP_SELL))
         return true;
   }
   return false;
}

void CloseOppositePositions(bool want_buy)
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;

      if(OrderSymbol() != Symbol() || OrderMagicNumber() != InpMagic)
         continue;

      int type = OrderType();
      if((want_buy && type == OP_SELL) || (!want_buy && type == OP_BUY))
      {
         RefreshRates();
         double price = (type == OP_BUY) ? Bid : Ask;
         if(!OrderClose(OrderTicket(), OrderLots(), price, InpSlippage, clrOrange))
            PrintLog(StringFormat("Не удалось закрыть ордер %d. Ошибка %d", OrderTicket(), GetLastError()));
      }
   }
}

void CloseAllPositions()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES))
         continue;

      if(OrderSymbol() != Symbol() || OrderMagicNumber() != InpMagic)
         continue;

      int type = OrderType();
      RefreshRates();
      double price = (type == OP_BUY) ? Bid : Ask;
      if(!OrderClose(OrderTicket(), OrderLots(), price, InpSlippage, clrRed))
         PrintLog(StringFormat("Не удалось закрыть ордер %d при деинициализации. Ошибка %d", OrderTicket(), GetLastError()));
   }
}

void OpenTrade(bool isBuy)
{
   if(!CheckSpread())
   {
      PrintLog("Спред превышает допустимый предел, вход отменён");
      return;
   }

   if(HasPosition(isBuy))
   {
      PrintLog("Уже есть позиция в том же направлении");
      return;
   }

   RefreshRates();
   double price  = isBuy ? Ask : Bid;
   double point  = Point;
   int    digits = Digits;

   double sl = 0.0;
   double tp = 0.0;

   if(InpStopLossPoints > 0.0)
   {
      sl = isBuy ? price - InpStopLossPoints * point : price + InpStopLossPoints * point;
      sl = NormalizeDouble(sl, digits);
   }

   if(InpTakeProfitPoints > 0.0)
   {
      tp = isBuy ? price + InpTakeProfitPoints * point : price - InpTakeProfitPoints * point;
      tp = NormalizeDouble(tp, digits);
   }

   int type   = isBuy ? OP_BUY : OP_SELL;
   int ticket = OrderSend(Symbol(), type, InpLots, price, InpSlippage, sl, tp, "LogReg MTF EA", InpMagic, 0, isBuy ? clrGreen : clrRed);

   if(ticket < 0)
   {
      PrintLog(StringFormat("OrderSend(%s) ошибка %d", isBuy ? "BUY" : "SELL", GetLastError()));
   }
   else
   {
      PrintLog(StringFormat("Открыт ордер %d %s lot=%.2f по цене %.5f", ticket, isBuy ? "BUY" : "SELL", InpLots, price));
      if(InpUseSound && InpSoundFile != "")
         PlaySound(InpSoundFile);
   }
}

int OnInit()
{
   g_lastBarTime = 0;
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   CloseAllPositions();
}

void OnTick()
{
   datetime bar_time = Time[0];
   if(bar_time == g_lastBarTime)
      return;

   g_lastBarTime = bar_time;

   const int needed = InpLength + 8;
   double close_arr[];
   ArraySetAsSeries(close_arr, true);

   int copied = CopyClose(Symbol(), Period(), 0, needed, close_arr);
   if(copied < InpLength + 4)
   {
      PrintLog("Недостаточно данных для расчёта регрессии");
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
      CloseOppositePositions(true);
      OpenTrade(true);
   }

   if(dn_sig_raw && allow_dn)
   {
      CloseOppositePositions(false);
      OpenTrade(false);
   }
}
