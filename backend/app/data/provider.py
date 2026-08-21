"""
Market data provider abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.data.models import Candle


class MarketDataProvider(ABC):
    """
    Provider-independent market-data interface.

    External providers must implement this interface before their
    data enters the trading engine.
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
        """

        raise NotImplementedError

    @abstractmethod
    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
    ) -> Candle | None:
        """
        Return the latest available candle.
        """

        raise NotImplementedError