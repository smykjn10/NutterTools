import pytz
from datetime import datetime
from typing import Any
import pandas as pd
from enums import FNO_UNIVERSE
from .data_fetcher import BulkDataFetcher
from .analytics_engine import AnalyticsEngine


class ScreenerService:
    def __init__(self, bulk_fetcher:BulkDataFetcher, analytics_engine:AnalyticsEngine):
        self.bulk_fetcher = bulk_fetcher
        self.analytics_engine = analytics_engine

        self.processed_universe_cache = []

    def _get_safest_closed_candle(self, df: pd.DataFrame) -> dict:
        """
        Protects the bot from Look-Ahead Bias by ensuring it only
        calculates setups on fully closed daily candles.
        """
        if df.empty:
            return {}

        # Convert DataFrame back to list of dicts for easy indexing
        processed_data = df.to_dict(orient="records")

        if len(processed_data) < 2:
            return processed_data[-1]  # Fallback if data is too short

        latest_candle = processed_data[-1]

        # Get Current Time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)

        # Safely extract Date (Handling both string and datetime objects)
        candle_date_val = latest_candle.get('Date', latest_candle.get('Datetime'))
        if isinstance(candle_date_val, str):
            try:
                candle_date = datetime.strptime(candle_date_val, '%Y-%m-%d').date()
            except ValueError:
                candle_date = datetime.strptime(candle_date_val, '%Y-%m-%d %H:%M:%S').date()
        else:
            candle_date = candle_date_val.date() if hasattr(candle_date_val, 'date') else candle_date_val

        is_today_candle = (candle_date == now.date())

        # Market is "Open" (or post-market settlement) before 15:30 IST
        is_market_open = now.hour < 15 or (now.hour == 15 and now.minute < 30)

        # Logic Branch
        if is_today_candle and is_market_open:
            # 🚨 DANGER: Live fluctuating candle! Fallback to yesterday.
            print(
                f"⚠️ Detected live forming candle. Falling back to previous day's closed candle for accurate setup signals.")
            return processed_data[-2]
        else:
            # ✅ SAFE: Either morning run (yesterday's data) or evening run (today's closed data).
            return processed_data[-1]

    def _calculate_confidence_score(self, candle: dict, setup_name: str) -> int:
        """
        Calculates a 1-100 confidence score based on the strategy's core math.
        Helps in sorting the watchlist for highest probability trades.
        """
        score = 50  # Base score

        # 1. TTM SQUEEZE FIRE Confidence
        if setup_name == "TTM_SQUEEZE_FIRE":
            rsi = candle.get('RSI', 50)
            if rsi > 60 or rsi < 40: score += 20  # Strong momentum
            if candle.get('SMA_20', 1) > 0:
                dist = abs(candle.get('Close', 0) - candle.get('SMA_20', 0)) / candle.get('SMA_20', 1)
                if dist < 0.01: score += 20  # Tightly coiled right before the fire

        # 2. INSTITUTIONAL BREAKOUT Confidence
        elif setup_name == "INSTITUTIONAL_BREAKOUT":
            vol = candle.get('Volume', 0)
            avg_vol = candle.get('VOL_SMA_20', 1)
            if vol > (2 * avg_vol):
                score += 30  # Massive volume explosion
            elif vol > (1.5 * avg_vol):
                score += 15

        # 3. 20 EMA PULLBACK Confidence
        elif setup_name == "20_EMA_PULLBACK":
            body = abs(candle.get('Close', 0) - candle.get('Open', 0))
            if body > 0:
                dist_ema = abs(candle.get('Close', 0) - candle.get('EMA_20', 0)) / candle.get('EMA_20', 1)
                if dist_ema < 0.005: score += 25  # Price kissed the EMA perfectly

        # 4. COIL NR4 Confidence
        elif setup_name == "COIL_NR4":
            vol = candle.get('Volume', 0)
            avg_vol = candle.get('VOL_SMA_20', 1)
            if vol < (0.5 * avg_vol): score += 30  # Extreme volume dry-up (Smart money is dead silent)

        # Cap score at 99
        return min(score, 99)

    async def generate_watchlist(self, app_state: Any, requested_universe: list[str] = None) -> dict[str, dict]:
        today_str = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
        # 1. Determine target universe
        target_universe = requested_universe if requested_universe else FNO_UNIVERSE
        if hasattr(app_state, "watchlist_cache_date") and app_state.watchlist_cache_date == today_str:
            # analysed stock in the watchlist
            cached_dict = app_state.watchlist_cache
            if not requested_universe:
                print("⚡ Returning Master Watchlist from App State Cache")
                return cached_dict
            else:
                # requested_universe is subset of watchlist cache
                if set(target_universe).issubset(set(cached_dict)):
                    print(f"⚡ Cache Hit! Retrieving pre-analyzed setups from internal state...")
                    if set(target_universe) == set(cached_dict):
                        return cached_dict
                    return {sym: cached_dict[sym] for sym in requested_universe}

        # 🔄 CACHE MISS (Analyze and Process)
        print(f"🔄 Cache Miss! Fetching & Analyzing 3-month data for {len(target_universe)} stocks...")
        # fetch data
        processed_bulk_data = {}
        raw_data_dict = self.bulk_fetcher.fetch_bulk_history(target_universe,interval="1d", period="1y")
        watchlist: dict[str, dict] = {}
        strategy_names = [s.name for s in self.analytics_engine.strategies]
        for symbol, raw_data in raw_data_dict.items():
            if not raw_data or len(raw_data) < 55:
                continue
            try:
                processed_df = self.analytics_engine.process_stock(raw_data)
            except Exception as e:
                print(f"⚠️ Analytics error for {symbol}: {e}")
                continue
            if processed_df.empty:
                continue
            processed_bulk_data[symbol] = processed_df.to_dict(orient="records")
            latest_candle = self._get_safest_closed_candle(processed_df)
            if not latest_candle:
                continue

            active_signals = []
            for name in strategy_names:
                sig = latest_candle.get(f"SIGNAL_{name}","")
                if sig in ["BULLISH", "BEARISH"]:
                    confidence = self._calculate_confidence_score(latest_candle, name)
                    active_signals.append({
                        "setup": name,
                        "direction": sig,
                        "confidence": confidence
                    })
                    # If stock triggered any setup, add to Dictionary using Symbol as Key
                    if active_signals:
                        watchlist[symbol] = {
                            # "symbol": symbol, # Optional now, but good for redundancy
                            "date": str(latest_candle.get("Date", "")),
                            "close": round(latest_candle.get("Close", 0), 2),
                            "volume": int(latest_candle.get("Volume", 0)),
                            "atr_14": round(latest_candle.get("ATR_14", 0), 2),
                            "signals": active_signals
                        }

        # 5. UPDATE MASTER CACHE
        # print(processed_bulk_data)
        if not requested_universe and app_state:
            app_state.watchlist_cache = watchlist
            app_state.watchlist_cache_date = today_str
            print(f"💾 Updated Master Watchlist Cache for {today_str}")
        return watchlist
