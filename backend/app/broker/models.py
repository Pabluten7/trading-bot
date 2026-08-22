"""
Broker domain models.

Defines normalized broker-side models used by the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class OrderSide(StrEnum):
    """Supported order directions."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Supported order types."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(StrEnum):
    """Normalized order states."""

    NEW = "new"
    ACCEPTED = "accepted"
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Position:
    """Normalized open position."""

    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True, slots=True)
class Account:
    """Normalized trading account information."""

    account_id: str
    buying_power: Decimal
    cash: Decimal
    portfolio_value: Decimal
    equity: Decimal


@dataclass(frozen=True, slots=True)
class Order:
    """Normalized broker order."""

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    status: OrderStatus

    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None