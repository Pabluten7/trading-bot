"""
Exponential Moving Average (EMA).
"""

from __future__ import annotations


def ema(
    values: list[float],
    period: int,
) -> list[float | None]:
    """
    Calculate the Exponential Moving Average.

    Parameters
    ----------
    values:
        Ordered price values, oldest first.

    period:
        Number of observations used by the EMA.

    Returns
    -------
    list[float | None]
        EMA values aligned with the input list.

        Positions before enough data exists contain None.
    """

    if period <= 0:
        raise ValueError("EMA period must be greater than zero.")

    if not values:
        return []

    result: list[float | None] = [None] * len(values)

    if len(values) < period:
        return result

    initial_average = sum(
        values[:period]
    ) / period

    result[period - 1] = initial_average

    multiplier = 2 / (period + 1)

    previous = initial_average

    for index in range(period, len(values)):
        current = values[index]

        current_ema = (
            (current - previous) * multiplier
        ) + previous

        result[index] = current_ema
        previous = current_ema

    return result