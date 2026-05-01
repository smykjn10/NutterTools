import os, pytz
from datetime import  datetime
from enums import Trend, FNO_UNIVERSE
from typing import Any
from dotenv import load_dotenv

load_dotenv()


class ScreenerService:
    def __init__(self, bulk_fetcher, analytic_engine):
        # 💉 Dependency Injection
        self._bulk_fetcher = bulk_fetcher
        self._analytics_engine = analytic_engine
        # 🧠 Internal State for Caching (Memoization)
        self._cached_universe = []
        self._cached_results = {}

    def _calculate_confidence(self, bb_width: float, vol_ratio: float, rsi: float, trend: Trend):
        """
        Grades the 'Coiled Spring' setup out of 100 based on intensity.
        Returns the score and an options position size multiplier.
        """
        score = 0

        # 1. Squeeze Quality (Max 40) - Tighter is better
        if bb_width < 0.02:
            score += 40
        elif bb_width < 0.03:
            score += 30
        elif bb_width < 0.04:
            score += 20
        elif bb_width < 0.05:
            score += 10

        # 2. Volume Surge (Max 35) - Higher surge is better
        if vol_ratio >= 2.5:
            score += 35
        elif vol_ratio >= 2.0:
            score += 25
        elif vol_ratio >= 1.5:
            score += 15
        elif vol_ratio > 1.0:
            score += 5

        # 3. Momentum Intensity (Max 25) - Stronger RSI is better
        if trend == Trend.BULLISH:
            if rsi >= 65:
                score += 25
            elif rsi >= 60:
                score += 15
            elif rsi >= 55:
                score += 5
        else:  # BEARISH
            if rsi <= 35:
                score += 25
            elif rsi <= 40:
                score += 15
            elif rsi <= 45:
                score += 5

        # Determine Position Size Multiplier for Risk Management
        if score >= 80:
            multiplier = 1.0  # A-Grade: Full Quantity (High Conviction)
        elif score >= 55:
            multiplier = 0.5  # B-Grade: Half Quantity (Moderate Conviction)
        else:
            multiplier = 0.25  # C-Grade: Test Quantity (Low Conviction)

        return {"score": score, "size_multiplier": multiplier}

    def _get_safest_closed_candle(self, processed_data: list) -> dict:
        """
        Protects the bot from Look-Ahead Bias by ensuring it only
        calculates setups on fully closed daily candles.
        """
        latest_candle = processed_data[-1]

        # Get Current Time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

        # Assuming your data_fetcher keeps 'Date' as a datetime object
        # yfinance puts daily candle dates at 00:00:00
        candle_date = latest_candle['Date'].date() if hasattr(latest_candle['Date'], 'date') else latest_candle['Date']

        is_today_candle = (candle_date == now.date())

        # Market is "Open" (or post-market settlement) before 15:30
        is_market_open = now.hour < 15 or (now.hour == 15 and now.minute < 30)

        if is_today_candle and is_market_open:
            # 🚨 DANGER: Live fluctuating candle! Fallback to yesterday.
            # print("⚠️ Detected live candle. Falling back to previous day's closed candle.")
            return processed_data[-2]
        else:
            # ✅ SAFE: Either morning run (yesterday's data) or evening run (today's closed data).
            return processed_data[-1]

    async def get_daily_watchlist(self, requested_universe: list[str] = None) -> dict[str, dict[str, Any]]:
        '''
        1. check requested universe exists in or equal to  the list of stocks or our universe processed earlier or not
        2. if yes then return from state
        3. else: analyse them and return whole data
        '''
        # 1. Determine target universe
        target_universe = requested_universe if requested_universe else FNO_UNIVERSE

        # 🛡️ THE CACHE CHECK (O(1) Retrieval if subset)
        if self._cached_universe and set(target_universe).issubset(set(self._cached_universe)):
            print("⚡ Cache Hit! Retrieving pre-analyzed setups from internal state...")
            # 🚀 NEW OPTIMIZATION: Agar dono barabar hain, toh direct cache return maar do! (Zero Loop)
            if set(target_universe) == set(self._cached_universe):
                return self._cached_results

            # 🎯 FILTER: Agar user ne choti list maangi hai, toh filter karke do (Maintain Order)
            return {
                sym: self._cached_results[sym]
                for sym in self._cached_results
                if sym in target_universe
            }

        # 🔄 CACHE MISS (Analyze and Process)
        print(f"🔄 Cache Miss! Fetching & Analyzing 3-month data for {len(target_universe)} stocks...")
        all_data = self._bulk_fetcher.fetch_bulk_history(target_universe, period="1y", interval="1d")
        results = {}
        squeeze_threshold = os.environ.get("SQUEEZE_THRESHOLD")
        # 2. Add analytical indicators to each stock in the universe
        for symbol, raw_data_list in all_data.items():
            # Need at least 55 days for EMA_50 to calculate properly
            if not raw_data_list or len(raw_data_list) < 55:
                continue

                # 🧮 Delegate Math to Analytics Engine
            try:
                processed_data = self._analytics_engine.add_coiled_spring_indicators(raw_data_list)
            except Exception as e:
                print(f"⚠️ Analytics error for {symbol}: {e}")
                continue

            # latest = processed_data[-1]
            latest = self._get_safest_closed_candle(processed_data)
            # Defensive check for missing core indicators
            if latest.get('EMA_50') is None or latest.get('BB_Width') is None:
                continue

            # Extract variables for readability
            close_price = latest['Close']
            volume = latest['Volume']
            ema_50 = latest['EMA_50']
            bb_width = latest['BB_Width']
            rsi = latest['RSI']
            vol_sma = latest['VOL_SMA_20']

            # 🚦 Rule 1 & 2: Squeeze and Volume Filters
            vol_ratio = volume / vol_sma if vol_sma else 0
            is_squeezed = bb_width < squeeze_threshold
            has_volume = vol_ratio > 1.0
            if is_squeezed and has_volume:
                direction = None

                # 🚦 Rule 3 & 4: Trend and Momentum Alignment
                if close_price > ema_50 and rsi > 55:
                    direction = Trend.BULLISH
                elif close_price < ema_50 and rsi < 45:
                    direction = Trend.BEARISH
                else:
                    continue  # Squeeze + Volume is there, but direction is unclear. Ignore!

                # 🧠 Apply Quant Confidence Scoring
                confidence_data = self._calculate_confidence(bb_width, vol_ratio, rsi, direction)

                # 🎯 Setup Found! Build the clean JSON response
                results[symbol] = {
                    "direction": direction.value,
                    "confidence_score": confidence_data["score"],
                    "qty_multiplier": confidence_data["size_multiplier"],
                    "close": round(close_price, 2),
                    "S1": round(latest['S1'], 2),
                    "R1": round(latest['R1'], 2),
                    "S2": round(latest['S2'], 2),
                    "R2": round(latest['R2'], 2),
                    "ATR": round(latest['ATR'], 2),
                    "bb_width": round(bb_width, 4),
                    "rsi": round(rsi, 2),
                    "volume_ratio": round(vol_ratio, 2)
                }

        # 🥇 Sort results first
        sorted_results = dict(
            sorted(results.items(), key=lambda item: item[1]['confidence_score'], reverse=True))

        # 💾 UPDATE THE STATE WITH SORTED DATA!
        self._cached_universe = target_universe
        self._cached_results = sorted_results  # 👈 Storing the pre-sorted dictionary

        print(f"✅ [Screener] Processing Complete. Found {len(sorted_results)} blast-ready setups.")
        return sorted_results
