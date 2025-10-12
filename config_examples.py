"""
Примеры конфигураций для системы оптимизации торгового робота
Содержит готовые настройки для различных торговых стилей и рынков
"""

from market_adaptation_system import MarketRegime
from timing_optimization_system import TradingSession
from advanced_risk_management import RiskLevel
from realtime_monitoring_system import AlertLevel

# =============================================================================
# КОНФИГУРАЦИИ ДЛЯ РАЗЛИЧНЫХ ТОРГОВЫХ СТИЛЕЙ
# =============================================================================

# Конфигурация для скальпинга (быстрые сделки)
SCALPING_CONFIG = {
    'strategy_params': {
        'fast_period': 3,
        'slow_period': 8,
        'stop_loss_pct': 0.005,  # 0.5%
        'take_profit_pct': 0.01,  # 1%
    },
    'risk_management': {
        'max_risk_per_trade': 0.01,  # 1% от депозита
        'max_positions': 5,
        'daily_loss_limit': 0.03,  # 3%
        'risk_level': RiskLevel.HIGH
    },
    'timing': {
        'primary_hours': [9, 10, 11, 14, 15, 16],  # Лондон + Нью-Йорк
        'secondary_hours': [8, 12, 13, 17],
        'avoid_hours': [0, 1, 2, 3, 4, 5, 6, 7, 22, 23]
    },
    'alerts': {
        'drawdown_warning': 0.02,  # 2%
        'drawdown_critical': 0.05,  # 5%
        'daily_loss_warning': -200,  # $200
        'daily_loss_critical': -500   # $500
    }
}

# Конфигурация для дневной торговли
DAY_TRADING_CONFIG = {
    'strategy_params': {
        'fast_period': 10,
        'slow_period': 20,
        'stop_loss_pct': 0.02,  # 2%
        'take_profit_pct': 0.04,  # 4%
    },
    'risk_management': {
        'max_risk_per_trade': 0.02,  # 2% от депозита
        'max_positions': 3,
        'daily_loss_limit': 0.05,  # 5%
        'risk_level': RiskLevel.MEDIUM
    },
    'timing': {
        'primary_hours': [8, 9, 10, 11, 12, 13, 14, 15, 16],  # Лондон + Нью-Йорк
        'secondary_hours': [7, 17],
        'avoid_hours': [0, 1, 2, 3, 4, 5, 6, 21, 22, 23]
    },
    'alerts': {
        'drawdown_warning': 0.03,  # 3%
        'drawdown_critical': 0.08,  # 8%
        'daily_loss_warning': -300,  # $300
        'daily_loss_critical': -800   # $800
    }
}

# Конфигурация для свинг-торговли (среднесрочные позиции)
SWING_TRADING_CONFIG = {
    'strategy_params': {
        'fast_period': 20,
        'slow_period': 50,
        'stop_loss_pct': 0.03,  # 3%
        'take_profit_pct': 0.06,  # 6%
    },
    'risk_management': {
        'max_risk_per_trade': 0.03,  # 3% от депозита
        'max_positions': 2,
        'daily_loss_limit': 0.08,  # 8%
        'risk_level': RiskLevel.MEDIUM
    },
    'timing': {
        'primary_hours': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],  # Полный день
        'secondary_hours': [7, 18],
        'avoid_hours': [0, 1, 2, 3, 4, 5, 6, 19, 20, 21, 22, 23]
    },
    'alerts': {
        'drawdown_warning': 0.05,  # 5%
        'drawdown_critical': 0.12,  # 12%
        'daily_loss_warning': -500,  # $500
        'daily_loss_critical': -1200  # $1200
    }
}

# Конфигурация для позиционной торговли (долгосрочные позиции)
POSITION_TRADING_CONFIG = {
    'strategy_params': {
        'fast_period': 50,
        'slow_period': 200,
        'stop_loss_pct': 0.05,  # 5%
        'take_profit_pct': 0.10,  # 10%
    },
    'risk_management': {
        'max_risk_per_trade': 0.05,  # 5% от депозита
        'max_positions': 1,
        'daily_loss_limit': 0.10,  # 10%
        'risk_level': RiskLevel.LOW
    },
    'timing': {
        'primary_hours': [9, 10, 11, 12, 13, 14, 15, 16],  # Основные часы
        'secondary_hours': [8, 17],
        'avoid_hours': [0, 1, 2, 3, 4, 5, 6, 7, 18, 19, 20, 21, 22, 23]
    },
    'alerts': {
        'drawdown_warning': 0.08,  # 8%
        'drawdown_critical': 0.15,  # 15%
        'daily_loss_warning': -800,  # $800
        'daily_loss_critical': -2000  # $2000
    }
}

# =============================================================================
# КОНФИГУРАЦИИ ДЛЯ РАЗЛИЧНЫХ РЫНКОВ
# =============================================================================

# Конфигурация для валютного рынка (Forex)
FOREX_CONFIG = {
    'market_specific': {
        'sessions': {
            'asian': {'start': 0, 'end': 8, 'volatility': 0.15},
            'london': {'start': 8, 'end': 16, 'volatility': 0.25},
            'new_york': {'start': 13, 'end': 21, 'volatility': 0.22},
            'overlap': {'start': 13, 'end': 16, 'volatility': 0.35}
        },
        'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'],
        'spread_impact': 0.0001,  # 1 пип
        'commission': 0.0001
    },
    'regime_parameters': {
        MarketRegime.TRENDING: {
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.06,
            'position_size': 0.15
        },
        MarketRegime.RANGING: {
            'stop_loss_pct': 0.015,
            'take_profit_pct': 0.03,
            'position_size': 0.08
        },
        MarketRegime.HIGH_VOLATILITY: {
            'stop_loss_pct': 0.04,
            'take_profit_pct': 0.08,
            'position_size': 0.05
        }
    }
}

# Конфигурация для фондового рынка
STOCK_CONFIG = {
    'market_specific': {
        'sessions': {
            'pre_market': {'start': 4, 'end': 9, 'volatility': 0.20},
            'regular': {'start': 9, 'end': 16, 'volatility': 0.25},
            'after_hours': {'start': 16, 'end': 20, 'volatility': 0.30}
        },
        'symbols': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
        'spread_impact': 0.01,  # $0.01
        'commission': 0.005  # $0.005 за акцию
    },
    'regime_parameters': {
        MarketRegime.TRENDING: {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10,
            'position_size': 0.20
        },
        MarketRegime.RANGING: {
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.06,
            'position_size': 0.10
        },
        MarketRegime.HIGH_VOLATILITY: {
            'stop_loss_pct': 0.08,
            'take_profit_pct': 0.15,
            'position_size': 0.05
        }
    }
}

# Конфигурация для криптовалютного рынка
CRYPTO_CONFIG = {
    'market_specific': {
        'sessions': {
            '24h': {'start': 0, 'end': 24, 'volatility': 0.40}
        },
        'symbols': ['BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD', 'LINKUSD'],
        'spread_impact': 0.001,  # 0.1%
        'commission': 0.001  # 0.1%
    },
    'regime_parameters': {
        MarketRegime.TRENDING: {
            'stop_loss_pct': 0.08,
            'take_profit_pct': 0.15,
            'position_size': 0.10
        },
        MarketRegime.RANGING: {
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.10,
            'position_size': 0.05
        },
        MarketRegime.HIGH_VOLATILITY: {
            'stop_loss_pct': 0.12,
            'take_profit_pct': 0.20,
            'position_size': 0.03
        }
    }
}

# =============================================================================
# КОНФИГУРАЦИИ ДЛЯ РАЗЛИЧНЫХ УРОВНЕЙ ОПЫТА
# =============================================================================

# Конфигурация для начинающих трейдеров
BEGINNER_CONFIG = {
    'risk_management': {
        'max_risk_per_trade': 0.01,  # 1% от депозита
        'max_positions': 1,
        'daily_loss_limit': 0.02,  # 2%
        'risk_level': RiskLevel.VERY_LOW
    },
    'strategy_params': {
        'fast_period': 20,
        'slow_period': 50,
        'stop_loss_pct': 0.02,  # 2%
        'take_profit_pct': 0.04,  # 4%
    },
    'alerts': {
        'drawdown_warning': 0.01,  # 1%
        'drawdown_critical': 0.03,  # 3%
        'daily_loss_warning': -50,  # $50
        'daily_loss_critical': -150  # $150
    },
    'features': {
        'auto_stop_trading_on_loss': True,
        'max_trades_per_day': 3,
        'mandatory_stop_loss': True,
        'position_sizing_help': True
    }
}

# Конфигурация для опытных трейдеров
EXPERIENCED_CONFIG = {
    'risk_management': {
        'max_risk_per_trade': 0.03,  # 3% от депозита
        'max_positions': 5,
        'daily_loss_limit': 0.08,  # 8%
        'risk_level': RiskLevel.MEDIUM
    },
    'strategy_params': {
        'fast_period': 10,
        'slow_period': 30,
        'stop_loss_pct': 0.025,  # 2.5%
        'take_profit_pct': 0.05,  # 5%
    },
    'alerts': {
        'drawdown_warning': 0.05,  # 5%
        'drawdown_critical': 0.12,  # 12%
        'daily_loss_warning': -300,  # $300
        'daily_loss_critical': -800  # $800
    },
    'features': {
        'auto_stop_trading_on_loss': False,
        'max_trades_per_day': 20,
        'mandatory_stop_loss': False,
        'position_sizing_help': False,
        'advanced_analytics': True
    }
}

# Конфигурация для профессиональных трейдеров
PROFESSIONAL_CONFIG = {
    'risk_management': {
        'max_risk_per_trade': 0.05,  # 5% от депозита
        'max_positions': 10,
        'daily_loss_limit': 0.15,  # 15%
        'risk_level': RiskLevel.HIGH
    },
    'strategy_params': {
        'fast_period': 5,
        'slow_period': 20,
        'stop_loss_pct': 0.03,  # 3%
        'take_profit_pct': 0.06,  # 6%
    },
    'alerts': {
        'drawdown_warning': 0.08,  # 8%
        'drawdown_critical': 0.20,  # 20%
        'daily_loss_warning': -1000,  # $1000
        'daily_loss_critical': -3000  # $3000
    },
    'features': {
        'auto_stop_trading_on_loss': False,
        'max_trades_per_day': 100,
        'mandatory_stop_loss': False,
        'position_sizing_help': False,
        'advanced_analytics': True,
        'custom_indicators': True,
        'multi_timeframe_analysis': True
    }
}

# =============================================================================
# КОНФИГУРАЦИИ ДЛЯ РАЗЛИЧНЫХ РЕЖИМОВ РАБОТЫ
# =============================================================================

# Конфигурация для демо-режима (тестирование)
DEMO_CONFIG = {
    'mode': 'demo',
    'initial_balance': 10000,
    'real_money': False,
    'logging_level': 'DEBUG',
    'save_trades': True,
    'performance_tracking': True,
    'risk_management': BEGINNER_CONFIG['risk_management'].copy(),
    'alerts': {
        'enabled': True,
        'email_notifications': False,
        'sound_alerts': True
    }
}

# Конфигурация для live-торговли
LIVE_CONFIG = {
    'mode': 'live',
    'initial_balance': 10000,
    'real_money': True,
    'logging_level': 'INFO',
    'save_trades': True,
    'performance_tracking': True,
    'risk_management': EXPERIENCED_CONFIG['risk_management'].copy(),
    'alerts': {
        'enabled': True,
        'email_notifications': True,
        'sound_alerts': True,
        'sms_notifications': True
    },
    'safety': {
        'max_daily_loss': 0.10,  # 10%
        'emergency_stop': True,
        'position_limits': True
    }
}

# Конфигурация для бэктестинга
BACKTEST_CONFIG = {
    'mode': 'backtest',
    'initial_balance': 10000,
    'real_money': False,
    'logging_level': 'WARNING',
    'save_trades': True,
    'performance_tracking': True,
    'risk_management': EXPERIENCED_CONFIG['risk_management'].copy(),
    'alerts': {
        'enabled': False,
        'email_notifications': False,
        'sound_alerts': False
    },
    'backtest': {
        'start_date': '2020-01-01',
        'end_date': '2023-12-31',
        'commission': 0.001,
        'slippage': 0.0001
    }
}

# =============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С КОНФИГУРАЦИЯМИ
# =============================================================================

def get_config_by_style(style: str) -> dict:
    """Возвращает конфигурацию по стилю торговли"""
    configs = {
        'scalping': SCALPING_CONFIG,
        'day_trading': DAY_TRADING_CONFIG,
        'swing_trading': SWING_TRADING_CONFIG,
        'position_trading': POSITION_TRADING_CONFIG
    }
    return configs.get(style, DAY_TRADING_CONFIG)

def get_config_by_market(market: str) -> dict:
    """Возвращает конфигурацию по рынку"""
    configs = {
        'forex': FOREX_CONFIG,
        'stocks': STOCK_CONFIG,
        'crypto': CRYPTO_CONFIG
    }
    return configs.get(market, FOREX_CONFIG)

def get_config_by_experience(experience: str) -> dict:
    """Возвращает конфигурацию по уровню опыта"""
    configs = {
        'beginner': BEGINNER_CONFIG,
        'experienced': EXPERIENCED_CONFIG,
        'professional': PROFESSIONAL_CONFIG
    }
    return configs.get(experience, BEGINNER_CONFIG)

def get_config_by_mode(mode: str) -> dict:
    """Возвращает конфигурацию по режиму работы"""
    configs = {
        'demo': DEMO_CONFIG,
        'live': LIVE_CONFIG,
        'backtest': BACKTEST_CONFIG
    }
    return configs.get(mode, DEMO_CONFIG)

def create_custom_config(base_config: dict, custom_params: dict) -> dict:
    """Создает пользовательскую конфигурацию на основе базовой"""
    import copy
    config = copy.deepcopy(base_config)
    
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = deep_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d
    
    return deep_update(config, custom_params)

def validate_config(config: dict) -> tuple[bool, list]:
    """Валидирует конфигурацию и возвращает результат и список ошибок"""
    errors = []
    
    # Проверяем обязательные поля
    required_fields = ['risk_management', 'strategy_params', 'alerts']
    for field in required_fields:
        if field not in config:
            errors.append(f"Отсутствует обязательное поле: {field}")
    
    # Проверяем risk_management
    if 'risk_management' in config:
        rm = config['risk_management']
        if 'max_risk_per_trade' in rm:
            if not 0 < rm['max_risk_per_trade'] <= 0.1:
                errors.append("max_risk_per_trade должен быть между 0 и 0.1")
        
        if 'max_positions' in rm:
            if not 1 <= rm['max_positions'] <= 20:
                errors.append("max_positions должен быть между 1 и 20")
    
    # Проверяем strategy_params
    if 'strategy_params' in config:
        sp = config['strategy_params']
        if 'fast_period' in sp and 'slow_period' in sp:
            if sp['fast_period'] >= sp['slow_period']:
                errors.append("fast_period должен быть меньше slow_period")
    
    return len(errors) == 0, errors

# =============================================================================
# ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# =============================================================================

if __name__ == "__main__":
    print("📋 ПРИМЕРЫ КОНФИГУРАЦИЙ")
    print("=" * 50)
    
    # Пример 1: Конфигурация для начинающего трейдера на Forex
    print("\n1. Конфигурация для начинающего трейдера на Forex:")
    forex_beginner = create_custom_config(
        get_config_by_market('forex'),
        get_config_by_experience('beginner')
    )
    print(f"   Максимальный риск на сделку: {forex_beginner['risk_management']['max_risk_per_trade']:.1%}")
    print(f"   Максимальное количество позиций: {forex_beginner['risk_management']['max_positions']}")
    
    # Пример 2: Конфигурация для опытного скальпера
    print("\n2. Конфигурация для опытного скальпера:")
    scalping_experienced = create_custom_config(
        get_config_by_style('scalping'),
        get_config_by_experience('experienced')
    )
    print(f"   Стоп-лосс: {scalping_experienced['strategy_params']['stop_loss_pct']:.1%}")
    print(f"   Тейк-профит: {scalping_experienced['strategy_params']['take_profit_pct']:.1%}")
    
    # Пример 3: Валидация конфигурации
    print("\n3. Валидация конфигурации:")
    is_valid, errors = validate_config(SCALPING_CONFIG)
    if is_valid:
        print("   ✅ Конфигурация валидна")
    else:
        print("   ❌ Ошибки в конфигурации:")
        for error in errors:
            print(f"      - {error}")
    
    print("\n💡 Используйте эти конфигурации как основу для настройки вашего торгового робота!")