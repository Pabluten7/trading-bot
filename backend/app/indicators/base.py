"""
Base interfaces for technical indicators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from decimal import Decimal

from app.data.models import Candle
from app.indicators.models import IndicatorSeries


class Indicator(ABC):
    """
    Base class for all technical indicators.

    Indicators receive normalized candles and return normalized
    indicator series.
    """

    name: str

    @abstractmethod
    def calculate(
        self,
        candles: Sequence[Candle],
    ) -> IndicatorSeries:
        """Calculate the indicator."""

        raise NotImplementedError

    @staticmethod
    def _to_decimal(
        value: float | int | Decimal,
    ) -> Decimal:
        """Convert a numeric value safely to Decimal."""

        return Decimal(str(value))