"""
Scanner eligibility filters.
"""

from __future__ import annotations

from app.indicators.calculator import IndicatorSnapshot


def passes_trend_filter(
    indicators: IndicatorSnapshot,
) -> bool:
    """
    Require a bullish long-term trend structure.

    EMA20 > EMA50 > EMA200
    """

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


def passes_momentum_filter(
    indicators: IndicatorSnapshot,
) -> bool:
    """
    Require acceptable momentum.

    RSI must be available and remain in a non-extreme range.
    """

    if indicators.rsi14 is None:
        return False

    return 45.0 <= indicators.rsi14 <= 75.0


def passes_volatility_filter(
    indicators: IndicatorSnapshot,
    price: float,
) -> bool:
    """
    Require usable volatility information.
    """

    if indicators.atr14 is None:
        return False

    if price <= 0:
        return False

    atr_percentage = (
        indicators.atr14 / price
    ) * 100.0

    return 0.5 <= atr_percentage <= 7.0


def is_eligible(
    indicators: IndicatorSnapshot,
    price: float,
) -> bool:
    """
    Determine whether a symbol can become a scan candidate.
    """

    return (
        passes_trend_filter(indicators)
        and passes_momentum_filter(indicators)
        and passes_volatility_filter(
            indicators,
            price,
        )
    )