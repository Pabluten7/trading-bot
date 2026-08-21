"""
Market data domain models and provider abstraction.

This module defines the normalized market-data structures used by the
trading engine. Concrete providers are implemented separately.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    """
    Normalized OHLCV candle.

    All prices are represented as Decimal to avoid introducing
    unnecessary floating-point errors into trading calculations.
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
        """Validate the candle."""

        if not self.symbol:
            raise ValueError("Candle symbol cannot be empty.")

        if self.volume < 0:
            raise ValueError("Candle volume cannot be negative.")

        if self.high < self.low:
            raise ValueError(
                "Candle high cannot be lower than low."
            )

        if self.open < self.low or self.open > self.high:
            raise ValueError(
                "Candle open must be between low and high."
            )

        if self.close < self.low or self.close > self.high:
            raise ValueError(
                "Candle close must be between low and high."
            )


class MarketDataProvider(ABC):
    """
    Provider-independent market-data interface.

    Broker/provider-specific implementations must conform to this
    interface before data reaches the trading engine.
    """

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Candle]:
        """
        Retrieve normalized candles for a symbol.

        Parameters
        ----------
        symbol:
            Trading symbol, e.g. ``AAPL``.
        start:
            Beginning of the requested period.
        end:
            End of the requested period.
        timeframe:
            Candle timeframe, e.g. ``4Hour``.
        """

        raise NotImplementedError

    @abstractmethod
    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
    ) -> Candle | None:
        """Return the latest available candle."""

        raise NotImplementedError