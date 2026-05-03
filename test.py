


from service_layer.data_fetcher import DataFetcher, BulkDataFetcher
from service_layer.analytics import  AnalyticsEngine
from enums import FNO_UNIVERSE


# # data_fetcher = DataFetcher().fetch_history_data("Reliance.NS",period="1mo",interval='30m')
# # print(data_fetcher)
data_fetcher = BulkDataFetcher()
analytics = AnalyticsEngine()
# .fetch_bulk_history(symbols=["RELIANCE"],interval="30m")

# print(data_fetcher)
#
# # import yfinance as yf
# #
# # data = yf.Ticker("Reliance.NS")
# # history_data = data.history(period="1mo",interval="30m")
# # print()
import asyncio
from service_layer.screener_service import ScreenerService
screener = ScreenerService(data_fetcher,analytics)
watchlist = asyncio.run(screener.get_daily_watchlist())
print(watchlist)












