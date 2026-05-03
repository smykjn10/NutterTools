from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseBroker(ABC):
    """
    Abstract Base Class for all Broker Integrations.
    Yeh class ek template hai. Har naya broker (Groww, Zerodha, etc.) isko follow karega.
    """

    @abstractmethod
    async def login(self) -> bool:
        """Authenticate and establish session with the broker."""
        pass

    @abstractmethod
    async def get_account_balance(self) -> float:
        """Fetch available margin/funds for trading."""
        pass

    @abstractmethod
    async def place_order(self, symbol: str, qty: int, order_type: str, price: float = 0.0) -> Dict[str, Any]:
        """
        Place a buy/sell order.
        order_type: 'BUY' or 'SELL'
        price: 0.0 means Market Order, otherwise Limit Order.
        """
        pass

    @abstractmethod
    async def get_positions(self) -> Dict[str, Any]:
        """Fetch currently open positions."""
        pass

    @abstractmethod
    async def get_ltp(self, symbol: str) -> float:
        """Get Last Traded Price for a specific instrument (especially for Options)."""
        pass