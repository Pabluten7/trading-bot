"""
Relative Strength Index (RSI).
"""

from __future__ import annotations


def rsi(
    values: list[float],
    period: int = 14,
) -> list[float | None]:
    """
    Calculate the Relative Strength Index.

    Uses Wilder's smoothing method.

    Parameters
    ----------
    values:
        Ordered closing prices, oldest first.

    period:
        RSI calculation period.

    Returns
    -------
    list[float | None]
        RSI values aligned with the input list.
    """

    if period <= 0:
        raise ValueError("RSI period must be greater than zero.")

    if len(values) <= period:
        return [None] * len(values)

    result: list[float | None] = [None] * len(values)

    gains: list[float] = []
    losses: list[float] = []

    for index in range(1, len(values)):
        change = values[index] - values[index - 1]

        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    average_gain = sum(
        gains[:period]
    ) / period

    average_loss = sum(
        losses[:period]
    ) / period

    result[period] = _calculate_rsi(
        average_gain,
        average_loss,
    )

    for index in range(period, len(gains)):
        average_gain = (
            (average_gain * (period - 1))
            + gains[index]
        ) / period

        average_loss = (
            (average_loss * (period - 1))
            + losses[index]
        ) / period

        result[index + 1] = _calculate_rsi(
            average_gain,
            average_loss,
        )

    return result


def _calculate_rsi(
    average_gain: float,
    average_loss: float,
) -> float:
    """Convert average gains/losses into an RSI value."""

    if average_loss == 0:
        return 100.0

    relative_strength = (
        average_gain / average_loss
    )

    return 100.0 - (
        100.0 / (1.0 + relative_strength)
    )