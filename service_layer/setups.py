import pandas as pd
from core.config import settings
import numpy as np

from .strategy_base import ITradingStrategy


class TTMSqueezeSetup(ITradingStrategy):
    @property
    def name(self) -> str:
        return "TTM_SQUEEZE_FIRE"  # Renamed to signify ACTION, not just consolidation

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        # 1. The Core Squeeze State
        squeeze_on = (df['BBU'] < df['KCU']) & (df['BBL'] > df['KCL'])

        # 🔥 THE FIX: The "Fire" Event (The Explosion)
        # Squeeze was ON yesterday (or recently), but is explicitly OFF today.
        # This proves the consolidation has just broken today!
        squeeze_fired_today = squeeze_on.shift(1).fillna(False) & ~squeeze_on

        # 2. Macro Trend Filter (EMA 50 Slope)
        ema_50_rising = df['EMA_50'] > df['EMA_50'].shift(3)
        ema_50_falling = df['EMA_50'] < df['EMA_50'].shift(3)

        # 3. Momentum: The "Coiled" Check (Checked for Yesterday)
        # We check if it was tightly coiled YESTERDAY before today's explosion
        distance_from_sma_yesterday = (df['Close'].shift(1) - df['SMA_20'].shift(1)).abs() / df['SMA_20'].shift(1)
        was_tightly_coiled = distance_from_sma_yesterday < 0.02

        # 4. Asymmetric RSI (Confirming the direction of the Fire)
        strong_bull_rsi = df['RSI'] > 55
        strong_bear_rsi = df['RSI'] < 45

        # 5. The Compression Juice (Ensuring the stock isn't fundamentally dead)
        baseline_volatility = (df['ATR_14'] / df['Close']) >= 0.01

        # We want the 14-day ATR to STILL be lower than 50-day ATR,
        # meaning the explosion has just started and has room to grow.
        contracting_volatility = df['ATR_14'] < df['ATR_50']
        is_volatile = baseline_volatility & contracting_volatility

        # 6. Final Institutional Alignments
        # BULLISH FIRE: It fired today + Uptrend Math + Tightly Coiled Yesterday
        bullish_bias = (
                squeeze_fired_today &
                (df['SMA_20'] > df['EMA_50']) &
                ema_50_rising &
                strong_bull_rsi &
                was_tightly_coiled &
                is_volatile
        )

        # BEARISH FIRE: It fired today + Downtrend Math + Tightly Coiled Yesterday
        bearish_bias = (
                squeeze_fired_today &
                (df['SMA_20'] < df['EMA_50']) &
                ema_50_falling &
                strong_bear_rsi &
                was_tightly_coiled &
                is_volatile
        )

        conditions = [bullish_bias, bearish_bias]
        choices = ['BULLISH', 'BEARISH']

        return pd.Series(np.select(conditions, choices, default=""), index=df.index)


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
        fresh_breakout_up = (df['Close'] > res_60) & (df['Close'] < (res_60 * df['ATR_14']))

        # Price crossed support, BUT is not extended more than 3% below it
        fresh_breakdown_down = (df['Close'] < sup_60) & (df['Close'] > (sup_60 * df['ATR_14']))

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
        body_size = (df['Close'] - df['Open']).abs().clip(lower=0.001)
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
        rsi_bullish = df['RSI'] > settings.BULLISH_RSI
        rsi_bearish = df['RSI'] < settings.BEARISH_RSI

        # # 🔥 6. THE NEW VOLATILITY FILTER (The "Juice" Check)
        # # The stock's average daily move must be strictly greater than 2% of its price
        # high_volatility = df['ATR'] > (df['Close'] * 0.02)

        # Condition A: Absolute Baseline.
        # Must be capable of moving at least 1% a day (Captures Nifty 50 Large Caps)
        # baseline_volatility = (df['ATR_14'] / df['Close']) >= 0.01
        is_volatile = (df['ATR_14'] / df['Close']) >= 0.01

        # Condition B: Volatility Expansion.
        # The short-term ATR (14 days) should be higher than the long-term ATR (50 days).
        # This proves the stock is currently "waking up" and momentum is building.
        # expanding_volatility = df['ATR_14'] > df['ATR_50']

        # Final Volatility Check
        # is_volatile = baseline_volatility & expanding_volatility


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


