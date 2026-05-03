import pandas as pd
from core.config import settings
import numpy as np

from strategy_base import ITradingStrategy


class TTMSqueezeSetup(ITradingStrategy):
    @property
    def name(self) -> str:
        return "TTM_SQUEEZE"

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        # TODO :- this is only a signal generator setup, need to check on execution timeframe that stock had broken the squeeze
        # 1. The Core Squeeze (Volatility Compression)
        is_squeeze = (df['BBU'] < df['KCU']) & (df['BBL'] > df['KCL'])

        # 2. Macro Trend Filter (EMA 50 Slope)
        # Using shift(3) to see if the slope is genuinely rising/falling over the last few days
        ema_50_rising = df['EMA_50'] > df['EMA_50'].shift(3)
        ema_50_falling = df['EMA_50'] < df['EMA_50'].shift(3)

        # 3. Momentum: Distance from Mean (The "Coiled" Check)
        # Price MUST be tightly hugging the 20 SMA. If it's more than 2% away, it's not a tight coil.
        distance_from_sma = (df['Close'] - df['SMA_20']).abs() / df['SMA_20']
        tightly_coiled = distance_from_sma < 0.02  # Maximum 2% distance allowed

        # 4. Asymmetric RSI (Avoiding the 45-55 Chop Zone)
        strong_bull_rsi = df['RSI'] > 55
        strong_bear_rsi = df['RSI'] < 45

        # The Compression Juice (For Spring/Coil Setups)
        baseline_volatility = (df['ATR_14'] / df['Close']) >= 0.01

        # The spring is tightly wound (Short term volatility has died down compared to historical)
        contracting_volatility = df['ATR_14'] < df['ATR_50']

        is_volatile = baseline_volatility & contracting_volatility

        # 5. Final Institutional Alignments
        # Bullish: 20 SMA > 50 EMA + 50 EMA is rising + High RSI + Tightly Coiled around 20 SMA
        bullish_bias = (df['SMA_20'] > df['EMA_50']) & ema_50_rising & strong_bull_rsi & tightly_coiled

        # Bearish: 20 SMA < 50 EMA + 50 EMA is falling + Low RSI + Tightly Coiled around 20 SMA
        bearish_bias = (df['SMA_20'] < df['EMA_50']) & ema_50_falling & strong_bear_rsi & tightly_coiled

        conditions = [is_squeeze & bullish_bias & is_volatile, is_squeeze & bearish_bias & is_volatile]
        choices = ['BULLISH', 'BEARISH']

        return pd.Series(np.select(conditions, choices, default=''), index=df.index)


class InstitutionalBreakoutSetup(ITradingStrategy):
    @property
    def name(self) -> str:
        return "INSTITUTIONAL_BREAKOUT"

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        # Using shift(1) so today's candle doesn't skew the historical resistance
        # 1. The Critical Levels (3 Months / 60-Day High and Low)
        # 60 trading days is roughly 3 months. This ensures we are catching major base breakouts!
        res_60 = df['High'].shift(1).rolling(window=settings.LOOK_BACK_PD).max()
        sup_60 = df['Low'].shift(1).rolling(window=settings.LOOK_BACK_PD).min()

        # 2. Volume Dynamics (The Footprints of Smart Money)
        # Today's volume must be an explosion (> 1.5x of 20-day average)
        high_vol_today = df['Volume'] > (settings.HIGH_VOL_THRESHOLD * df['VOL_SMA_20'])

        # Pre-Breakout Dry-up (VCP): Average volume of the 3 days prior must be LESS than the 20-day average
        vol_sma_3 = df['Volume'].rolling(window=3).mean()
        pre_breakout_dryup = vol_sma_3.shift(1) < df['VOL_SMA_20'].shift(1)

        # 3. Macro Trend Validation
        ema_50_rising = df['EMA_50'] > df['EMA_50'].shift(3)
        ema_50_falling = df['EMA_50'] < df['EMA_50'].shift(3)

        # 4. The "Freshness" Filter (Crucial for Options)
        # Price crossed resistance, BUT is not extended more than 3% above it (Avoid chasing)
        fresh_breakout_up = (df['Close'] > res_60) & (df['Close'] < (res_60 * 1.03))  # TODO

        # Price crossed support, BUT is not extended more than 3% below it
        fresh_breakdown_down = (df['Close'] < sup_60) & (df['Close'] > (sup_60 * 0.97))

        # # 🔥 5. THE NEW VOLATILITY FILTER (The "Juice" Check)
        # # The stock's average daily move must be strictly greater than 2% of its price
        # high_volatility = df['ATR'] > (df['Close'] * 0.02)

        # Condition A: Absolute Baseline.
        # Must be capable of moving at least 1% a day (Captures Nifty 50 Large Caps)
        baseline_volatility = (df['ATR_14'] / df['Close']) >= 0.01

        # Condition B: Volatility Expansion.
        # The short-term ATR (14 days) should be higher than the long-term ATR (50 days).
        # This proves the stock is currently "waking up" and momentum is building.
        expanding_volatility = df['ATR_14'] > df['ATR_50']

        # Final Volatility Check
        is_volatile = baseline_volatility & expanding_volatility

        # 6. Final Institutional Alignments

        # BULLISH: Fresh Breakout + Volume Surge + Prior Volume Dryup + Uptrending MA Stack + Strong RSI
        bullish_alignment = (
                fresh_breakout_up &
                high_vol_today &
                pre_breakout_dryup &
                (df['SMA_20'] > df['EMA_50']) &
                ema_50_rising &
                (df['RSI'] > settings.BULLISH_RSI) & # > 60 means the stock is explicitly in a "Mark-Up" phase
                 is_volatile
        )

        # BEARISH: Support Smash + Volume Surge + Downtrending MA Stack + Weak RSI
        # Note: We do NOT require 'pre_breakout_dryup' here because panic selling doesn't need prior accumulation
        bearish_alignment = (
                fresh_breakdown_down &
                high_vol_today &
                (df['SMA_20'] < df['EMA_50']) &
                ema_50_falling &
                (df['RSI'] < settings.BEARISH_RSI) &  # < 40 means explicit "Mark-Down" phase
                 is_volatile
        )

        conditions = [bullish_alignment, bearish_alignment]
        choices = ['BULLISH', 'BEARISH']

        return pd.Series(np.select(conditions, choices, default=''), index=df.index)


class PullbackBounceSetup(ITradingStrategy):
    @property
    def name(self) -> str:
        '''
            "mean reversion" principle—the idea that even in a strong trend, prices eventually return to their average before continuing the move
        '''
        return "20_EMA_PULLBACK"

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        # 1. Macro Trend Validation
        ema_50_rising = df['EMA_50'] > df['EMA_50'].shift(3)
        ema_50_falling = df['EMA_50'] < df['EMA_50'].shift(3)

        ema_20_above_50 = df['EMA_20'] > df['EMA_50']
        ema_20_below_50 = df['EMA_20'] < df['EMA_50']

        # 2. Volume Logic: The "No Supply" Check
        pre_bounce_dryup = df['Volume'].shift(1) < df['VOL_SMA_20'].shift(1)

        # 3. Candlestick Math (Wick vs Body Size)
        body_size = (df['Close'] - df['Open']).abs()
        lower_wick = df[['Close', 'Open']].min(axis=1) - df['Low']
        upper_wick = df['High'] - df[['Close', 'Open']].max(axis=1)

        # 4. The Rejection Action
        dipped_to_ema_bull = df['Low'] <= df['EMA_20']
        closed_above_ema = df['Close'] > df['EMA_20']
        strong_bull_rejection = lower_wick > (1.5 * body_size)

        dipped_to_ema_bear = df['High'] >= df['EMA_20']
        closed_below_ema = df['Close'] < df['EMA_20']
        strong_bear_rejection = upper_wick > (1.5 * body_size)

        # 5. Momentum Safety Net
        rsi_bullish = df['RSI'] > 50
        rsi_bearish = df['RSI'] < 50

        # # 🔥 6. THE NEW VOLATILITY FILTER (The "Juice" Check)
        # # The stock's average daily move must be strictly greater than 2% of its price
        # high_volatility = df['ATR'] > (df['Close'] * 0.02)

        # Condition A: Absolute Baseline.
        # Must be capable of moving at least 1% a day (Captures Nifty 50 Large Caps)
        baseline_volatility = (df['ATR_14'] / df['Close']) >= 0.01

        # Condition B: Volatility Expansion.
        # The short-term ATR (14 days) should be higher than the long-term ATR (50 days).
        # This proves the stock is currently "waking up" and momentum is building.
        expanding_volatility = df['ATR_14'] > df['ATR_50']

        # Final Volatility Check
        is_volatile = baseline_volatility & expanding_volatility


        # 7. Final Combined Signals
        bull_signal = (
                ema_20_above_50 &
                ema_50_rising &
                pre_bounce_dryup &
                dipped_to_ema_bull &
                closed_above_ema &
                strong_bull_rejection &
                rsi_bullish &
                is_volatile  # Reject slow-moving garbage
        )

        bear_signal = (
                ema_20_below_50 &
                ema_50_falling &
                pre_bounce_dryup &
                dipped_to_ema_bear &
                closed_below_ema &
                strong_bear_rejection &
                rsi_bearish &
                is_volatile  # Reject slow-moving garbage
        )

        conditions = [bull_signal, bear_signal]
        choices = ['BULLISH', 'BEARISH']

        return pd.Series(np.select(conditions, choices, default=""), index=df.index)


class CoilNR4Setup(ITradingStrategy):
    @property
    def name(self) -> str:
        '''
        Most accurate setup
        '''
        return "COIL_NR4"

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        # 1. Daily Range Calculation
        df['Daily_Range'] = df['High'] - df['Low']

        # 2. Inside Bar Logic (Fixed the Tick Trap using <= and >=)
        inside_bar = (df['High'] <= df['High'].shift(1)) & (df['Low'] >= df['Low'].shift(1))

        # 3. NR4 Logic (Today's range is the narrowest in the last 4 days)
        is_nr4 = df['Daily_Range'] == df['Daily_Range'].rolling(window=4).min()

        # 4. Volume Contraction (Smart money is quiet, waiting for the explosion)
        volume_dryup = df['Volume'] < df['VOL_SMA_20']

        # 5. The Base Coil (Unbiased Volatility Contraction)
        # The Compression Juice (For Spring/Coil Setups)
        baseline_volatility = (df['ATR_14'] / df['Close']) >= 0.01

        # The spring is tightly wound (Short term volatility has died down compared to historical)
        contracting_volatility = df['ATR_14'] < df['ATR_50']

        is_volatile = baseline_volatility & contracting_volatility

        base_coil = is_volatile & inside_bar & is_nr4 & volume_dryup

        # 6. Directional Bias (Institutional Alignment)
        # A coil is a spring. It has a higher probability of breaking out in the direction of the macro trend.
        ema_20_above_50 = df['EMA_20'] > df['EMA_50']
        ema_20_below_50 = df['EMA_20'] < df['EMA_50']



        bullish_coil = base_coil & ema_20_above_50 & (df['RSI'] > 50 )
        bearish_coil = base_coil & ema_20_below_50 & (df['RSI'] < 50 )

        conditions = [bullish_coil, bearish_coil]
        choices = ['BULLISH', 'BEARISH']

        # Using "" for clean JSON serialization later
        return pd.Series(np.select(conditions, choices, default=""), index=df.index)


