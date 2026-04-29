from .brokers.base_broker import BaseBroker



class ScreenerService:
    def __init__(self, broker:BaseBroker):
        self._broker