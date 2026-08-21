"""
Indicator result models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class IndicatorValue:
    """Single calculated indicator value."""

    name: str
    timestamp: datetime
    value: Decimal


@dataclass(frozen=True, slots=True)
class IndicatorSeries:
    """Time series containing calculated indicator values."""

    name: str
    values: tuple[IndicatorValue, ...]

    @property
    def latest(self) -> IndicatorValue | None:
        """Return the latest indicator value."""

        if not self.values:
            return None

        return self.values[-1]