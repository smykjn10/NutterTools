from enum import Enum

# Standardized Enums for the Trading Bot
class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class Trend(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"

class BrokerType(str, Enum):
    GROWW = "GROWW"
    YFINANCE = "YFINANCE"
    MOCK = "MOCK"

# The Master F&O Universe List (Constant)
# Tum isme apne hisaab se aur stocks add kar sakte ho
FNO_UNIVERSE = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT",
    "AXISBANK", "BAJFINANCE", "MARUTI", "ASIANPAINT"]


