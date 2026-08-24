"""
Risk management domain models.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskParameters:
    """Risk parameters used to calculate a position."""

    account_equity: float
    entry_price: float
    stop_price: float

    risk_per_trade_percent: float


@dataclass(frozen=True, slots=True)
class PositionSizing:
    """Calculated position sizing result."""

    entry_price: float
    stop_price: float

    risk_per_share: float
    risk_amount: float

    quantity: int
    position_value: float

    risk_percent: float