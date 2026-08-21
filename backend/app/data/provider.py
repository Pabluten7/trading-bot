"""
Market data provider abstraction.

Defines the interface that external market-data providers must
implement. The rest of the application works against this abstraction
instead of depending directly on Alpaca or another provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.data.models import Candle


class MarketDataProvider(ABC):
    """
    Abstract interface for market-data providers.

    External providers such as Alpaca will implement this interface.
    """

    @abstractmethod
    def get_candles(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[Candle]]:
        """
        Return normalized candles for the requested symbols.

        Parameters
        ----------
        symbols:
            List of stock symbols.

        start:
            Start of the requested period.

        end:
            End of the requested period.

        Returns
        -------
        dict[str, list[Candle]]
            Candles grouped by symbol.
        """
        raise NotImplementedError

    @abstractmethod
    def get_latest_candle(
        self,
        symbol: str,
    ) -> Candle | None:
        """
        Return the latest available candle for a symbol.

        Returns ``None`` when no candle is available.
        """
        raise NotImplementedError