"""
Development market-data provider.

Provides deterministic synthetic market data for local development
when no external market-data provider is configured.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.data.models import Candle
from app.data.provider import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """
    Synthetic market-data provider for development.

    The generated candles are deterministic and are intended only for
    development of scanners, indicators, strategy and risk components.
    They must never be used for live trading.
    """

    def get_candles(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[Candle]]:
        """Generate synthetic 4-hour candles."""

        if start >= end:
            raise ValueError(
                "Market-data start time must be before end time."
            )

        normalized_symbols = [
            symbol.strip().upper()
            for symbol in symbols
            if symbol.strip()
        ]

        result: dict[str, list[Candle]] = {
            symbol: []
            for symbol in normalized_symbols
        }

        for symbol_index, symbol in enumerate(
            normalized_symbols,
            start=1,
        ):
            candles: list[Candle] = []

            timestamp = start

            base_price = Decimal(
                100 + (symbol_index * 25)
            )

            index = 0

            while timestamp < end:
                movement = Decimal(
                    (index % 7) - 3
                )

                open_price = (
                    base_price
                    + Decimal(index)
                    + movement
                )

                close_price = (
                    open_price
                    + Decimal("1.50")
                )

                high_price = (
                    close_price
                    + Decimal("0.75")
                )

                low_price = (
                    open_price
                    - Decimal("0.75")
                )

                volume = (
                    1_000_000
                    + (index * 10_000)
                    + (symbol_index * 100_000)
                )

                candles.append(
                    Candle(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        adjusted=True,
                    )
                )

                timestamp += timedelta(hours=4)
                index += 1

            result[symbol] = candles

        return result

    def get_latest_candle(
        self,
        symbol: str,
    ) -> Candle | None:
        """Generate a single latest synthetic candle."""

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        now = datetime.now(timezone.utc)

        return Candle(
            symbol=normalized_symbol,
            timestamp=now,
            open=Decimal("100.00"),
            high=Decimal("102.00"),
            low=Decimal("99.00"),
            close=Decimal("101.50"),
            volume=1_000_000,
            adjusted=True,
        )