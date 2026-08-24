"""
Strategy domain models.

Contains the normalized market state consumed by the strategy engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.indicators.calculator import IndicatorSnapshot


class MarketDirection(StrEnum):
    """Detected market direction."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """
    Market information required by the strategy.

    This object deliberately contains no broker or portfolio state.
    """

    symbol: str
    close: float
    indicators: IndicatorSnapshot

    market_direction: MarketDirection = MarketDirection.NEUTRAL