import pandas as pd
import numpy as np

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange


class AnalyticsEngine:
    def __init__(self):
        pass

    def add_RSI(self, data: list[dict], period: int = 14):
        data_df = pd.DataFrame(data)
        # ta_data = ta.add_momentum_ta(
        #     pd.DataFrame(data),
        #     "High",
        #     "Low",
        #     "Close",
        #     "Volume",
        #
        # )
        # return ta_data.to_dict(orient="records")
        ## Series is column extracted from dataframe, s.to_frame().T -> series to frame
        rsi = RSIIndicator(close=data_df["Close"], window=period).rsi()
        data_df = data_df.where(pd.notnull(data_df), None)  # Json Sanitizer
        # where SQL vs DB sql m condition satisfy krne wala data return krta h, pandas m condition satisfy krne wale ko as it is rkhta h aur unsatisfied ko alternate se replace kr deta hai
        data_df['RSI'] = rsi
        return data_df.to_dict()

    def add_exec_indicators(self, data: list[dict], time_frame: str = "30m", rsi_period: int = 14) -> list[dict]:
        # 1. Convert to DataFrame
        data_df = pd.DataFrame(data)

        # 2. Calculate Indicators (Math Layer)
        rsi = RSIIndicator(close=data_df["Close"], window=rsi_period).rsi()
        ema_9 = EMAIndicator(close=data_df["Close"], window=9).ema_indicator()
        ema_21 = EMAIndicator(close=data_df["Close"], window=21).ema_indicator()

        # 3. Add columns to DataFrame
        data_df['RSI'] = rsi
        data_df['EMA_9_EXEC'] = ema_9
        data_df['EMA_21_EXEC'] = ema_21

        # VOLUME CALCULATION (Pure Pandas, no TA library needed)
        data_df['VOL_SMA_20'] = data_df['Volume'].rolling(window=20).mean()

        # 4. Clean Data (Sanitize NaNs to None AT THE VERY END)
        data_df = data_df.where(pd.notnull(data_df), other=None)

        # 5. Return as a list of dictionaries
        return data_df.to_dict(orient="records")

    def add_dir_indicators(self, data: list[dict], time_frame: str = "1d", rsi_period: int = 14) -> list[dict]:
        data_df = pd.DataFrame(data)

        # 2. Calculate Indicators (Math Layer)
        rsi = RSIIndicator(close=data_df["Close"], window=rsi_period).rsi()
        ema_50 = EMAIndicator(close=data_df["Close"], window=50).ema_indicator()
        ema_200 = EMAIndicator(close=data_df["Close"], window=200).ema_indicator()

        # 3. Add columns to DataFrame
        data_df['RSI'] = rsi
        data_df['ema_50'] = ema_50
        data_df['ema_200'] = ema_200

        # VOLUME CALCULATION (Pure Pandas, no TA library needed)
        data_df['VOL_SMA_20'] = data_df['Volume'].rolling(window=20).mean()

        # 4. Clean Data (Sanitize NaNs to None AT THE VERY END)
        data_df = data_df.where(pd.notnull(data_df), None)

        # 5. Return as a list of dictionaries
        return data_df.to_dict(orient="records")

    def get_asset_direction(self, data: list[dict]) -> list[dict]:
        """
        Calculates the broader market trend using 1-Day data.
        Uses STATE logic: 50 EMA vs 200 EMA crossover + RSI Momentum.
        """
        df = pd.DataFrame(data)

        # Higher timeframe relies on 'STATE' Confluence (Trend + Momentum)
        conditions = [
            # 🟢 BULLISH TREND: 50 EMA is ABOVE 200 EMA AND Daily RSI > 50
            (df['ema_50'] > df['ema_200']) & (df['RSI'] > 50),

            # 🔴 BEARISH TREND: 50 EMA is BELOW 200 EMA AND Daily RSI < 50
            (df['ema_50'] < df['ema_200']) & (df['RSI'] < 50)
        ]

        choices = ['BULLISH', 'BEARISH']

        # Add DIRECTION column.
        # If EMA is bullish but RSI is weak (divergence), it defaults to SIDEWAYS.
        df['DIRECTION'] = np.select(conditions, choices, default='SIDEWAYS')

        # Sanitize NaNs (EMA 200 will have 200 days of NaNs initially)
        df = df.where(pd.notnull(df), other=None)

        return df.to_dict(orient="records")

    def generate_signals(self, data: list[dict]):
        # if data[-1]["rsi"] > 60 and  data[-1]["EMA_9_EXEC"] > data[-1]["EMA_21_EXEC"] and data[-1]["Volume"] > 1.2 * data[-1]["VOL_SMA_20"]:
        #     return "buy"
        df = pd.DataFrame(data)
        conditions = [
            (df["EMA_9_EXEC"] > df["EMA_21_EXEC"]) & (df["EMA_9_EXEC"].shift(1) <= df["EMA_21_EXEC"].shift(1)) & df[
                "RSI"] > 60 & (df['Volume'] > 1.2 * df['VOL_SMA_20']),

            (df['EMA_9_EXEC'] < df['EMA_21_EXEC']) &
            (df['EMA_9_EXEC'].shift(1) >= df['EMA_21_EXEC'].shift(1)) &
            (df['RSI'] < 40)
        ]
        choices = ['BUY', 'SELL']
        df["SIGNAL"] = np.select(conditions, choices, default="HOLD")
        df = df.where(pd.notnull(df), other=None)
        return df.to_dict(orient="records")

    def add_coiled_spring_indicators(self, data: list[dict]) -> list[dict]:
        '''
        Calculates indicators for the 'Coiled Spring' Breakout Strategy.
        Focuses on Squeeze, Momentum, Trend, and Volume Surge.
        :param data:
        :return: 50EMA, Bollinger Bands, RSI, VOL_SMA_20, ATR, PIVOTS (R1,R2, S1, S2)
        '''
        df = pd.DataFrame(data)

        # 1. The Trend Filter (Institutional Bias)
        ema_50 = EMAIndicator(close=df['Close'], window=50)
        df['EMA_50'] = ema_50.ema_indicator()
        df['SMA_20'] = df["Close"].rolling(window=20).mean()


        # 2. The Squeeze (Bollinger Band Width)
        bb_ind = BollingerBands(close=df['Close'], window=20, window_dev=2)
        df['BBU'] = bb_ind.bollinger_hband()
        df['BBL'] = bb_ind.bollinger_lband()
        # df['BBM'] = bb_ind.bollinger_mavg()
        # df['BB_Width'] = (df['BBU'] - df['BBL']) / df['BBM']

        # 3. The Momentum (RSI 14)
        rsi_ind = RSIIndicator(close=df['Close'], window=14)
        df['RSI'] = rsi_ind.rsi()

        # 4. Execution Levels (ATR & Pivots)
        atr_ind = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['ATR'] = atr_ind.average_true_range()

        # 5. Keltner Channels (Historical Range) -> kc_mult is usually 1.5
        kc_mult = 1.5
        df['KCU'] = df['SMA_20'] + (kc_mult * df['ATR'])
        df['KCL'] = df['SMA_20'] - (kc_mult * df['ATR'])

        # 🔥 ENGINE 1: True TTM Squeeze Condition (BB strictly inside KC)
        df['Squeeze_On'] = (df['BBU'] < df['KCU']) & (df['BBL'] > df['KCL'])

        # 🔥 ENGINE 2: Momentum Breakout (LONG) & Breakdown (SHORT)
        # --- LONG SETUP (Bullish) ---
        df['Resistance_Level'] = df['High'].shift(1).rolling(window=20).max()
        df['Is_Breakout_Up'] = df['Close'] > df['Resistance_Level']
        df['In_Uptrend'] = df['Close'] > df['SMA_20']

        # --- SHORT SETUP (Bearish) ---
        df['Support_Level'] = df['Low'].shift(1).rolling(window=20).min()
        df['Is_Breakout_Down'] = df['Close'] < df['Support_Level']
        df['In_Downtrend'] = df['Close'] < df['SMA_20']

        # --- VOLUME CONFIRMATION (Dono ke liye zaroori hai) ---
        df['VOL_SMA_20'] = df['Volume'].rolling(window=20).mean()
        df['High_Volume'] = df['Volume'] > (1.5 * df['VOL_SMA_20'])

        # --- COMBINED SIGNALS ---
        df['Bullish_Momentum'] = df['Is_Breakout_Up'] & df['High_Volume'] & df['In_Uptrend']
        df['Bearish_Momentum'] = df['Is_Breakout_Down'] & df['High_Volume'] & df['In_Downtrend']

        # Agar Bullish ya Bearish mein se ek bhi true hai, toh signal ON hai
        df['Momentum_Signal'] = df['Bullish_Momentum'] | df['Bearish_Momentum']

        # Base Pivot
        df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3

        # Level 1 (First Targets / Immediate Support-Resistance)
        df['S1'] = (2 * df['Pivot']) - df['High']
        df['R1'] = (2 * df['Pivot']) - df['Low']

        # Level 2 (Second Targets / Extended Move)
        df['S2'] = df['Pivot'] - (df['High'] - df['Low'])
        df['R2'] = df['Pivot'] + (df['High'] - df['Low'])

        # 6. JSON Sanitizer (The Pandas Trick)
        df = df.where(pd.notnull(df), other=None)

        return df.to_dict(orient="records")
