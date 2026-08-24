"""
Scanner eligibility filters.
"""

from __future__ import annotations

from app.scanner.models import ScanCandidate


def has_valid_price(
    candidate: ScanCandidate,
) -> bool:
    """Return whether the candidate has a valid market price."""

    return candidate.price > 0


def has_required_indicators(
    candidate: ScanCandidate,
) -> bool:
    """Return whether all required indicators are available."""

    indicators = candidate.indicators

    return (
        indicators.ema20 is not None
        and indicators.ema50 is not None
        and indicators.ema200 is not None
        and indicators.rsi14 is not None
        and indicators.atr14 is not None
    )


def has_bullish_ema_alignment(
    candidate: ScanCandidate,
) -> bool:
    """Return whether the EMAs are aligned bullishly."""

    indicators = candidate.indicators

    if (
        indicators.ema20 is None
        or indicators.ema50 is None
        or indicators.ema200 is None
    ):
        return False

    return (
        indicators.ema20
        > indicators.ema50
        > indicators.ema200
    )


def is_candidate_eligible(
    candidate: ScanCandidate,
) -> bool:
    """
    Determine whether a candidate can enter the ranking stage.
    """

    return (
        has_valid_price(candidate)
        and has_required_indicators(candidate)
        and has_bullish_ema_alignment(candidate)
    )