#property indicator_chart_window
#property indicator_plots 0

input int              InpLength        = 100;           // Длина выборки логарифмической регрессии
input ENUM_TIMEFRAMES  InpHTF           = PERIOD_H4;     // Старший таймфрейм
input bool             InpUseHTFFilter  = true;          // Использовать фильтр HTF
input bool             InpUseSound      = true;          // Включить звуковой сигнал
input string           InpSoundFile     = "alert.wav";  // Файл звукового сигнала

//--- служебные переменные для предотвращения повторных сигналов
datetime g_lastUpSignalTime   = 0;
datetime g_lastDownSignalTime = 0;

//--- расчет логарифмической регрессии
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

int OnInit()
{
   string headline = StringFormat("LogReg MTF Alerts (%s/%s)", EnumToString((ENUM_TIMEFRAMES)_Period), EnumToString(InpHTF));
   IndicatorSetString(INDICATOR_SHORTNAME, headline);
   return(INIT_SUCCEEDED);
}

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(rates_total <= InpLength + 4)
      return prev_calculated;

   //--- используем последний закрытый бар (shift = 1)
   const int shift_curr = 1;
   const int shift_prev = 2;

   double end_curr, end_curr3, end_prev, end_prev3;
   if(!CalcEnd(close, shift_curr, InpLength, rates_total, end_curr))
      return prev_calculated;
   if(!CalcEnd(close, shift_curr + 3, InpLength, rates_total, end_curr3))
      return prev_calculated;
   if(!CalcEnd(close, shift_prev, InpLength, rates_total, end_prev))
      return prev_calculated;
   if(!CalcEnd(close, shift_prev + 3, InpLength, rates_total, end_prev3))
      return prev_calculated;

   double diff_curr = end_curr - end_curr3;
   double diff_prev = end_prev - end_prev3;

   bool up_sig_raw = (diff_prev <= 0.0 && diff_curr > 0.0);
   bool dn_sig_raw = (diff_prev >= 0.0 && diff_curr < 0.0);

   bool allow_up   = true;
   bool allow_down = true;

   if(InpUseHTFFilter)
   {
      const int needed = InpLength + 8;
      double htf_close[];
      ArraySetAsSeries(htf_close, true);
      int copied = CopyClose(_Symbol, InpHTF, 0, needed, htf_close);
      if(copied < InpLength + 4)
         return prev_calculated;

      double end_htf_curr, end_htf_prev3;
      if(!CalcEnd(htf_close, 1, InpLength, copied, end_htf_curr))
         return prev_calculated;
      if(!CalcEnd(htf_close, 1 + 3, InpLength, copied, end_htf_prev3))
         return prev_calculated;

      allow_up   = (end_htf_curr > end_htf_prev3);
      allow_down = (end_htf_curr < end_htf_prev3);
   }

   datetime signal_time = time[shift_curr];

   string msg = "";

   if(up_sig_raw && allow_up && signal_time != g_lastUpSignalTime)
   {
      g_lastUpSignalTime = signal_time;
      msg = StringFormat("%s %s: LogReg UP сигнал на баре %s", _Symbol, EnumToString((ENUM_TIMEFRAMES)_Period), TimeToString(signal_time));
      Alert(msg);
      if(InpUseSound && InpSoundFile != "")
         PlaySound(InpSoundFile);
   }

   if(dn_sig_raw && allow_down && signal_time != g_lastDownSignalTime)
   {
      g_lastDownSignalTime = signal_time;
      msg = StringFormat("%s %s: LogReg DOWN сигнал на баре %s", _Symbol, EnumToString((ENUM_TIMEFRAMES)_Period), TimeToString(signal_time));
      Alert(msg);
      if(InpUseSound && InpSoundFile != "")
         PlaySound(InpSoundFile);
   }

   return rates_total;
}
