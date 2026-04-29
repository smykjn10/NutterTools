import yfinance as yf
import pandas as pd


class DataFetcher:

    def fetch_history_data(self, asset: str, period: str = "1mo", interval: str = "1d"):
        try:
            stock = yf.Ticker(asset)
            stock_history = stock.history(period=period)
            stock_history = stock_history.reset_index()
            if stock_history.empty:
                return []
            stock_history['Date'] = stock_history['Date'].dt.strftime('%Y-%m-%d')
            return stock_history.to_dict(orient="records")
        except Exception as e:
            print(str(e))
            raise


# data_fetcher = DataFetcher()
# data = data_fetcher.fetch_history_data("smayak")
# print(data)
