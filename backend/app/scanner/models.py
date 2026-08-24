"""
Scanner domain models.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.data.models import Candle
from app.indicators.calculator import IndicatorSnapshot


@dataclass(frozen=True, slots=True)
class ScanCandidate:
    """
    Represents a stock candidate produced by the scanner.

    A candidate contains market information and its calculated
    indicators, but it does not represent a trading order.
    """

    symbol: str
    price: float

    indicators: IndicatorSnapshot

    score: float
    eligible: bool

    candle: Candle