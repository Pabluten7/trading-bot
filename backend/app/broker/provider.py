"""
Broker provider abstraction.

The trading system depends on this interface instead of directly
depending on Alpaca or another broker implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.broker.models import (
    Account,
    Order,
    OrderSide,
    OrderType,
    Position,
)


class BrokerProvider(ABC):
    """Abstract interface for broker integrations."""

    @abstractmethod
    def get_account(self) -> Account:
        """Return normalized account information."""
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return all currently open positions."""
        raise NotImplementedError

    @abstractmethod
    def get_position(
        self,
        symbol: str,
    ) -> Position | None:
        """Return one open position, if it exists."""
        raise NotImplementedError

    @abstractmethod
    def submit_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
    ) -> Order:
        """Submit a normalized order."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(
        self,
        order_id: str,
    ) -> None:
        """Cancel an existing order."""
        raise NotImplementedError

    @abstractmethod
    def get_order(
        self,
        order_id: str,
    ) -> Order | None:
        """Return an order by ID."""
        raise NotImplementedError