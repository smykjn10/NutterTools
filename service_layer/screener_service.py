from .brokers.base_broker import BaseBroker
from .data_fetcher import BulkDataFetcher


class ScreenerService:
    def __init__(self, universe:list[str]):
        self._universe = universe

    async def get_daily_watchlist(self):

        pass

