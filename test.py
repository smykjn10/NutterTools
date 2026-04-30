


from service_layer.data_fetcher import DataFetcher, BulkDataFetcher



# data_fetcher = DataFetcher().fetch_history_data("Reliance.NS",period="1mo",interval='30m')
# print(data_fetcher)
data_fetcher = BulkDataFetcher().fetch_bulk_history(symbols=["RELIANCE"],interval="30m")
print(data_fetcher)

# import yfinance as yf
#
# data = yf.Ticker("Reliance.NS")
# history_data = data.history(period="1mo",interval="30m")
# print()
