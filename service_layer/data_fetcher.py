import time

import yfinance as yf
import pandas as pd
from typing import List, Dict



class DataFetcher:

    def fetch_history_data(self, asset: str, period: str = "1mo", interval: str = "1d"):
        '''
        Currently this function can handle only 1d interval # TODO
        :param asset:
        :param period:
        :param interval:
        :return:
        '''
        try:
            stock = yf.Ticker(asset + ".NS")
            stock_history = stock.history(period=period, interval=interval)
            stock_history = stock_history.reset_index()
            if stock_history.empty:
                return []
            stock_history['Date'] = stock_history['Date'].dt.strftime('%Y-%m-%d')
            return stock_history.to_dict(orient="records")
        except Exception as e:
            print(str(e))
            raise





class BulkDataFetcher:
    def __init__(self):
        self.suffix = ".NS"

    def fetch_bulk_history(self, stock_list:list[str], interval: str = "1d", period:str = "1y",retries:int=3)->dict[str,pd.DataFrame]:
        stock_data = {}
        if not stock_list:
            return stock_data
        stock_list = [f"{stock}{self.suffix}" for stock in stock_list]
        print(f"📡 Downloading bulk data for {len(stock_list)} assets...")
        data = pd.DataFrame()
        for attempt in range(retries):
            try:
                data = yf.download(
                    period=period,
                    interval=interval,
                    tickers=stock_list,
                    group_by='ticker',
                    auto_adjust=True,
                    threads=True,
                    progress=True
                )
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                else:
                    return stock_data
            else:
                if data.empty:
                    return stock_data
                else:
                    break

        is_intraday = interval != "1d"
        is_multi_index = isinstance(data.columns, pd.MultiIndex)

        for s in stock_list:
            if is_multi_index:
                if s in data.columns.levels[0]:
                    df_ticker = data[s].copy()
                else:
                    continue
            else:
                # If only 1 symbol was requested, 'data' is already the target DataFrame
                df_ticker = data.copy()
            df_ticker = df_ticker.dropna()
            if df_ticker.empty:
                continue
            # Extract Datetime from Index to a Column
            df_ticker = df_ticker.reset_index()
            date_col = next((col for col in ["Datetime", "Date", "index"] if col in df_ticker.columns), None)
            if date_col:
                # Guarantee datetime format
                df_ticker[date_col] = pd.to_datetime(df_ticker[date_col])

                # Modern Check: Fix Timezone mapping to standard IST
                if df_ticker[date_col].dt.tz is not None:
                    df_ticker[date_col] = df_ticker[date_col].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)

                # JSON-Safe Formatting based on timeframe (Required since we are returning list[dict])
                if is_intraday:
                    df_ticker[date_col] = df_ticker[date_col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    df_ticker.rename(columns={date_col: 'Datetime'}, inplace=True)
                else:
                    df_ticker[date_col] = df_ticker[date_col].dt.strftime('%Y-%m-%d')
                    df_ticker.rename(columns={date_col: 'Date'}, inplace=True)

                # Return clean JSON structure for independent modules (Original Architecture)
            stock_data[s] = df_ticker

        return stock_data




class BulkDataFetcher_BKP_2:
    def __init__(self):
        # Indian stocks need .NS suffix for Yahoo Finance
        self.suffix = ".NS"

    # 👑 FIX 1: Default period is now "1y" to give AnalyticsEngine enough data for 60-day channels & 50-EMA
    def fetch_bulk_history(self, symbols: List[str], interval: str = "1d", period: str = "1y") -> Dict[str, list[dict]]:
        """
        Fetches data for multiple stocks in O(1) network call.
        Returns: A dictionary where key is symbol and value is its JSON-serializable list of dicts.
        """
        if not symbols:
            return {}

        formatted_symbols = [f"{s}{self.suffix}" for s in symbols]
        print(f"📡 Downloading bulk data for {len(symbols)} assets...")

        try:
            # data is a DataFrame (MultiIndex if len(symbols) > 1, flat if len(symbols) == 1)
            data = yf.download(
                tickers=formatted_symbols,
                period=period,
                interval=interval,
                group_by='ticker',
                threads=True,
                progress=False,
                auto_adjust=True
            )
        except Exception as e:
            print(f"❌ Bulk Download Error: {e}")
            return {}

        result_map = {}
        is_intraday = interval != "1d"

        # 👑 FIX 2: Handle the yfinance single-ticker flat DataFrame quirk
        is_multi_index = isinstance(data.columns, pd.MultiIndex)

        for s in symbols:
            ticker_col = f"{s}{self.suffix}"

            # Safely extract the ticker's DataFrame
            if is_multi_index:
                if ticker_col in data.columns.levels[0]:
                    df_ticker = data[ticker_col].copy()
                else:
                    continue
            else:
                # If only 1 symbol was requested, 'data' is already the target DataFrame
                df_ticker = data.copy()

            df_ticker = df_ticker.dropna()
            if df_ticker.empty:
                continue

            # Extract Datetime from Index to a Column
            df_ticker = df_ticker.reset_index()

            time_col = None
            for col in ['Datetime', 'Date', 'index']:
                if col in df_ticker.columns:
                    time_col = col
                    break

            if time_col:
                # Guarantee datetime format
                df_ticker[time_col] = pd.to_datetime(df_ticker[time_col])

                # Modern Check: Fix Timezone mapping to standard IST
                if df_ticker[time_col].dt.tz is not None:
                    df_ticker[time_col] = df_ticker[time_col].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)

                # JSON-Safe Formatting based on timeframe (Required since we are returning list[dict])
                if is_intraday:
                    df_ticker[time_col] = df_ticker[time_col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    df_ticker.rename(columns={time_col: 'Datetime'}, inplace=True)
                else:
                    df_ticker[time_col] = df_ticker[time_col].dt.strftime('%Y-%m-%d')
                    df_ticker.rename(columns={time_col: 'Date'}, inplace=True)

            # Return clean JSON structure for independent modules (Original Architecture)
            result_map[s] = df_ticker.to_dict(orient="records")

        return result_map


class BulkDataFetcher_BKP:
    '''
    this is before handling single list stock in symbols list since yf.download will return single data frame
    '''
    def __init__(self):
        # Indian stocks need .NS suffix for Yahoo Finance
        self.suffix = ".NS"

    def fetch_bulk_history(self, symbols: List[str], interval: str = "1d", period: str = "3mo") -> Dict[
        str, list[dict]]:
        """
        Fetches data for multiple stocks in O(1) network call.
        Returns: A dictionary where key is symbol and value is its DataFrame.
        """
        # 1. DSA: List Comprehension to add suffix
        formatted_symbols = [f"{s}{self.suffix}" for s in symbols]

        print(f"📡 Downloading bulk data for {len(symbols)} assets...")

        # 2. Networking: O(1) call
        try:
            # data is Multi-Index DataFrame
            data = yf.download(
                tickers=formatted_symbols,
                period=period,
                interval=interval,
                group_by='ticker',
                threads=True,  # Multi-threading enabled
                progress=False
            )
        except Exception as e:
            print(f"❌ Bulk Download Error: {e}")
            return {}

        # 3. Data Transformation: Multi-index to Dict of DataFrames
        result_map = {}
        is_intraday = interval != "1d"
        for s in symbols:
            ticker_col = f"{s}{self.suffix}"
            if ticker_col in data:
                # 1. Flatten the MultiIndex to a normal 2D DataFrame
                df_ticker: pd.DataFrame = data[ticker_col].copy()
                df_ticker = df_ticker.dropna()
                if not df_ticker.empty:
                    # 2. Extract Datetime from Index to a Column
                    df_ticker = df_ticker.reset_index()

                    time_col = None
                    for col in ['Datetime', 'Date', 'index']:
                        if col in df_ticker.columns:
                            time_col = col
                            break
                    if time_col:
                        # 1. Pehle guarantee kar lo ki column strictly Datetime format mein ho
                        df_ticker[time_col] = pd.to_datetime(df_ticker[time_col])

                        # 2. Modern Check: Kya is column ke paas Timezone information hai?
                        if df_ticker[time_col].dt.tz is not None:
                            # Hai toh UTC se IST mein badlo, fir timezone hata do
                            df_ticker[time_col] = df_ticker[time_col].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)

                        # 3. JSON-Safe Formatting based on timeframe
                        if is_intraday:
                            df_ticker[time_col] = df_ticker[time_col].dt.strftime('%Y-%m-%d %H:%M:%S')
                            df_ticker.rename(columns={time_col: 'Datetime'}, inplace=True)
                        else:
                            df_ticker[time_col] = df_ticker[time_col].dt.strftime('%Y-%m-%d')
                            df_ticker.rename(columns={time_col: 'Date'}, inplace=True)

                # 5. Return clean structure for independent modules
                result_map[s] = df_ticker.to_dict(orient="records")

        return result_map


from enums import FNO_UNIVERSE
fetcher = BulkDataFetcher()
data = fetcher.fetch_bulk_history(["RELIANCE"])
print(data)