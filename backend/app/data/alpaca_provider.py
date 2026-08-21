"""
Alpaca market-data provider.

Implements the internal MarketDataProvider abstraction using Alpaca's
historical stock market-data API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import Adjustment

from app.config.settings import settings
from app.data.models import Candle
from app.data.provider import MarketDataProvider


class AlpacaMarketDataProvider(MarketDataProvider):
    """
    Market-data provider backed by Alpaca.

    The rest of the application should interact with this class only
    through the MarketDataProvider interface.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """
        Initialize the Alpaca market-data client.

        If credentials are not explicitly provided, they are obtained
        from application settings.
        """

        resolved_api_key = (
            api_key
            if api_key is not None
            else settings.broker.api_key
        )

        resolved_secret_key = (
            secret_key
            if secret_key is not None
            else settings.broker.secret_key
        )

        if not resolved_api_key:
            raise ValueError(
                "Alpaca API key is not configured."
            )

        if not resolved_secret_key:
            raise ValueError(
                "Alpaca secret key is not configured."
            )

        self._client = StockHistoricalDataClient(
            api_key=resolved_api_key,
            secret_key=resolved_secret_key,
        )

        self._timeframe = TimeFrame(
            4,
            TimeFrameUnit.Hour,
        )

    @staticmethod
    def _normalize_timestamp(
        timestamp: datetime,
    ) -> datetime:
        """
        Normalize timestamps to timezone-aware UTC datetimes.
        """

        if timestamp.tzinfo is None:
            return timestamp.replace(
                tzinfo=timezone.utc
            )

        return timestamp.astimezone(timezone.utc)

    @staticmethod
    def _to_candle(
        symbol: str,
        bar: object,
    ) -> Candle:
        """
        Convert an Alpaca bar into the internal Candle model.
        """

        timestamp = AlpacaMarketDataProvider._normalize_timestamp(
            bar.timestamp
        )

        return Candle(
            symbol=symbol,
            timestamp=timestamp,
            open=Decimal(str(bar.open)),
            high=Decimal(str(bar.high)),
            low=Decimal(str(bar.low)),
            close=Decimal(str(bar.close)),
            volume=int(bar.volume),
            adjusted=True,
        )

    def get_candles(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[Candle]]:
        """
        Retrieve 4-hour candles for multiple symbols.

        Results are returned grouped by symbol.
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

        if start >= end:
            raise ValueError(
                "Market-data start time must be before end time."
            )

        request = StockBarsRequest(
            symbol_or_symbols=normalized_symbols,
            timeframe=self._timeframe,
            start=start,
            end=end,
            adjustment=Adjustment.ALL,
        )

        response = self._client.get_stock_bars(
            request
        )

        result: dict[str, list[Candle]] = {
            symbol: []
            for symbol in normalized_symbols
        }

        for symbol in normalized_symbols:
            try:
                bars = response[symbol]
            except KeyError:
                continue

            result[symbol] = [
                self._to_candle(
                    symbol=symbol,
                    bar=bar,
                )
                for bar in bars
            ]

        return result

    def get_latest_candle(
        self,
        symbol: str,
    ) -> Candle | None:
        """
        Retrieve the most recent 4-hour candle for a symbol.
        """

        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        request = StockBarsRequest(
            symbol_or_symbols=[normalized_symbol],
            timeframe=self._timeframe,
            limit=1,
            adjustment=Adjustment.ALL,
        )

        response = self._client.get_stock_bars(
            request
        )

        try:
            bars = response[normalized_symbol]
        except KeyError:
            return None

        if not bars:
            return None

        return self._to_candle(
            symbol=normalized_symbol,
            bar=bars[-1],
        )


alpaca_market_data_provider = (
    AlpacaMarketDataProvider
    if settings.broker.api_key
    and settings.broker.secret_key
    else None
)