import pandas as pd
import numpy as np

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import asyncio
from data_fetcher import DataFetcher


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

    # def generate_signals(self, data: list[dict], direction:str):
    #     """
    #     :param data:
    #     :param direction: we are taking as input since we are making this function dependent and if it's None function does not check the direction on big timeframe it just create signals
    #     1. check direction -> since direction is based on 1d time frame we do not need to run it everytime but each time we are getting different asset we have to handle that
    #
    #     2. generate signal
    #         a) if dir is upside -> Buy if
    #             check 9_EMA > 21_EMA, RSI> 58, Volume > 1.4* Average volume, price has crossed Resistance, retest done
    #     :return: buy or sell or hold conviction, stop loss, targets list t1-->tn
    #     """
    #     data_fetcher = DataFetcher()
    #     fetch_asset_direction_data = data_fetcher.fetch_history_data()
    #     direction = self.get_asset_direction()

    # def execution_engine(self,data:list[dict],time_frame:str)->list[dict]:
    #     EMA_9 =
    #     EMA_21 =
    #     RSI_14 =
    #     VOL_SMA_20 =
    #
    #     pass
