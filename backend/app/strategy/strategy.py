"""
Trading strategy engine.
"""

from __future__ import annotations

from app.scanner.models import ScanCandidate
from app.strategy.conditions import meets_entry_conditions
from app.strategy.models import (
    EntrySignal,
    SignalDirection,
    SignalStrength,
)


class TradingStrategy:
    """
    Converts scanner candidates into entry signals.

    This class does not execute trades and does not manage
    portfolio positions.
    """

    def evaluate(
        self,
        candidate: ScanCandidate,
    ) -> EntrySignal | None:
        """
        Evaluate one scanner candidate.

        Returns None when no entry signal exists.
        """

        if not candidate.eligible:
            return None

        if not meets_entry_conditions(candidate):
            return None

        strength = self._calculate_strength(
            candidate.score
        )

        reason = self._build_reason(
            candidate
        )

        return EntrySignal(
            symbol=candidate.symbol,
            direction=SignalDirection.LONG,
            strength=strength,
            score=candidate.score,
            price=candidate.price,
            reason=reason,
            candidate=candidate,
        )

    def evaluate_many(
        self,
        candidates: list[ScanCandidate],
    ) -> list[EntrySignal]:
        """
        Evaluate multiple candidates.

        Signals preserve the scanner's score ordering.
        """

        signals: list[EntrySignal] = []

        for candidate in candidates:
            signal = self.evaluate(candidate)

            if signal is not None:
                signals.append(signal)

        signals.sort(
            key=lambda signal: signal.score,
            reverse=True,
        )

        return signals

    @staticmethod
    def _calculate_strength(
        score: float,
    ) -> SignalStrength:
        """Convert a numerical score into signal strength."""

        if score >= 80.0:
            return SignalStrength.STRONG

        if score >= 65.0:
            return SignalStrength.MODERATE

        return SignalStrength.WEAK

    @staticmethod
    def _build_reason(
        candidate: ScanCandidate,
    ) -> str:
        """Build a human-readable explanation for the signal."""

        indicators = candidate.indicators

        return (
            "Bullish trend confirmed by EMA alignment "
            f"(EMA20={indicators.ema20:.2f}, "
            f"EMA50={indicators.ema50:.2f}, "
            f"EMA200={indicators.ema200:.2f}); "
            f"RSI14={indicators.rsi14:.2f}; "
            f"ATR14={indicators.atr14:.2f}; "
            f"scanner score={candidate.score:.2f}."
        )


strategy = TradingStrategy()