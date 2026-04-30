from abc import ABC, abstractmethod
from typing import Any

class BaseBroker(ABC):
    """
        The Master Blueprint. Every new broker we add MUST implement these methods.
    """

    @abstractmethod
    def login(self) -> bool:
        pass

    @abstractmethod
    def get_live_price(self, asset: str) -> float:
        pass

    @abstractmethod
    def place_order(self, action: str, asset: str, quantity: int, sl_price: float) -> dict[str, Any]:
        """Should return order details like order_id, status"""
        pass

    @abstractmethod
    def get_positions(self) -> list:
        pass