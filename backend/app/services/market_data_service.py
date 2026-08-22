"""
Market data service.

Provides a single application-level interface for retrieving
normalized market data.
"""

from __future__ import annotations

from datetime import datetime

from app.data import (
    Candle,
    MarketDataProvider,
    alpaca_market_data_provider,
)


class MarketDataService:
    """
    Application service for market data.

    Business logic should depend on this service rather than directly
    on an external market-data provider.
    """

    def __init__(
        self,
        provider: MarketDataProvider = alpaca_market_data_provider,
    ) -> None:
        self._provider = provider

    @property
    def provider(self) -> MarketDataProvider:
        """Return the configured market-data provider."""
        return self._provider

    def get_candles(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[Candle]]:
        """
        Retrieve candles for multiple symbols.
        """

        if not symbols:
            return {}

        normalized_symbols = [
            symbol.strip().upper()
            for symbol in symbols
            if symbol.strip()
        ]

        if not normalized_symbols:
            return {}

        return self._provider.get_candles(
            symbols=normalized_symbols,
            start=start,
            end=end,
        )

    def get_latest_candle(
        self,
        symbol: str,
    ) -> Candle | None:
        """Retrieve the latest candle for a symbol."""

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError(
                "symbol cannot be empty."
            )

        return self._provider.get_latest_candle(
            normalized_symbol,
        )


market_data_service = MarketDataService()