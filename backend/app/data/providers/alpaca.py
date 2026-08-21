"""
Alpaca market-data provider.

Converts Alpaca market-data responses into the internal Candle model.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from app.config.settings import settings
from app.data.models import Candle
from app.data.provider import MarketDataProvider


class AlpacaMarketDataProvider(MarketDataProvider):
    """
    Market-data provider backed by Alpaca.

    This class is responsible only for retrieving and normalizing
    market data. Trading decisions remain outside the provider.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self._api_key = (
            api_key
            if api_key is not None
            else settings.broker.api_key
        )

        self._secret_key = (
            secret_key
            if secret_key is not None
            else settings.broker.secret_key
        )

        self._client: StockHistoricalDataClient | None = None

    @property
    def client(self) -> StockHistoricalDataClient:
        """Return the initialized Alpaca client."""

        if self._client is None:
            if not self._api_key or not self._secret_key:
                raise RuntimeError(
                    "Alpaca API credentials are not configured."
                )

            self._client = StockHistoricalDataClient(
                self._api_key,
                self._secret_key,
            )

        return self._client

    @staticmethod
    def _parse_timeframe(
        timeframe: str,
    ) -> TimeFrame:
        """
        Convert the internal timeframe representation into Alpaca's
        TimeFrame representation.
        """

        normalized = timeframe.strip().lower()

        if normalized in {"4h", "4hour", "4hours"}:
            return TimeFrame(
                4,
                TimeFrameUnit.Hour,
            )

        if normalized in {"1h", "1hour", "1hours"}:
            return TimeFrame(
                1,
                TimeFrameUnit.Hour,
            )

        if normalized in {"1d", "1day", "1days"}:
            return TimeFrame(
                1,
                TimeFrameUnit.Day,
            )

        if normalized in {"1w", "1week", "1weeks"}:
            return TimeFrame(
                1,
                TimeFrameUnit.Week,
            )

        raise ValueError(
            f"Unsupported market-data timeframe: {timeframe}"
        )

    async def get_candles(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list[Candle]:
        """Retrieve and normalize historical candles."""

        if not symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        if start >= end:
            raise ValueError(
                "Start datetime must be before end datetime."
            )

        alpaca_timeframe = self._parse_timeframe(
            timeframe
        )

        request = StockBarsRequest(
            symbol_or_symbols=symbol.upper(),
            timeframe=alpaca_timeframe,
            start=start,
            end=end,
            adjustment="all"
            if settings.market_data.use_adjusted_data
            else "raw",
        )

        response = self.client.get_stock_bars(
            request
        )

        bars = response[symbol.upper()]

        candles: list[Candle] = []

        for bar in bars:
            candles.append(
                Candle(
                    symbol=symbol.upper(),
                    timestamp=bar.timestamp,
                    open=Decimal(str(bar.open)),
                    high=Decimal(str(bar.high)),
                    low=Decimal(str(bar.low)),
                    close=Decimal(str(bar.close)),
                    volume=int(bar.volume),
                    adjusted=settings.market_data.use_adjusted_data,
                )
            )

        return candles

    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
    ) -> Candle | None:
        """Return the latest available candle."""

        from datetime import timedelta, timezone

        now = datetime.now(timezone.utc)

        if timeframe.lower() in {
            "4h",
            "4hour",
            "4hours",
        }:
            lookback = timedelta(days=5)
        elif timeframe.lower() in {
            "1d",
            "1day",
            "1days",
        }:
            lookback = timedelta(days=10)
        else:
            lookback = timedelta(days=2)

        candles = await self.get_candles(
            symbol=symbol,
            start=now - lookback,
            end=now,
            timeframe=timeframe,
        )

        if not candles:
            return None

        return candles[-1]