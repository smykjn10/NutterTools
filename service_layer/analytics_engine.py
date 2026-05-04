import pandas as pd
from typing import List, Dict
from ta.volatility import AverageTrueRange, BollingerBands, KeltnerChannel
from ta.trend import SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator

# Import our locked strategies interface
from .strategy_base import ITradingStrategy


class AnalyticsEngine:
    def __init__(self, strategies: List[ITradingStrategy]):
        # DEPENDENCY INVERSION: Engine doesn't hardcode strategies. It accepts them.
        self.strategies = strategies

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