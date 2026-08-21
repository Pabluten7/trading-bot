"""
Market data domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    """
    Normalized OHLCV candle.

    Prices use Decimal to avoid unnecessary floating-point
    precision errors in trading calculations.
    """

    symbol: str
    timestamp: datetime

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: int

    adjusted: bool = True

    def __post_init__(self) -> None:
        """Validate candle consistency."""

        if not self.symbol:
            raise ValueError(
                "Candle symbol cannot be empty."
            )

        if self.volume < 0:
            raise ValueError(
                "Candle volume cannot be negative."
            )

        if self.high < self.low:
            raise ValueError(
                "Candle high cannot be lower than low."
            )

        if not (
            self.low <= self.open <= self.high
        ):
            raise ValueError(
                "Candle open must be between low and high."
            )

        if not (
            self.low <= self.close <= self.high
        ):
            raise ValueError(
                "Candle close must be between low and high."
            )