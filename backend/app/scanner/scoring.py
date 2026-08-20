"""
Scanner scoring logic.
"""

from __future__ import annotations

from app.indicators.calculator import IndicatorSnapshot


def calculate_trend_score(
    indicators: IndicatorSnapshot,
) -> float:
    """
    Calculate the trend component of the scanner score.

    The score rewards bullish EMA alignment:

        EMA20 > EMA50 > EMA200

    The score is normalized between 0 and 100.
    """

    if (
        indicators.ema20 is None
        or indicators.ema50 is None
        or indicators.ema200 is None
    ):
        return 0.0

    score = 0.0

    if indicators.ema20 > indicators.ema50:
        score += 50.0

    if indicators.ema50 > indicators.ema200:
        score += 50.0

    return score


def calculate_momentum_score(
    indicators: IndicatorSnapshot,
) -> float:
    """
    Calculate the momentum component.

    RSI is used as a momentum filter rather than an independent
    buy signal.

    The preferred zone is between 50 and 70.
    """

    if indicators.rsi14 is None:
        return 0.0

    value = indicators.rsi14

    if 50.0 <= value <= 70.0:
        return 100.0

    if 45.0 <= value < 50.0:
        return 50.0

    if 70.0 < value <= 75.0:
        return 50.0

    return 0.0


def calculate_volatility_score(
    indicators: IndicatorSnapshot,
    price: float,
) -> float:
    """
    Calculate the volatility component.

    ATR is currently used as a basic measure of price movement.

    The score remains neutral when insufficient information is
    available.
    """

    if (
        indicators.atr14 is None
        or price <= 0
    ):
        return 0.0

    atr_percentage = (
        indicators.atr14 / price
    ) * 100.0

    # Avoid rewarding extremely low or extremely high volatility.
    if 1.0 <= atr_percentage <= 5.0:
        return 100.0

    if 0.5 <= atr_percentage < 1.0:
        return 50.0

    if 5.0 < atr_percentage <= 7.0:
        return 50.0

    return 0.0


def calculate_total_score(
    indicators: IndicatorSnapshot,
    price: float,
) -> tuple[
    float,
    float,
    float,
    float,
]:
    """
    Calculate the complete scanner score.

    Returns
    -------
    tuple
        total score,
        trend score,
        momentum score,
        volatility score.
    """

    trend_score = calculate_trend_score(
        indicators
    )

    momentum_score = calculate_momentum_score(
        indicators
    )

    volatility_score = calculate_volatility_score(
        indicators,
        price,
    )

    total_score = (
        trend_score * 0.50
        + momentum_score * 0.30
        + volatility_score * 0.20
    )

    return (
        total_score,
        trend_score,
        momentum_score,
        volatility_score,
    )