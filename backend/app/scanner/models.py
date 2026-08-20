"""
Scanner data models.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.indicators.calculator import IndicatorSnapshot


@dataclass(frozen=True)
class ScanCandidate:
    """
    Represents a stock that passed the scanner filters.
    """

    symbol: str
    sector: str
    price: float

    indicators: IndicatorSnapshot

    score: float

    trend_score: float
    momentum_score: float
    volatility_score: float

    eligible: bool = True


@dataclass(frozen=True)
class ScanResult:
    """
    Result returned by the market scanner.
    """

    candidates: list[ScanCandidate]

    scanned_symbols: int
    eligible_symbols: int

    maximum_candidates: int = 8