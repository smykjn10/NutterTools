from abc import ABC, abstractmethod


class Rectangle(ABC):
    def __init__(self,width, height):
        self._width = width
        self._height = height


    @abstractmethod
    def area(self):
        return self._width * self._height

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height

    @abstractmethod
    def set_width(self, width):
        self._width = width

    @abstractmethod
    def set_height(self, height):
        self._height = height


class Sqaure(Rectangle):
    def __init__(self,size):
        super().__init__(size,size)

    def set_width(self, width):
        self._width = self._height = width

    def set_height(self, height):
        self._width = self._height = height

    def area(self):
        return self._width * self._height



s = Sqaure(5)
s.set_width(10)
print(s.area())

import asyncio
import time


# ==========================================
# 1. THE BLOCKING FUNCTION (e.g., yfinance)
# ==========================================
def fetch_data_blocking(symbol: str, timeframe: str, delay: int) -> dict:
    """Yeh ek slow, synchronous function hai jo thread ko block karta hai."""
    print(f"[⚙️ Thread] Fetching {timeframe} data for {symbol}...")
    time.sleep(delay)  # Network latency simulate kar rahe hain
    print(f"[✅ Thread] {timeframe} data fetched!")
    return {"symbol": symbol, "timeframe": timeframe, "status": "success"}


# ==========================================
# 2. THE ASYNC ENGINE (FastAPI Route/Main)
# ==========================================
async def main():
    print("🚀 Main Event Loop Started...\n")

    # --- PATTERN 1: Single Background Task ---
    print("⏳ Executing single to_thread call...")
    # Syntax: asyncio.to_thread(function_name, arg1, arg2...)
    data_30m = await asyncio.to_thread(fetch_data_blocking, "RELIANCE.NS", "30m", 2)
    print(f"Result 1: {data_30m}\n")

    # --- PATTERN 2: Concurrent Background Tasks (Phase 2 Masterplan) ---
    print("⏳ Executing multiple timeframes concurrently...")
    # asyncio.gather in background threads ko ek sath chalayega
    results = await asyncio.gather(
        asyncio.to_thread(fetch_data_blocking, "RELIANCE.NS", "30m", 3),
        asyncio.to_thread(fetch_data_blocking, "RELIANCE.NS", "1D", 3)
    )

    print("\n🎉 Dono data ek sath aa gaye (Total time: ~3 seconds, not 6!):")
    print(f"Result 30m: {results[0]}")
    print(f"Result 1D: {results[1]}")


# Run the async app
if __name__ == "__main__":
    asyncio.run(main())