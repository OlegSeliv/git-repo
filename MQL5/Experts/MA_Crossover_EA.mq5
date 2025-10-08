//+------------------------------------------------------------------+
//|                                                MA_Crossover_EA    |
//|                                    Simple MA crossover with RM    |
//+------------------------------------------------------------------+
#property strict
#property version   "1.0"
#property description "Moving Average crossover EA with risk management and trailing stop"

#include <Trade/Trade.mqh>

input string            InpSymbol               = _Symbol;               // Торговый символ
input ENUM_TIMEFRAMES   InpTimeframe            = PERIOD_CURRENT;        // Таймфрейм

input int               InpFastMAPeriod         = 20;                    // Быстрая МА
input int               InpSlowMAPeriod         = 50;                    // Медленная МА
input ENUM_MA_METHOD    InpMAMethod             = MODE_EMA;              // Метод МА
input ENUM_APPLIED_PRICE InpAppliedPrice        = PRICE_CLOSE;           // Цена для МА

input int               InpSLPoints             = 500;                   // Стоп-лосс (пункты)
input int               InpTPPoints             = 1000;                  // Тейк-профит (пункты)

input double            InpRiskPercent          = 1.0;                   // Риск на сделку, % от баланса (0 = фикс. лот)
input double            InpFixedLots            = 0.10;                  // Фиксированный лот (если риск 0)
input long              InpMagicNumber          = 20251008;              // Магик

input bool              InpAllowLong            = true;                  // Разрешить покупки
input bool              InpAllowShort           = true;                  // Разрешить продажи
input bool              InpReverseOnSignal      = true;                  // Разворот при противоположном сигнале
input bool              InpOnlyOnePosition      = true;                  // Только одна позиция по символу
input bool              InpTradeOnlyOnNewBar    = true;                  // Торговать только на новом баре

input bool              InpUseTrailingStop      = true;                  // Включить трейлинг-стоп
input int               InpTrailingStartPoints  = 400;                   // Старт трейлинга (пункты в профите)
input int               InpTrailingStepPoints   = 200;                   // Шаг подтяжки SL (пункты)

input int               InpDeviationPoints      = 20;                    // Допустимое отклонение (пункты)
input string            InpOrderComment         = "MA_Crossover_EA";    // Комментарий к ордерам

//--- Глобальные
CTrade                  trade;
int                     g_fastMAHandle = INVALID_HANDLE;
int                     g_slowMAHandle = INVALID_HANDLE;
string                  g_symbol;
ENUM_TIMEFRAMES         g_timeframe;
double                  g_point        = 0.0;
int                     g_digits       = 0;
datetime                g_lastBarTime  = 0;

//+------------------------------------------------------------------+
//| Вспомогательные функции                                          |
//+------------------------------------------------------------------+
bool IsNewBar()
{
	datetime times[];
	if(CopyTime(g_symbol, g_timeframe, 0, 1, times) <= 0)
		return(false);
	if(times[0] != g_lastBarTime)
	{
		g_lastBarTime = times[0];
		return(true);
	}
	return(false);
}

double NormalizeVolume(double volume)
{
	double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
	double minv = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
	double maxv = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
	if(step <= 0.0) step = 0.01;
	if(volume < minv) volume = minv;
	if(volume > maxv) volume = maxv;
	// Округляем вниз к шагу, чтобы не превышать рассчитанный риск
	volume = MathFloor(volume / step + 1e-9) * step;
	int volDigits = (int)SymbolInfoInteger(g_symbol, SYMBOL_VOLUME_DIGITS);
	return(NormalizeDouble(volume, volDigits));
}

double CalculateLotSizeByRisk(int slPoints)
{
	if(InpRiskPercent <= 0.0 || slPoints <= 0)
		return(NormalizeVolume(InpFixedLots));

	double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
	double riskMoney = balance * InpRiskPercent / 100.0;
	double tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
	double tickSize  = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
	double point     = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
	if(tickValue <= 0.0 || tickSize <= 0.0 || point <= 0.0)
		return(NormalizeVolume(InpFixedLots));

	// Стоимость пункта на 1 лот
	double valuePerPointPerLot = tickValue * (point / tickSize);
	if(valuePerPointPerLot <= 0.0)
		return(NormalizeVolume(InpFixedLots));

	double lots = riskMoney / (slPoints * valuePerPointPerLot);
	lots = NormalizeVolume(lots);
	if(lots <= 0.0)
		lots = NormalizeVolume(SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN));
	return(lots);
}

bool GetCrossSignals(bool &crossUp, bool &crossDown)
{
	crossUp = false;
	crossDown = false;
	if(g_fastMAHandle == INVALID_HANDLE || g_slowMAHandle == INVALID_HANDLE)
		return(false);

	double fastArr[3];
	double slowArr[3];
	int copiedFast = CopyBuffer(g_fastMAHandle, 0, 0, 3, fastArr);
	int copiedSlow = CopyBuffer(g_slowMAHandle, 0, 0, 3, slowArr);
	if(copiedFast < 3 || copiedSlow < 3)
		return(false);

	// Используем закрытые бары: 1 и 2
	if(!MathIsValidNumber(fastArr[1]) || !MathIsValidNumber(fastArr[2]) ||
	   !MathIsValidNumber(slowArr[1]) || !MathIsValidNumber(slowArr[2]))
		return(false);

	crossUp   = (fastArr[2] <= slowArr[2]) && (fastArr[1] > slowArr[1]);
	crossDown = (fastArr[2] >= slowArr[2]) && (fastArr[1] < slowArr[1]);
	return(true);
}

bool OpenPosition(ENUM_ORDER_TYPE orderType)
{
	double price = 0.0;
	double sl    = 0.0;
	double tp    = 0.0;
	double ask   = 0.0;
	double bid   = 0.0;
	SymbolInfoDouble(g_symbol, SYMBOL_ASK, ask);
	SymbolInfoDouble(g_symbol, SYMBOL_BID, bid);

	int slPoints = InpSLPoints;
	int tpPoints = InpTPPoints;

	double lots = CalculateLotSizeByRisk(slPoints);
	if(lots <= 0.0)
	{
		Print("[EA] Lots <= 0, skip open");
		return(false);
	}

	if(orderType == ORDER_TYPE_BUY)
	{
		price = ask;
		if(slPoints > 0) sl = NormalizeDouble(price - slPoints * g_point, g_digits);
		if(tpPoints > 0) tp = NormalizeDouble(price + tpPoints * g_point, g_digits);
		bool ok = trade.Buy(lots, g_symbol, 0.0, sl, tp, InpOrderComment);
		if(!ok)
		{
			PrintFormat("[EA] Buy failed: %d (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
			return(false);
		}
		PrintFormat("[EA] Buy opened: lots=%.2f price=%.5f SL=%.5f TP=%.5f", lots, price, sl, tp);
		return(true);
	}
	else if(orderType == ORDER_TYPE_SELL)
	{
		price = bid;
		if(slPoints > 0) sl = NormalizeDouble(price + slPoints * g_point, g_digits);
		if(tpPoints > 0) tp = NormalizeDouble(price - tpPoints * g_point, g_digits);
		bool ok = trade.Sell(lots, g_symbol, 0.0, sl, tp, InpOrderComment);
		if(!ok)
		{
			PrintFormat("[EA] Sell failed: %d (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
			return(false);
		}
		PrintFormat("[EA] Sell opened: lots=%.2f price=%.5f SL=%.5f TP=%.5f", lots, price, sl, tp);
		return(true);
	}
	return(false);
}

void UpdateTrailingStop()
{
	if(!InpUseTrailingStop)
		return;
	if(!PositionSelect(g_symbol))
		return;

	ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
	double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
	double sl        = PositionGetDouble(POSITION_SL);
	double tp        = PositionGetDouble(POSITION_TP);

	double bid = 0.0, ask = 0.0;
	SymbolInfoDouble(g_symbol, SYMBOL_BID, bid);
	SymbolInfoDouble(g_symbol, SYMBOL_ASK, ask);

	if(posType == POSITION_TYPE_BUY)
	{
		double profitPoints = (bid - openPrice) / g_point;
		if(profitPoints >= InpTrailingStartPoints)
		{
			double newSL = NormalizeDouble(bid - InpTrailingStepPoints * g_point, g_digits);
			if(sl == 0.0 || newSL > sl)
			{
				if(trade.PositionModify(g_symbol, newSL, tp))
					PrintFormat("[EA] Trailing BUY: SL -> %.5f", newSL);
				else
					PrintFormat("[EA] Trailing BUY failed: %d (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
			}
		}
	}
	else if(posType == POSITION_TYPE_SELL)
	{
		double profitPoints = (openPrice - ask) / g_point;
		if(profitPoints >= InpTrailingStartPoints)
		{
			double newSL = NormalizeDouble(ask + InpTrailingStepPoints * g_point, g_digits);
			if(sl == 0.0 || newSL < sl)
			{
				if(trade.PositionModify(g_symbol, newSL, tp))
					PrintFormat("[EA] Trailing SELL: SL -> %.5f", newSL);
				else
					PrintFormat("[EA] Trailing SELL failed: %d (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
			}
		}
	}
}

void ManageSignals()
{
	bool crossUp = false, crossDown = false;
	if(!GetCrossSignals(crossUp, crossDown))
		return;

	if(!InpAllowLong)  crossUp = false;
	if(!InpAllowShort) crossDown = false;

	bool hasPos = PositionSelect(g_symbol);
	if(!hasPos)
	{
		if(crossUp)
			OpenPosition(ORDER_TYPE_BUY);
		else if(crossDown)
			OpenPosition(ORDER_TYPE_SELL);
		return;
	}

	ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
	if(crossUp)
	{
		if(posType == POSITION_TYPE_SELL)
		{
			if(InpReverseOnSignal)
			{
				if(trade.PositionClose(g_symbol))
					OpenPosition(ORDER_TYPE_BUY);
				else
					PrintFormat("[EA] Close SELL failed: %d (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
			}
			else if(!InpOnlyOnePosition)
			{
				OpenPosition(ORDER_TYPE_BUY);
			}
		}
	}
	else if(crossDown)
	{
		if(posType == POSITION_TYPE_BUY)
		{
			if(InpReverseOnSignal)
			{
				if(trade.PositionClose(g_symbol))
					OpenPosition(ORDER_TYPE_SELL);
				else
					PrintFormat("[EA] Close BUY failed: %d (%s)", trade.ResultRetcode(), trade.ResultRetcodeDescription());
			}
			else if(!InpOnlyOnePosition)
			{
				OpenPosition(ORDER_TYPE_SELL);
			}
		}
	}
}

//+------------------------------------------------------------------+
//| Стартовые функции эксперта                                       |
//+------------------------------------------------------------------+
int OnInit()
{
	g_symbol    = InpSymbol;
	g_timeframe = InpTimeframe;
	g_point     = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
	g_digits    = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);

	trade.SetExpertMagicNumber((ulong)InpMagicNumber);
	trade.SetDeviationInPoints(InpDeviationPoints);

	g_fastMAHandle = iMA(g_symbol, g_timeframe, InpFastMAPeriod, 0, InpMAMethod, InpAppliedPrice);
	g_slowMAHandle = iMA(g_symbol, g_timeframe, InpSlowMAPeriod, 0, InpMAMethod, InpAppliedPrice);
	if(g_fastMAHandle == INVALID_HANDLE || g_slowMAHandle == INVALID_HANDLE)
	{
		Print("[EA] Failed to create MA handles");
		return(INIT_FAILED);
	}
	PrintFormat("[EA] Init OK on %s, TF=%d", g_symbol, (int)g_timeframe);
	return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
	if(g_fastMAHandle != INVALID_HANDLE)
		IndicatorRelease(g_fastMAHandle);
	if(g_slowMAHandle != INVALID_HANDLE)
		IndicatorRelease(g_slowMAHandle);
}

void OnTick()
{
	// Трейлинг обрабатываем на каждом тике
	UpdateTrailingStop();

	// Торговые сигналы — по новому бару (опционально)
	if(InpTradeOnlyOnNewBar)
	{
		if(!IsNewBar())
			return;
	}
	ManageSignals();
}

//+------------------------------------------------------------------+
