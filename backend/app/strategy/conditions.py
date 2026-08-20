"""
Entry conditions for the trading strategy.
"""

from __future__ import annotations

from app.scanner.models import ScanCandidate


def has_bullish_trend(
    candidate: ScanCandidate,
) -> bool:
    """
    Check that the candidate maintains bullish EMA alignment.
    """

    indicators = candidate.indicators

    if (
        indicators.ema20 is None
        or indicators.ema50 is None
        or indicators.ema200 is None
    ):
        return False

    return (
        indicators.ema20 > indicators.ema50
        and indicators.ema50 > indicators.ema200
    )


def has_acceptable_momentum(
    candidate: ScanCandidate,
) -> bool:
    """
    Check whether momentum is suitable for a long entry.

    The strategy avoids entering when RSI is excessively extended.
    """

    rsi_value = candidate.indicators.rsi14

    if rsi_value is None:
        return False

    return 50.0 <= rsi_value <= 70.0


def has_usable_volatility(
    candidate: ScanCandidate,
) -> bool:
    """
    Check that ATR provides sufficient price movement information.
    """

    atr_value = candidate.indicators.atr14

    if atr_value is None:
        return False

    if candidate.price <= 0:
        return False

    atr_percentage = (
        atr_value / candidate.price
    ) * 100.0

    return 0.5 <= atr_percentage <= 7.0


def meets_entry_conditions(
    candidate: ScanCandidate,
) -> bool:
    """
    Determine whether all mandatory strategy conditions are met.
    """

    return (
        has_bullish_trend(candidate)
        and has_acceptable_momentum(candidate)
        and has_usable_volatility(candidate)
    )