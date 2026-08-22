"""
Alpaca market-data provider.

Adapts Alpaca market data to the internal MarketDataProvider
abstraction used by the Trading Bot.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
)
from alpaca.data.timeframe import (
    TimeFrame,
    TimeFrameUnit,
)

from app.config.settings import settings
from app.data.models import Candle
from app.data.provider import MarketDataProvider


class AlpacaMarketDataProvider(MarketDataProvider):
    """
    Alpaca implementation of the market-data provider.

    This class is responsible only for retrieving and normalizing
    market data. Trading decisions are handled elsewhere.
    """

    def __init__(self) -> None:
        self._client: StockHistoricalDataClient | None = None

    @property
    def client(self) -> StockHistoricalDataClient:
        """Return the initialized Alpaca historical-data client."""

        if self._client is None:
            api_key = settings.broker.api_key
            secret_key = settings.broker.secret_key

            if not api_key or not secret_key:
                raise RuntimeError(
                    "Alpaca API credentials are not configured."
                )

            self._client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key,
            )

        return self._client

    def get_candles(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[Candle]]:
        """
        Return normalized 4-hour candles for the requested symbols.

        The internal trading configuration controls the intended
        candle timeframe. Currently the bot is designed around 4H
        candles.
        """

        if not symbols:
            return {}

        if start >= end:
            raise ValueError(
                "start must be earlier than end."
            )

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(
                amount=4,
                unit=TimeFrameUnit.Hour,
            ),
            start=start,
            end=end,
            adjustment=(
                "all"
                if settings.market_data.use_adjusted_data
                else "raw"
            ),
        )

        response = self.client.get_stock_bars(request)

        result: dict[str, list[Candle]] = {
            symbol: []
            for symbol in symbols
        }

        for symbol in symbols:
            bars = response.data.get(symbol, [])

            for bar in bars:
                result[symbol].append(
                    Candle(
                        symbol=symbol,
                        timestamp=bar.timestamp,
                        open=Decimal(str(bar.open)),
                        high=Decimal(str(bar.high)),
                        low=Decimal(str(bar.low)),
                        close=Decimal(str(bar.close)),
                        volume=int(bar.volume),
                        adjusted=settings.market_data.use_adjusted_data,
                    )
                )

        return result

    def get_latest_candle(
        self,
        symbol: str,
    ) -> Candle | None:
        """
        Return the latest available 4-hour candle for a symbol.
        """

        if not symbol:
            raise ValueError(
                "symbol cannot be empty."
            )

        now = datetime.now().astimezone()

        start = now - timedelta(days=3)

        candles = self.get_candles(
            symbols=[symbol],
            start=start,
            end=now,
        )

        symbol_candles = candles.get(symbol, [])

        if not symbol_candles:
            return None

        return symbol_candles[-1]


alpaca_market_data_provider = (
    AlpacaMarketDataProvider()
)