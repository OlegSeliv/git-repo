"""
Модуль для определения текущего рыночного режима.
Использует машинное обучение и статистические методы для классификации рынка.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


@dataclass
class MarketRegime:
    """Описание рыночного режима"""
    regime_type: str  # 'trending_up', 'trending_down', 'ranging', 'volatile', 'quiet'
    confidence: float
    sub_regime: Optional[str] = None  # Подтип режима
    transition_probability: float = 0.0  # Вероятность смены режима
    duration: int = 0  # Продолжительность текущего режима в барах
    strength: float = 0.0  # Сила режима
    characteristics: Dict = None


class MarketRegimeDetector:
    """
    Детектор рыночных режимов с использованием множественных методов:
    1. Hidden Markov Models (HMM)
    2. Gaussian Mixture Models (GMM)
    3. Statistical regime detection
    4. Technical indicators ensemble
    """
    
    def __init__(self, 
                 lookback_period: int = 100,
                 regime_threshold: float = 0.7,
                 min_regime_duration: int = 10):
        """
        Args:
            lookback_period: Период для анализа
            regime_threshold: Порог уверенности для определения режима
            min_regime_duration: Минимальная продолжительность режима
        """
        self.lookback_period = lookback_period
        self.regime_threshold = regime_threshold
        self.min_regime_duration = min_regime_duration
        
        # Модели для определения режимов
        self.gmm_model = None
        self.scaler = StandardScaler()
        
        # История режимов
        self.regime_history = []
        self.current_regime = None
        self.regime_start_index = 0
        
        # Параметры режимов
        self.regime_parameters = {
            'trending_up': {
                'min_trend_strength': 0.6,
                'min_directional_movement': 0.7,
                'max_volatility_ratio': 1.5
            },
            'trending_down': {
                'min_trend_strength': 0.6,
                'min_directional_movement': 0.7,
                'max_volatility_ratio': 1.5
            },
            'ranging': {
                'max_trend_strength': 0.3,
                'min_mean_reversion': 0.6,
                'max_breakout_probability': 0.3
            },
            'volatile': {
                'min_volatility_ratio': 2.0,
                'min_volatility_clustering': 0.6,
                'min_tail_events': 0.1
            },
            'quiet': {
                'max_volatility_ratio': 0.5,
                'max_volume_ratio': 0.7,
                'min_range_bound': 0.7
            }
        }
        
    def detect_regime(self, price_data: pd.DataFrame) -> MarketRegime:
        """
        Определение текущего рыночного режима.
        
        Args:
            price_data: DataFrame с ценовыми данными (OHLCV)
            
        Returns:
            MarketRegime: Текущий рыночный режим
        """
        # Расчет признаков
        features = self._calculate_features(price_data)
        
        # Множественные методы детекции
        statistical_regime = self._statistical_detection(features)
        ml_regime = self._ml_detection(features)
        indicator_regime = self._indicator_based_detection(price_data)
        
        # Ансамблевое решение
        final_regime = self._ensemble_decision(
            statistical_regime, ml_regime, indicator_regime
        )
        
        # Обновление истории
        self._update_regime_history(final_regime)
        
        return final_regime
    
    def _calculate_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Расчет признаков для определения режима.
        """
        features = pd.DataFrame()
        
        # Возвраты
        features['returns'] = price_data['close'].pct_change()
        features['log_returns'] = np.log(price_data['close'] / price_data['close'].shift(1))
        
        # Волатильность
        features['volatility'] = features['returns'].rolling(20).std()
        features['volatility_ratio'] = (
            features['volatility'] / features['volatility'].rolling(60).mean()
        )
        
        # Тренд
        features['sma_20'] = price_data['close'].rolling(20).mean()
        features['sma_50'] = price_data['close'].rolling(50).mean()
        features['trend_strength'] = (
            (features['sma_20'] - features['sma_50']) / price_data['close']
        )
        
        # Momentum
        features['rsi'] = self._calculate_rsi(price_data['close'])
        features['momentum'] = price_data['close'].pct_change(10)
        
        # Volume features (если доступны)
        if 'volume' in price_data.columns:
            features['volume_ratio'] = (
                price_data['volume'] / price_data['volume'].rolling(20).mean()
            )
            features['volume_momentum'] = price_data['volume'].pct_change(5)
        
        # Microstructure
        if all(col in price_data.columns for col in ['high', 'low']):
            features['high_low_range'] = (
                (price_data['high'] - price_data['low']) / price_data['close']
            )
            features['close_location'] = (
                (price_data['close'] - price_data['low']) / 
                (price_data['high'] - price_data['low'] + 1e-10)
            )
        
        # Statistical moments
        features['skewness'] = features['returns'].rolling(30).skew()
        features['kurtosis'] = features['returns'].rolling(30).kurt()
        
        return features.dropna()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Расчет RSI.
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _statistical_detection(self, features: pd.DataFrame) -> Dict:
        """
        Статистическое определение режима.
        """
        if len(features) < self.lookback_period:
            return {'regime': 'unknown', 'confidence': 0.0}
            
        recent_data = features.iloc[-self.lookback_period:]
        
        # Анализ трендовости
        trend_test = self._test_trend(recent_data)
        
        # Анализ волатильности
        volatility_regime = self._analyze_volatility_regime(recent_data)
        
        # Анализ mean-reversion
        mean_reversion = self._test_mean_reversion(recent_data)
        
        # Определение режима
        if trend_test['is_trending'] and trend_test['direction'] > 0:
            regime = 'trending_up'
            confidence = trend_test['strength']
        elif trend_test['is_trending'] and trend_test['direction'] < 0:
            regime = 'trending_down'
            confidence = trend_test['strength']
        elif mean_reversion['is_mean_reverting']:
            regime = 'ranging'
            confidence = mean_reversion['strength']
        elif volatility_regime['is_volatile']:
            regime = 'volatile'
            confidence = volatility_regime['confidence']
        else:
            regime = 'quiet'
            confidence = 0.6
            
        return {'regime': regime, 'confidence': confidence}
    
    def _test_trend(self, data: pd.DataFrame) -> Dict:
        """
        Тестирование наличия тренда.
        """
        if 'returns' not in data.columns:
            return {'is_trending': False, 'direction': 0, 'strength': 0}
            
        returns = data['returns'].dropna()
        
        # Тест на автокорреляцию
        autocorr = returns.autocorr(lag=1)
        
        # Линейная регрессия
        x = np.arange(len(returns))
        y = returns.cumsum().values
        
        if len(x) > 1:
            z = np.polyfit(x, y, 1)
            slope = z[0]
            
            # R-squared
            p = np.poly1d(z)
            yhat = p(x)
            ybar = np.sum(y) / len(y)
            ssreg = np.sum((yhat - ybar) ** 2)
            sstot = np.sum((y - ybar) ** 2) + 1e-10
            r_squared = ssreg / sstot
        else:
            slope = 0
            r_squared = 0
            
        # Определение тренда
        is_trending = (abs(r_squared) > 0.5 and abs(autocorr) > 0.1)
        direction = np.sign(slope)
        strength = min(1.0, abs(r_squared) * (1 + abs(autocorr)))
        
        return {
            'is_trending': is_trending,
            'direction': direction,
            'strength': strength
        }
    
    def _analyze_volatility_regime(self, data: pd.DataFrame) -> Dict:
        """
        Анализ волатильного режима.
        """
        if 'volatility_ratio' not in data.columns:
            return {'is_volatile': False, 'confidence': 0}
            
        vol_ratio = data['volatility_ratio'].iloc[-1]
        vol_clustering = self._measure_volatility_clustering(data)
        
        # Проверка на экстремальные события
        if 'returns' in data.columns:
            returns = data['returns'].dropna()
            extreme_events = (abs(returns) > returns.std() * 2).mean()
        else:
            extreme_events = 0
            
        is_volatile = (
            vol_ratio > 1.5 or 
            vol_clustering > 0.6 or 
            extreme_events > 0.1
        )
        
        confidence = min(1.0, (vol_ratio / 2 + vol_clustering + extreme_events) / 3)
        
        return {'is_volatile': is_volatile, 'confidence': confidence}
    
    def _measure_volatility_clustering(self, data: pd.DataFrame) -> float:
        """
        Измерение кластеризации волатильности (GARCH-эффект).
        """
        if 'returns' not in data.columns:
            return 0.0
            
        returns = data['returns'].dropna()
        squared_returns = returns ** 2
        
        # Автокорреляция квадратов возвратов
        autocorr_sq = squared_returns.autocorr(lag=1)
        
        return abs(autocorr_sq)
    
    def _test_mean_reversion(self, data: pd.DataFrame) -> Dict:
        """
        Тест на mean-reversion (возврат к среднему).
        """
        if 'close_location' not in data.columns:
            # Используем альтернативный метод
            if 'returns' in data.columns:
                returns = data['returns'].dropna()
                # Hurst exponent approximation
                hurst = self._estimate_hurst_exponent(returns)
                is_mean_reverting = hurst < 0.5
                strength = max(0, (0.5 - hurst) * 2)
            else:
                is_mean_reverting = False
                strength = 0
        else:
            close_loc = data['close_location'].dropna()
            
            # Частота возврата к середине диапазона
            mean_crosses = ((close_loc > 0.4) & (close_loc < 0.6)).mean()
            
            # Стандартное отклонение от середины
            deviation = close_loc.std()
            
            is_mean_reverting = mean_crosses > 0.3 and deviation < 0.3
            strength = min(1.0, mean_crosses * 2 * (1 - deviation))
            
        return {'is_mean_reverting': is_mean_reverting, 'strength': strength}
    
    def _estimate_hurst_exponent(self, returns: pd.Series) -> float:
        """
        Упрощенная оценка экспоненты Херста.
        """
        if len(returns) < 20:
            return 0.5
            
        lags = range(2, min(20, len(returns) // 2))
        tau = []
        
        for lag in lags:
            # Разбиваем на подпериоды
            chunks = [returns[i:i+lag] for i in range(0, len(returns), lag)]
            chunks = [c for c in chunks if len(c) == lag]
            
            if not chunks:
                continue
                
            # R/S статистика
            rs_values = []
            for chunk in chunks:
                if len(chunk) > 0 and chunk.std() > 0:
                    mean_centered = chunk - chunk.mean()
                    cumsum = mean_centered.cumsum()
                    R = cumsum.max() - cumsum.min()
                    S = chunk.std()
                    rs_values.append(R / S if S > 0 else 0)
                    
            if rs_values:
                tau.append(np.mean(rs_values))
                
        if len(tau) < 2:
            return 0.5
            
        # Линейная регрессия в лог-лог пространстве
        log_lags = np.log(list(lags)[:len(tau)])
        log_tau = np.log(tau)
        
        if len(log_lags) > 1:
            hurst = np.polyfit(log_lags, log_tau, 1)[0]
            return np.clip(hurst, 0, 1)
        else:
            return 0.5
    
    def _ml_detection(self, features: pd.DataFrame) -> Dict:
        """
        Определение режима с использованием машинного обучения (GMM).
        """
        if len(features) < 50:
            return {'regime': 'unknown', 'confidence': 0.0}
            
        # Подготовка признаков
        feature_cols = ['returns', 'volatility_ratio', 'trend_strength', 'momentum']
        feature_cols = [col for col in feature_cols if col in features.columns]
        
        if not feature_cols:
            return {'regime': 'unknown', 'confidence': 0.0}
            
        X = features[feature_cols].dropna()
        
        if len(X) < 20:
            return {'regime': 'unknown', 'confidence': 0.0}
            
        # Обучение или использование GMM
        if self.gmm_model is None:
            self.gmm_model = GaussianMixture(
                n_components=4,  # 4 основных режима
                covariance_type='full',
                random_state=42
            )
            X_scaled = self.scaler.fit_transform(X)
            self.gmm_model.fit(X_scaled)
        else:
            X_scaled = self.scaler.transform(X)
            
        # Предсказание текущего режима
        current_features = X_scaled[-1:] 
        regime_probs = self.gmm_model.predict_proba(current_features)[0]
        regime_label = np.argmax(regime_probs)
        confidence = regime_probs[regime_label]
        
        # Интерпретация кластеров
        regime_map = {
            0: 'trending_up',
            1: 'trending_down',
            2: 'ranging',
            3: 'volatile'
        }
        
        regime = regime_map.get(regime_label, 'unknown')
        
        return {'regime': regime, 'confidence': confidence}
    
    def _indicator_based_detection(self, price_data: pd.DataFrame) -> Dict:
        """
        Определение режима на основе технических индикаторов.
        """
        if len(price_data) < 50:
            return {'regime': 'unknown', 'confidence': 0.0}
            
        # ADX для определения силы тренда
        adx = self._calculate_adx(price_data)
        
        # Bollinger Bands для волатильности
        bb_width = self._calculate_bb_width(price_data)
        
        # ATR для волатильности
        atr = self._calculate_atr(price_data)
        
        # Определение режима
        if adx > 25 and price_data['close'].iloc[-1] > price_data['close'].iloc[-20]:
            regime = 'trending_up'
            confidence = min(1.0, adx / 50)
        elif adx > 25 and price_data['close'].iloc[-1] < price_data['close'].iloc[-20]:
            regime = 'trending_down'
            confidence = min(1.0, adx / 50)
        elif adx < 20 and bb_width < 0.1:
            regime = 'ranging'
            confidence = 0.6
        elif bb_width > 0.2 or (atr / price_data['close'].iloc[-1]) > 0.02:
            regime = 'volatile'
            confidence = min(1.0, bb_width * 2)
        else:
            regime = 'quiet'
            confidence = 0.5
            
        return {'regime': regime, 'confidence': confidence}
    
    def _calculate_adx(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """
        Расчет ADX (Average Directional Index).
        """
        if not all(col in price_data.columns for col in ['high', 'low', 'close']):
            return 0.0
            
        high = price_data['high']
        low = price_data['low']
        close = price_data['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(period).mean().iloc[-1]
        
        return adx if not np.isnan(adx) else 0.0
    
    def _calculate_bb_width(self, price_data: pd.DataFrame, period: int = 20) -> float:
        """
        Расчет ширины Bollinger Bands.
        """
        close = price_data['close']
        sma = close.rolling(period).mean()
        std = close.rolling(period).std()
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        
        bb_width = ((upper_band - lower_band) / sma).iloc[-1]
        
        return bb_width if not np.isnan(bb_width) else 0.0
    
    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """
        Расчет ATR (Average True Range).
        """
        if not all(col in price_data.columns for col in ['high', 'low', 'close']):
            return 0.0
            
        high = price_data['high']
        low = price_data['low']
        close = price_data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr if not np.isnan(atr) else 0.0
    
    def _ensemble_decision(self, 
                          statistical: Dict,
                          ml: Dict, 
                          indicator: Dict) -> MarketRegime:
        """
        Ансамблевое решение на основе множественных методов.
        """
        # Веса для каждого метода
        weights = {
            'statistical': 0.35,
            'ml': 0.35,
            'indicator': 0.30
        }
        
        # Собираем голоса
        votes = {}
        
        for method, result, weight in [
            ('statistical', statistical, weights['statistical']),
            ('ml', ml, weights['ml']),
            ('indicator', indicator, weights['indicator'])
        ]:
            regime = result.get('regime', 'unknown')
            confidence = result.get('confidence', 0)
            
            if regime != 'unknown':
                if regime not in votes:
                    votes[regime] = 0
                votes[regime] += confidence * weight
                
        # Выбираем режим с максимальным весом
        if not votes:
            final_regime = 'unknown'
            confidence = 0.0
        else:
            final_regime = max(votes, key=votes.get)
            confidence = votes[final_regime]
            
        # Определение подрежима и дополнительных характеристик
        sub_regime = self._determine_sub_regime(final_regime, statistical, ml, indicator)
        
        # Расчет вероятности перехода
        transition_prob = self._calculate_transition_probability(final_regime)
        
        # Определение силы режима
        strength = self._calculate_regime_strength(final_regime, confidence)
        
        # Характеристики режима
        characteristics = self._get_regime_characteristics(final_regime)
        
        return MarketRegime(
            regime_type=final_regime,
            confidence=confidence,
            sub_regime=sub_regime,
            transition_probability=transition_prob,
            duration=self._get_regime_duration(),
            strength=strength,
            characteristics=characteristics
        )
    
    def _determine_sub_regime(self, 
                             main_regime: str,
                             statistical: Dict,
                             ml: Dict,
                             indicator: Dict) -> Optional[str]:
        """
        Определение подтипа режима.
        """
        if main_regime == 'trending_up':
            # Проверка силы тренда
            if all(r.get('confidence', 0) > 0.8 for r in [statistical, ml, indicator]):
                return 'strong_trend'
            else:
                return 'weak_trend'
                
        elif main_regime == 'trending_down':
            if all(r.get('confidence', 0) > 0.8 for r in [statistical, ml, indicator]):
                return 'strong_trend'
            else:
                return 'weak_trend'
                
        elif main_regime == 'ranging':
            # Проверка ширины диапазона
            return 'tight_range'  # или 'wide_range'
            
        elif main_regime == 'volatile':
            return 'extreme_volatility'  # или 'moderate_volatility'
            
        return None
    
    def _calculate_transition_probability(self, current_regime: str) -> float:
        """
        Расчет вероятности смены режима.
        """
        if not self.regime_history:
            return 0.5
            
        # Анализ последних переходов
        recent_history = self.regime_history[-20:]
        
        # Подсчет переходов
        transitions = 0
        for i in range(1, len(recent_history)):
            if recent_history[i].regime_type != recent_history[i-1].regime_type:
                transitions += 1
                
        transition_rate = transitions / len(recent_history) if recent_history else 0
        
        # Корректировка на продолжительность текущего режима
        duration = self._get_regime_duration()
        if duration > self.min_regime_duration * 2:
            # Увеличиваем вероятность перехода для долгих режимов
            transition_rate *= 1.5
            
        return min(1.0, transition_rate)
    
    def _get_regime_duration(self) -> int:
        """
        Получение продолжительности текущего режима.
        """
        if not self.regime_history:
            return 0
            
        current = self.regime_history[-1].regime_type if self.regime_history else None
        duration = 0
        
        for regime in reversed(self.regime_history):
            if regime.regime_type == current:
                duration += 1
            else:
                break
                
        return duration
    
    def _calculate_regime_strength(self, regime: str, confidence: float) -> float:
        """
        Расчет силы режима.
        """
        base_strength = confidence
        
        # Корректировка на продолжительность
        duration = self._get_regime_duration()
        if duration > self.min_regime_duration:
            base_strength *= 1.1
            
        # Корректировка на стабильность
        if len(self.regime_history) > 10:
            recent = self.regime_history[-10:]
            stability = sum(1 for r in recent if r.regime_type == regime) / 10
            base_strength *= (0.5 + stability * 0.5)
            
        return min(1.0, base_strength)
    
    def _get_regime_characteristics(self, regime: str) -> Dict:
        """
        Получение характеристик режима.
        """
        characteristics = {
            'trending_up': {
                'recommended_strategies': ['trend_following', 'momentum'],
                'avoid_strategies': ['mean_reversion', 'range_trading'],
                'risk_level': 'medium',
                'typical_duration': '5-20 bars',
                'key_indicators': ['ADX > 25', 'RSI > 50', 'Price > SMA']
            },
            'trending_down': {
                'recommended_strategies': ['trend_following_short', 'momentum_short'],
                'avoid_strategies': ['buy_and_hold', 'range_trading'],
                'risk_level': 'medium-high',
                'typical_duration': '5-20 bars',
                'key_indicators': ['ADX > 25', 'RSI < 50', 'Price < SMA']
            },
            'ranging': {
                'recommended_strategies': ['range_trading', 'mean_reversion'],
                'avoid_strategies': ['trend_following', 'breakout'],
                'risk_level': 'low',
                'typical_duration': '20-50 bars',
                'key_indicators': ['ADX < 20', 'RSI 30-70', 'BB contraction']
            },
            'volatile': {
                'recommended_strategies': ['volatility_trading', 'options'],
                'avoid_strategies': ['tight_stops', 'martingale'],
                'risk_level': 'high',
                'typical_duration': '3-10 bars',
                'key_indicators': ['ATR spike', 'BB expansion', 'Volume spike']
            },
            'quiet': {
                'recommended_strategies': ['wait', 'accumulation'],
                'avoid_strategies': ['scalping', 'high_frequency'],
                'risk_level': 'very_low',
                'typical_duration': '10-30 bars',
                'key_indicators': ['Low ATR', 'Low volume', 'Tight range']
            }
        }
        
        return characteristics.get(regime, {})
    
    def _update_regime_history(self, regime: MarketRegime):
        """
        Обновление истории режимов.
        """
        self.regime_history.append(regime)
        
        # Ограничиваем размер истории
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-500:]
            
        self.current_regime = regime
    
    def get_regime_statistics(self) -> Dict:
        """
        Получение статистики по режимам.
        """
        if not self.regime_history:
            return {}
            
        stats = {
            'total_observations': len(self.regime_history),
            'regime_distribution': {},
            'average_duration': {},
            'transition_matrix': {}
        }
        
        # Распределение режимов
        for regime in self.regime_history:
            regime_type = regime.regime_type
            if regime_type not in stats['regime_distribution']:
                stats['regime_distribution'][regime_type] = 0
            stats['regime_distribution'][regime_type] += 1
            
        # Нормализация
        total = len(self.regime_history)
        for regime in stats['regime_distribution']:
            stats['regime_distribution'][regime] /= total
            
        # Средняя продолжительность каждого режима
        current_regime = None
        current_duration = 0
        durations = {}
        
        for regime in self.regime_history:
            if regime.regime_type == current_regime:
                current_duration += 1
            else:
                if current_regime is not None:
                    if current_regime not in durations:
                        durations[current_regime] = []
                    durations[current_regime].append(current_duration)
                current_regime = regime.regime_type
                current_duration = 1
                
        for regime, dur_list in durations.items():
            stats['average_duration'][regime] = np.mean(dur_list)
            
        return stats