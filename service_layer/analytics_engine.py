import pandas as pd
import numpy as np
from scipy.stats import linregress
from typing import List, Dict
from ta.volatility import AverageTrueRange, BollingerBands, KeltnerChannel
from ta.trend import SMAIndicator, EMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator

# Import our locked strategies interface
from .strategy_base import ITradingStrategy


class AnalyticsEngine:
    def __init__(self, strategies: List[ITradingStrategy]):
        # DEPENDENCY INVERSION: Engine doesn't hardcode strategies. It accepts them.
        self.strategies = strategies

    def get_normalized_lrs(self, series: pd.Series, window: int = 5):
        def calc_slope(y):
            x = np.arange(len(y))
            slope, _, _, _, _ = linregress(x, y)
            return (slope / y[-1]) * 100

        return series.rolling(window=window).apply(calc_slope)

    def _add_base_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # Trend (ema_10, #ema_20, ema_50)
        df['EMA_20'] = EMAIndicator(close=df["Close"], window=20).ema_indicator()
        df['EMA_50'] = EMAIndicator(close=df["Close"], window=50).ema_indicator()
        df['EMA_10'] = EMAIndicator(close=df["Close"], window=10).ema_indicator()
        # ATR

        df['ATR_14'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'],
                                        window=14).average_true_range()
        # ADX
        df['ADX'] = ADXIndicator(df['high'], df['low'], df['close'], 14).adx()
        # RSI
        df["RSI"] = RSIIndicator(df['close'], 14).rsi()
        # linear regression slope along with ema_slope ( angle with x axis) > 0.1 Uptrend  < -0.1 down trend
        df['LRS'] = self.get_normalized_lrs(df['close'], window=5)
        df.dropna(inplace=True)

        # # Pichle 5 din ka sabse zyada volume (Shifted)
        # df['vol_max_impulse'] = df['volume'].shift(1).rolling(window=5).max()
        # # Pichle 10 din ka average volume
        # df['vol_avg_10'] = df['volume'].rolling(window=10).mean()
        #
        # # Condition: Impulse me volume avg se 2x tha, aur aaj avg se kam hai
        # volume_filter = (df['vol_max_impulse'] > df['vol_avg_10'] * 2) & (df['volume'] < df['vol_avg_10'])

        # # Aaj ya kal me se kabhi bhi low 20 EMA ke paas aaya ho
        # df['near_ema'] = df['low'].rolling(window=3).min() <= (df['ema20'] * 1.01)
        #
        # # Lekin close abhi bhi 20 EMA ke upar hi hai (Trend intact)
        # df['stayed_above'] = df['close'].rolling(window=3).min() > df['ema20']

        '''
        df['rsi_max_5d'] = df['rsi'].shift(1).rolling(window=5).max()
df['rsi_min_5d'] = df['rsi'].shift(1).rolling(window=5).min()
        
        bullish_rsi_gate = (
    (df['rsi_max_5d'] > 70) &       # 1. Was recently explosive
    (df['rsi'].between(40, 55)) &  # 2. Reset to neutral zone (Support)
    (df['rsi'] > df['rsi'].shift(1)) # 3. Momentum just turned up
)

# BEARISH: Power Drop -> Neutral Reset -> Slight Downtick
bearish_rsi_gate = (
    (df['rsi_min_5d'] < 30) &       # 1. Was recently crashing
    (df['rsi'].between(45, 60)) &  # 2. Reset to neutral zone (Resistance)
    (df['rsi'] < df['rsi'].shift(1)) # 3. Momentum just turned down
)
        '''

        return df

    def _calculate_base_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Injects all technical math required by the setups."""

        # 1. Volume & Momentum
        df['VOL_SMA_20'] = SMAIndicator(close=df['Volume'], window=20).sma_indicator()
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()

        # 2. Trend (Moving Averages)
        df['SMA_20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()
        df['EMA_20'] = EMAIndicator(close=df['Close'], window=20).ema_indicator()
        df['EMA_50'] = EMAIndicator(close=df['Close'], window=50).ema_indicator()

        # 3. Volatility Bands (For TTM Squeeze)
        bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BBU'] = bb.bollinger_hband()
        df['BBL'] = bb.bollinger_lband()

        kc = KeltnerChannel(high=df['High'], low=df['Low'], close=df['Close'], window=20, window_atr=1.5)
        df['KCU'] = kc.keltner_channel_hband()
        df['KCL'] = kc.keltner_channel_lband()

        # 4. Volatility Expansion/Contraction (The Juice Checks)
        df['ATR_14'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'],
                                        window=14).average_true_range()
        df['ATR_50'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'],
                                        window=50).average_true_range()

        # CRITICAL TRADING FIX: Drop NaNs. 50-EMA needs 50 days to calculate.
        # First 49 rows are NaN. We MUST drop them before passing to setup logic.
        df.dropna(inplace=True)
        return df

    def process_stock(self, raw_data_list: List[dict]) -> pd.DataFrame:
        """Converts raw list[dict] to DataFrame, runs math, and evaluates setups."""
        if not raw_data_list:
            return pd.DataFrame()

        df = pd.DataFrame(raw_data_list)
        # Ensure proper datetime sorting for pandas shift() math
        time_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df[time_col] = pd.to_datetime(df[time_col])
        df.sort_values(by=time_col, inplace=True)
        df.set_index(time_col, inplace=True)

        # Apply Math
        df = self._calculate_base_indicators(df)

        # Execute all injected setups dynamically
        for strategy in self.strategies:
            signal_col_name = f"SIGNAL_{strategy.name}"
            df[signal_col_name] = strategy.generate_signal(df)

        return df.reset_index()
