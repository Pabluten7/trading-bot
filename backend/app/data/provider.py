"""
Market data provider abstraction.

External market-data providers must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.data.models import Candle


class MarketDataProvider(ABC):
    """
    Abstract market-data provider.

    This abstraction keeps the trading system independent from
    the external market-data vendor.
    """

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "4Hour",
    ) -> list[Candle]:
        """
        Return historical candles for a symbol.

        Parameters
        ----------
        symbol:
            Market symbol, for example ``AAPL``.

        start:
            Beginning of the requested period.

        end:
            End of the requested period.

        timeframe:
            Candle timeframe. The project currently uses 4-hour candles.
        """

        raise NotImplementedError

    @abstractmethod
    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str = "4Hour",
    ) -> Candle | None:
        """Return the latest available candle for a symbol."""

        raise NotImplementedError