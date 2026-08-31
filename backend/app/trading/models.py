"""
Trading execution domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from decimal import Decimal

from app.broker.models import Order


class TradeDecision(StrEnum):
    """Possible decisions produced by the trading engine."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class TradeResult:
    """Result of a trading-engine evaluation."""

    symbol: str
    decision: TradeDecision
    reason: str
    quantity: Decimal = Decimal("0")
    order: Order | None = None