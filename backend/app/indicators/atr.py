"""
Average True Range (ATR).
"""

from __future__ import annotations

from app.data.models import Candle


def atr(
    candles: list[Candle],
    period: int = 14,
) -> list[float | None]:
    """
    Calculate the Average True Range.

    Uses Wilder's smoothing method.

    Parameters
    ----------
    candles:
        Ordered candles, oldest first.

    period:
        ATR calculation period.

    Returns
    -------
    list[float | None]
        ATR values aligned with the candle list.
    """

    if period <= 0:
        raise ValueError("ATR period must be greater than zero.")

    if not candles:
        return []

    if len(candles) <= period:
        return [None] * len(candles)

    true_ranges: list[float] = [
        0.0
    ] * len(candles)

    true_ranges[0] = (
        candles[0].high - candles[0].low
    )

    for index in range(1, len(candles)):
        candle = candles[index]
        previous_close = candles[index - 1].close

        true_ranges[index] = max(
            candle.high - candle.low,
            abs(candle.high - previous_close),
            abs(candle.low - previous_close),
        )

    result: list[float | None] = [None] * len(candles)

    initial_atr = sum(
        true_ranges[1:period + 1]
    ) / period

    result[period] = initial_atr

    previous_atr = initial_atr

    for index in range(period + 1, len(candles)):
        current_atr = (
            (
                previous_atr * (period - 1)
            )
            + true_ranges[index]
        ) / period

        result[index] = current_atr
        previous_atr = current_atr

    return result