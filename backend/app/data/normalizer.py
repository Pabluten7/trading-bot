"""
Market data normalization.

Converts provider-specific market data into the internal Candle model.
"""

from __future__ import annotations

from datetime import datetime

from app.data.exceptions import InvalidMarketDataError
from app.data.models import Candle


def normalize_candle(
    *,
    symbol: str,
    timestamp: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    timeframe: str = "4Hour",
) -> Candle:
    """
    Normalize raw OHLCV values into a Candle.

    Validation is intentionally performed at this boundary so the
    rest of the application can assume that Candle objects are valid.
    """

    if not symbol:
        raise InvalidMarketDataError(
            "Market symbol cannot be empty."
        )

    if high < low:
        raise InvalidMarketDataError(
            "Candle high cannot be lower than candle low."
        )

    if open_price < low or open_price > high:
        raise InvalidMarketDataError(
            "Candle open must be inside the high/low range."
        )

    if close < low or close > high:
        raise InvalidMarketDataError(
            "Candle close must be inside the high/low range."
        )

    if volume < 0:
        raise InvalidMarketDataError(
            "Candle volume cannot be negative."
        )

    return Candle(
        symbol=symbol.upper(),
        timestamp=timestamp,
        open=float(open_price),
        high=float(high),
        low=float(low),
        close=float(close),
        volume=float(volume),
        timeframe=timeframe,
    )