"""
Market data service.

Coordinates access to the configured market-data provider and exposes
a stable interface to the rest of the Trading Bot.
"""

from __future__ import annotations

from datetime import datetime

from app.data.models import Candle
from app.data.provider import MarketDataProvider


class MarketDataService:
    """
    Application-level market-data service.

    Business logic should depend on this service rather than directly
    accessing an external market-data provider.
    """

    def __init__(
        self,
        provider: MarketDataProvider | None = None,
    ) -> None:
        self._provider = provider

    @property
    def provider(
        self,
    ) -> MarketDataProvider | None:
        """Return the configured market-data provider."""

        return self._provider

    def configure_provider(
        self,
        provider: MarketDataProvider | None,
    ) -> None:
        """Configure the market-data provider."""

        self._provider = provider

    def is_configured(self) -> bool:
        """Return whether a provider is configured."""

        return self._provider is not None

    def get_candles(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[Candle]]:
        """Retrieve normalized candles."""

        provider = self._require_provider()

        return provider.get_candles(
            symbols=symbols,
            start=start,
            end=end,
        )

    def get_latest_candle(
        self,
        symbol: str,
    ) -> Candle | None:
        """Retrieve the latest candle for a symbol."""

        provider = self._require_provider()

        return provider.get_latest_candle(
            symbol=symbol,
        )

    def _require_provider(
        self,
    ) -> MarketDataProvider:
        """Return the provider or raise when unavailable."""

        if self._provider is None:
            raise RuntimeError(
                "Market-data provider is not configured."
            )

        return self._provider


market_data_service = MarketDataService()