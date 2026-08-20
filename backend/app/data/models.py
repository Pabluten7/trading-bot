"""
Market data models.

Defines the normalized internal representation of market data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    """
    Represents one OHLCV market candle.

    All market-data providers must be converted into this format
    before being consumed by the rest of the application.
    """

    symbol: str
    timestamp: datetime

    open: float
    high: float
    low: float
    close: float

    volume: float

    timeframe: str = "4Hour"

    @property
    def is_bullish(self) -> bool:
        """Return whether the candle closed above its open."""

        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Return whether the candle closed below its open."""

        return self.close < self.open

    @property
    def body_size(self) -> float:
        """Return the absolute candle body size."""

        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        """Return the complete candle price range."""

        return self.high - self.low