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
            stock_history = stock.history(period=period,interval=interval)
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
        # Indian stocks need .NS suffix for Yahoo Finance
        self.suffix = ".NS"

    def fetch_bulk_history(self, symbols: List[str], period: str = "1mo", interval: str = "1d") -> Dict[
        str, pd.DataFrame]:
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
        for s in symbols:
            ticker_name = f"{s}{self.suffix}"
            if ticker_name in data:
                # Cleaning the data (Removing NaNs)
                df_ticker = data[ticker_name].dropna()
                result_map[s] = df_ticker

        return result_map

# data_fetcher = DataFetcher()
# data = data_fetcher.fetch_history_data("smayak")
# print(data)
