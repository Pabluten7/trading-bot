"""
Strategy data models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.scanner.models import ScanCandidate


class SignalDirection(StrEnum):
    """Possible trading signal directions."""

    LONG = "long"


class SignalStrength(StrEnum):
    """Strength of an entry signal."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass(frozen=True)
class EntrySignal:
    """
    Represents a strategy-generated entry signal.

    A signal is only a proposal. It does not execute an order.
    """

    symbol: str
    direction: SignalDirection

    strength: SignalStrength

    score: float
    price: float

    reason: str

    candidate: ScanCandidate