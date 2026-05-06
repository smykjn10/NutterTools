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
        squeeze_fired_today = squeeze_on.shift(1).fillna(False) & ~squeeze_on  # TODO Try 1

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
                (df['RSI'] > settings.BULLISH_RSI) &  # > 60 means the stock is explicitly in a "Mark-Up" phase
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


import pandas as pd
import numpy as np


# from your_module import ITradingStrategy, settings # (Make sure to import your interfaces/settings)

class PullbackBounceSetup(ITradingStrategy):
    @property
    def name(self) -> str:
        '''
            "mean reversion" principle—the idea that even in a strong trend, prices eventually return to their average before continuing the move.
            Upgraded with Factor-Based Scoring & Noise Reduction.
        '''
        return "20_EMA_PULLBACK"

    def generate_signal(self, df: pd.DataFrame) -> pd.Series:
        # 1. Macro Trend & Tension Validation
        # Using shift(1) to ensure the slope is rising compared to yesterday
        ema_50_rising = df['EMA_50'] > df['EMA_50'].shift(1)
        ema_50_falling = df['EMA_50'] < df['EMA_50'].shift(1)

        ema_20_above_50 = df['EMA_20'] > df['EMA_50']
        ema_20_below_50 = df['EMA_20'] < df['EMA_50']

        # 🚀 OPTIMIZATION: Trend Expansion (Gap between EMAs should not be shrinking)
        ema_gap_bull = (df['EMA_20'] - df['EMA_50']) >= (df['EMA_20'].shift(1) - df['EMA_50'].shift(1))
        ema_gap_bear = (df['EMA_50'] - df['EMA_20']) >= (df['EMA_50'].shift(1) - df['EMA_20'].shift(1))

        # 2. Volume Logic: Smart Dry up during pullback, SURGE on bounce
        # Using a 3-day rolling mean for previous days to smooth out isolated volume spikes
        avg_vol_last_3_days = df['Volume'].shift(1).rolling(window=3).mean()
        prev_sma_20_vol = df['VOL_SMA_20'].shift(1)

        pre_bounce_dryup = avg_vol_last_3_days < prev_sma_20_vol
        # 🚀 OPTIMIZATION: Smart Money footprint (Volume expanded on bounce day)
        bounce_volume_surge = df['Volume'] > df['Volume'].shift(1)

        # 3. The Bounce Logic (Zones + Risk Reward)
        # Bullish rules
        # Max 2% deep filter to reject fake-outs that crash through EMA
        dipped_to_ema_bull = (df['Low'] <= df['EMA_20']) & (df['Low'] >= (df['EMA_20'] * 0.98))
        closed_above_ema = df['Close'] > df['EMA_20']
        prev_closed_above_ema = df['Close'].shift(1) > df['EMA_20'].shift(1)
        green_candle = df['Close'] > df['Open']  # Replaces strict wick math
        # 🚀 OPTIMIZATION: Risk-Reward check (Close within 2.5% of EMA)
        close_near_ema_bull = df['Close'] <= (df['EMA_20'] * 1.025)

        # Bearish rules (Exact Inverse)
        dipped_to_ema_bear = (df['High'] >= df['EMA_20']) & (df['High'] <= (df['EMA_20'] * 1.02))
        closed_below_ema = df['Close'] < df['EMA_20']
        prev_closed_below_ema = df['Close'].shift(1) < df['EMA_20'].shift(1)
        red_candle = df['Close'] < df['Open']
        close_near_ema_bear = df['Close'] >= (df['EMA_20'] * 0.975)

        # 4. Momentum & Volatility
        # Feel free to change 55/45 to settings.BULLISH_RSI / settings.BEARISH_RSI if imported
        rsi_bullish = df['RSI'] > settings.BULLISH_RSI
        rsi_bearish = df['RSI'] < settings.BEARISH_RSI

        # The "Juice" Check - Must be capable of moving at least 2% a day
        is_volatile = (df['ATR_14'] / df['Close']) >= 0.02

        # ---------------------------------------------------------
        # 🧠 5. THE SCORING ENGINE (Factor-Based Weightage)
        # ---------------------------------------------------------

        # Calculate Bullish Sub-Scores (Converting True/False to 1/0 and multiplying by weights)
        bull_score = (
                ((dipped_to_ema_bull & closed_above_ema & close_near_ema_bull & green_candle).astype(int) * 35) +
                ((ema_20_above_50 & ema_50_rising & ema_gap_bull).astype(int) * 25) +
                ((pre_bounce_dryup & bounce_volume_surge).astype(int) * 20) +
                (rsi_bullish.astype(int) * 10) +
                (is_volatile.astype(int) * 10)
        )

        # Calculate Bearish Sub-Scores
        bear_score = (
                ((dipped_to_ema_bear & closed_below_ema & close_near_ema_bear & red_candle).astype(int) * 35) +
                ((ema_20_below_50 & ema_50_falling & ema_gap_bear).astype(int) * 25) +
                ((pre_bounce_dryup & bounce_volume_surge).astype(int) * 20) +
                (rsi_bearish.astype(int) * 10) +
                (is_volatile.astype(int) * 10)
        )

        # Inject the strength score directly into the dataframe for the execution engine
        # (It stores whichever score is higher)
        df[f'{self.name}_STRENGTH'] = np.where(bull_score >= bear_score, bull_score, bear_score)

        # Threshold Rule: Signal triggers ONLY if conviction is 75 or higher out of 100
        MINIMUM_THRESHOLD = 75

        bull_signal_passed = bull_score >= MINIMUM_THRESHOLD
        bear_signal_passed = bear_score >= MINIMUM_THRESHOLD

        conditions = [bull_signal_passed, bear_signal_passed]
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

        bullish_coil = base_coil & ema_20_above_50 & (df['RSI'] > 50)
        bearish_coil = base_coil & ema_20_below_50 & (df['RSI'] < 50)

        conditions = [bullish_coil, bearish_coil]
        choices = ['BULLISH', 'BEARISH']

        # Using "" for clean JSON serialization later
        return pd.Series(np.select(conditions, choices, default=""), index=df.index)
