from service_layer.data_fetcher import BulkDataFetcher
from service_layer.analytics_engine import AnalyticsEngine
from service_layer.setups import TTMSqueezeSetup, InstitutionalBreakoutSetup, PullbackBounceSetup, CoilNR4Setup

# # data_fetcher = DataFetcher().fetch_history_data("Reliance.NS",period="1mo",interval='30m')
# # print(data_fetcher)
data_fetcher = BulkDataFetcher()
analytics = AnalyticsEngine(
    strategies=[PullbackBounceSetup()]
)
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

screener = ScreenerService(data_fetcher, analytics)
watchlist = asyncio.run(screener.generate_watchlist(None))
print(watchlist)


#
# import asyncio
# import time
#
#
# async def task(name, delay):
#     print("second")
#     print(f"{name} started at {time.time():.2f}")
#     await asyncio.sleep(delay)
#     print(f"{name} finished at {time.time():.2f}")
#
#
#
# async def main():
#     print("first")
#     start = time.time()
#     await asyncio.gather(
#         task("A", 3),
#         task("B", 3),
#         task("C", 3)
#     )
#
#     print(f"Total time: {time.time() - start:.2f}s")
#
#
# asyncio.run(main())
# #



#
#
# async def foo():
#     return 42
#
#
#
#
# coro = foo()
#
# print(coro)
#
#
#
# def foo():
#     print("A")
#     yield "pause here"
#     print("B")
#
# print(foo())
#
# for i in foo():
#     print(i, type(i))
#     print(type(i))
#
#












