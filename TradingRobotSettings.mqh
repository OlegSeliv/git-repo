//+------------------------------------------------------------------+
//|                                         TradingRobotSettings.mqh |
//|                                    Copyright 2025, Trading Robot |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Trading Robot"
#property link      "https://www.mql5.com"

//+------------------------------------------------------------------+
//| Структура для хранения настроек робота                          |
//+------------------------------------------------------------------+
struct RobotSettings
{
   //--- Основные параметры
   double         LotSize;           // Размер лота
   int            MagicNumber;       // Уникальный идентификатор
   string         Comment;           // Комментарий к сделкам
   
   //--- Параметры стратегии
   int            FastMAPeriod;      // Период быстрой MA
   int            SlowMAPeriod;      // Период медленной MA
   ENUM_MA_METHOD MAMethod;          // Метод расчета MA
   ENUM_APPLIED_PRICE MAPrice;       // Цена для расчета
   
   //--- Управление рисками
   double         StopLoss;          // Stop Loss в пунктах
   double         TakeProfit;        // Take Profit в пунктах
   double         TrailingStop;      // Trailing Stop в пунктах
   double         MaxRiskPercent;    // Максимальный риск на сделку
   int            MaxPositions;      // Максимум открытых позиций
   
   //--- Временные фильтры
   bool           UseTimeFilter;     // Использовать временной фильтр
   int            StartHour;         // Час начала торговли
   int            StartMinute;       // Минута начала
   int            EndHour;           // Час окончания
   int            EndMinute;         // Минута окончания
   
   //--- Дополнительные параметры
   bool           UseBreakeven;      // Использовать безубыток
   double         BreakevenPoints;   // Пункты для безубытка
   double         BreakevenProfit;   // Прибыль в пунктах для безубытка
   
   //--- Фильтры входа
   bool           UseSpreadFilter;   // Фильтр по спреду
   int            MaxSpread;         // Максимальный спред
   bool           UseNewsFilter;     // Фильтр новостей
   int            NewsBeforeMinutes; // Минут до новости
   int            NewsAfterMinutes;  // Минут после новости
};

//+------------------------------------------------------------------+
//| Структура для статистики торговли                               |
//+------------------------------------------------------------------+
struct TradingStatistics
{
   int            TotalTrades;       // Всего сделок
   int            WinningTrades;     // Прибыльных сделок
   int            LosingTrades;      // Убыточных сделок
   double         TotalProfit;       // Общая прибыль
   double         TotalLoss;         // Общий убыток
   double         MaxDrawdown;       // Максимальная просадка
   double         ProfitFactor;      // Профит-фактор
   double         WinRate;           // Процент выигрышей
   datetime       StartTime;         // Время начала статистики
   double         InitialBalance;    // Начальный баланс
};

//+------------------------------------------------------------------+
//| Перечисление режимов работы робота                              |
//+------------------------------------------------------------------+
enum ENUM_ROBOT_MODE
{
   MODE_NORMAL,         // Обычный режим
   MODE_CONSERVATIVE,   // Консервативный режим
   MODE_AGGRESSIVE,     // Агрессивный режим
   MODE_SCALPING,       // Скальпинг
   MODE_TESTING         // Режим тестирования
};

//+------------------------------------------------------------------+
//| Перечисление типов сигналов                                     |
//+------------------------------------------------------------------+
enum ENUM_SIGNAL_TYPE
{
   SIGNAL_NONE,         // Нет сигнала
   SIGNAL_BUY,          // Сигнал на покупку
   SIGNAL_SELL,         // Сигнал на продажу
   SIGNAL_CLOSE_BUY,    // Закрыть покупки
   SIGNAL_CLOSE_SELL,   // Закрыть продажи
   SIGNAL_CLOSE_ALL     // Закрыть все позиции
};

//+------------------------------------------------------------------+
//| Класс для управления настройками                                |
//+------------------------------------------------------------------+
class CRobotSettingsManager
{
private:
   RobotSettings  m_settings;
   string         m_fileName;
   
public:
   //--- Конструктор
   CRobotSettingsManager(string fileName = "robot_settings.set")
   {
      m_fileName = fileName;
      SetDefaultSettings();
   }
   
   //--- Установка настроек по умолчанию
   void SetDefaultSettings()
   {
      m_settings.LotSize = 0.01;
      m_settings.MagicNumber = 123456;
      m_settings.Comment = "MA Robot";
      
      m_settings.FastMAPeriod = 10;
      m_settings.SlowMAPeriod = 30;
      m_settings.MAMethod = MODE_SMA;
      m_settings.MAPrice = PRICE_CLOSE;
      
      m_settings.StopLoss = 50;
      m_settings.TakeProfit = 100;
      m_settings.TrailingStop = 30;
      m_settings.MaxRiskPercent = 2.0;
      m_settings.MaxPositions = 1;
      
      m_settings.UseTimeFilter = false;
      m_settings.StartHour = 9;
      m_settings.StartMinute = 0;
      m_settings.EndHour = 22;
      m_settings.EndMinute = 0;
      
      m_settings.UseBreakeven = false;
      m_settings.BreakevenPoints = 20;
      m_settings.BreakevenProfit = 5;
      
      m_settings.UseSpreadFilter = true;
      m_settings.MaxSpread = 20;
      m_settings.UseNewsFilter = false;
      m_settings.NewsBeforeMinutes = 30;
      m_settings.NewsAfterMinutes = 30;
   }
   
   //--- Сохранение настроек в файл
   bool SaveSettings()
   {
      int handle = FileOpen(m_fileName, FILE_WRITE|FILE_BIN);
      if(handle == INVALID_HANDLE)
      {
         Print("Ошибка открытия файла для записи: ", m_fileName);
         return false;
      }
      
      FileWriteStruct(handle, m_settings);
      FileClose(handle);
      
      Print("Настройки сохранены в файл: ", m_fileName);
      return true;
   }
   
   //--- Загрузка настроек из файла
   bool LoadSettings()
   {
      if(!FileIsExist(m_fileName))
      {
         Print("Файл настроек не найден: ", m_fileName);
         return false;
      }
      
      int handle = FileOpen(m_fileName, FILE_READ|FILE_BIN);
      if(handle == INVALID_HANDLE)
      {
         Print("Ошибка открытия файла для чтения: ", m_fileName);
         return false;
      }
      
      FileReadStruct(handle, m_settings);
      FileClose(handle);
      
      Print("Настройки загружены из файла: ", m_fileName);
      return true;
   }
   
   //--- Получение настроек
   RobotSettings GetSettings() { return m_settings; }
   
   //--- Установка настроек
   void SetSettings(const RobotSettings &settings) { m_settings = settings; }
   
   //--- Валидация настроек
   bool ValidateSettings()
   {
      bool isValid = true;
      
      if(m_settings.LotSize <= 0)
      {
         Print("Ошибка: Размер лота должен быть больше 0");
         isValid = false;
      }
      
      if(m_settings.FastMAPeriod >= m_settings.SlowMAPeriod)
      {
         Print("Ошибка: Период быстрой MA должен быть меньше периода медленной MA");
         isValid = false;
      }
      
      if(m_settings.MaxRiskPercent < 0 || m_settings.MaxRiskPercent > 100)
      {
         Print("Ошибка: Максимальный риск должен быть от 0 до 100%");
         isValid = false;
      }
      
      if(m_settings.MaxPositions < 1)
      {
         Print("Ошибка: Максимум позиций должен быть не менее 1");
         isValid = false;
      }
      
      return isValid;
   }
   
   //--- Печать настроек
   void PrintSettings()
   {
      Print("========== Текущие настройки робота ==========");
      Print("Размер лота: ", m_settings.LotSize);
      Print("Magic Number: ", m_settings.MagicNumber);
      Print("Быстрая MA: ", m_settings.FastMAPeriod);
      Print("Медленная MA: ", m_settings.SlowMAPeriod);
      Print("Stop Loss: ", m_settings.StopLoss);
      Print("Take Profit: ", m_settings.TakeProfit);
      Print("Trailing Stop: ", m_settings.TrailingStop);
      Print("Макс. риск: ", m_settings.MaxRiskPercent, "%");
      Print("Макс. позиций: ", m_settings.MaxPositions);
      Print("Временной фильтр: ", m_settings.UseTimeFilter ? "Включен" : "Выключен");
      Print("===============================================");
   }
};

//+------------------------------------------------------------------+
//| Класс для управления статистикой                                |
//+------------------------------------------------------------------+
class CTradingStatisticsManager
{
private:
   TradingStatistics m_stats;
   
public:
   //--- Конструктор
   CTradingStatisticsManager()
   {
      ResetStatistics();
   }
   
   //--- Сброс статистики
   void ResetStatistics()
   {
      m_stats.TotalTrades = 0;
      m_stats.WinningTrades = 0;
      m_stats.LosingTrades = 0;
      m_stats.TotalProfit = 0;
      m_stats.TotalLoss = 0;
      m_stats.MaxDrawdown = 0;
      m_stats.ProfitFactor = 0;
      m_stats.WinRate = 0;
      m_stats.StartTime = TimeCurrent();
      m_stats.InitialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   }
   
   //--- Обновление статистики после сделки
   void UpdateStatistics(double profit)
   {
      m_stats.TotalTrades++;
      
      if(profit > 0)
      {
         m_stats.WinningTrades++;
         m_stats.TotalProfit += profit;
      }
      else if(profit < 0)
      {
         m_stats.LosingTrades++;
         m_stats.TotalLoss += MathAbs(profit);
      }
      
      //--- Расчет профит-фактора
      if(m_stats.TotalLoss > 0)
         m_stats.ProfitFactor = m_stats.TotalProfit / m_stats.TotalLoss;
      else if(m_stats.TotalProfit > 0)
         m_stats.ProfitFactor = 999.99;
      
      //--- Расчет процента выигрышей
      if(m_stats.TotalTrades > 0)
         m_stats.WinRate = (double)m_stats.WinningTrades / m_stats.TotalTrades * 100;
      
      //--- Обновление максимальной просадки
      double currentDrawdown = CalculateDrawdown();
      if(currentDrawdown > m_stats.MaxDrawdown)
         m_stats.MaxDrawdown = currentDrawdown;
   }
   
   //--- Расчет текущей просадки
   double CalculateDrawdown()
   {
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      
      if(balance > 0)
         return (balance - equity) / balance * 100;
      
      return 0;
   }
   
   //--- Получение статистики
   TradingStatistics GetStatistics() { return m_stats; }
   
   //--- Печать статистики
   void PrintStatistics()
   {
      Print("========== Статистика торговли ==========");
      Print("Всего сделок: ", m_stats.TotalTrades);
      Print("Прибыльных: ", m_stats.WinningTrades);
      Print("Убыточных: ", m_stats.LosingTrades);
      Print("Общая прибыль: ", DoubleToString(m_stats.TotalProfit, 2));
      Print("Общий убыток: ", DoubleToString(m_stats.TotalLoss, 2));
      Print("Профит-фактор: ", DoubleToString(m_stats.ProfitFactor, 2));
      Print("Процент выигрышей: ", DoubleToString(m_stats.WinRate, 1), "%");
      Print("Макс. просадка: ", DoubleToString(m_stats.MaxDrawdown, 2), "%");
      Print("=========================================");
   }
   
   //--- Сохранение статистики в файл
   bool SaveStatisticsToFile(string fileName = "trading_statistics.csv")
   {
      int handle = FileOpen(fileName, FILE_WRITE|FILE_CSV);
      if(handle == INVALID_HANDLE)
      {
         Print("Ошибка открытия файла статистики");
         return false;
      }
      
      //--- Заголовки
      if(FileSize(handle) == 0)
      {
         FileWrite(handle, "Date;Time;Total Trades;Winning;Losing;Total Profit;Total Loss;Profit Factor;Win Rate;Max Drawdown");
      }
      
      //--- Данные
      FileWrite(handle,
                TimeToString(TimeCurrent(), TIME_DATE),
                TimeToString(TimeCurrent(), TIME_MINUTES),
                m_stats.TotalTrades,
                m_stats.WinningTrades,
                m_stats.LosingTrades,
                DoubleToString(m_stats.TotalProfit, 2),
                DoubleToString(m_stats.TotalLoss, 2),
                DoubleToString(m_stats.ProfitFactor, 2),
                DoubleToString(m_stats.WinRate, 1),
                DoubleToString(m_stats.MaxDrawdown, 2));
      
      FileClose(handle);
      return true;
   }
};

//+------------------------------------------------------------------+
//| Утилиты для работы с ценами и расчетами                        |
//+------------------------------------------------------------------+
class CPriceUtils
{
public:
   //--- Нормализация цены
   static double NormalizePrice(double price, string symbol)
   {
      return NormalizeDouble(price, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
   }
   
   //--- Конвертация пунктов в цену
   static double PointsToPrice(int points, string symbol)
   {
      return points * SymbolInfoDouble(symbol, SYMBOL_POINT);
   }
   
   //--- Конвертация цены в пункты
   static int PriceToPoints(double price, string symbol)
   {
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point > 0)
         return (int)(price / point);
      return 0;
   }
   
   //--- Расчет размера лота по риску
   static double CalculateLotByRisk(double riskPercent, double stopLossPoints, string symbol)
   {
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double riskAmount = balance * riskPercent / 100.0;
      double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      
      if(tickValue > 0 && stopLossPoints > 0)
      {
         double lotSize = riskAmount / (stopLossPoints * tickValue);
         return NormalizeLot(lotSize, symbol);
      }
      
      return SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   }
   
   //--- Нормализация размера лота
   static double NormalizeLot(double lot, string symbol)
   {
      double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
      double stepLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      
      lot = MathMax(minLot, lot);
      lot = MathMin(maxLot, lot);
      lot = MathRound(lot / stepLot) * stepLot;
      
      return NormalizeDouble(lot, 2);
   }
   
   //--- Проверка достаточности маржи
   static bool CheckMargin(double lotSize, ENUM_ORDER_TYPE orderType, string symbol)
   {
      double price = (orderType == ORDER_TYPE_BUY) ? 
                     SymbolInfoDouble(symbol, SYMBOL_ASK) : 
                     SymbolInfoDouble(symbol, SYMBOL_BID);
      
      double margin;
      if(OrderCalcMargin(orderType, symbol, lotSize, price, margin))
      {
         double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
         return (freeMargin >= margin);
      }
      
      return false;
   }
};

//+------------------------------------------------------------------+
//| Класс для логирования                                           |
//+------------------------------------------------------------------+
class CLogger
{
private:
   string   m_logFileName;
   bool     m_enableLogging;
   int      m_logLevel;  // 0 - ERROR, 1 - WARNING, 2 - INFO, 3 - DEBUG
   
public:
   //--- Конструктор
   CLogger(string fileName = "robot_log.txt", bool enable = true, int level = 2)
   {
      m_logFileName = fileName;
      m_enableLogging = enable;
      m_logLevel = level;
   }
   
   //--- Логирование сообщения
   void Log(string message, int level = 2)
   {
      if(!m_enableLogging || level > m_logLevel)
         return;
      
      string levelStr;
      switch(level)
      {
         case 0: levelStr = "[ERROR]"; break;
         case 1: levelStr = "[WARNING]"; break;
         case 2: levelStr = "[INFO]"; break;
         case 3: levelStr = "[DEBUG]"; break;
         default: levelStr = "[UNKNOWN]";
      }
      
      string fullMessage = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + " " + 
                          levelStr + " " + message;
      
      //--- Вывод в журнал терминала
      Print(fullMessage);
      
      //--- Запись в файл
      int handle = FileOpen(m_logFileName, FILE_WRITE|FILE_READ|FILE_TXT);
      if(handle != INVALID_HANDLE)
      {
         FileSeek(handle, 0, SEEK_END);
         FileWriteString(handle, fullMessage + "\n");
         FileClose(handle);
      }
   }
   
   //--- Логирование ошибки
   void LogError(string message) { Log(message, 0); }
   
   //--- Логирование предупреждения
   void LogWarning(string message) { Log(message, 1); }
   
   //--- Логирование информации
   void LogInfo(string message) { Log(message, 2); }
   
   //--- Логирование отладки
   void LogDebug(string message) { Log(message, 3); }
   
   //--- Установка уровня логирования
   void SetLogLevel(int level) { m_logLevel = level; }
   
   //--- Включение/выключение логирования
   void EnableLogging(bool enable) { m_enableLogging = enable; }
};

//+------------------------------------------------------------------+