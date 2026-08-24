"""
Candidate scoring system.

Converts technical conditions into a normalized score used to rank
scanner candidates.
"""

from __future__ import annotations

from app.scanner.models import ScanCandidate


class CandidateScorer:
    """
    Calculate a normalized candidate score.

    The score is used for ranking, not for directly executing trades.
    """

    def score(
        self,
        candidate: ScanCandidate,
    ) -> float:
        """
        Calculate the candidate score.

        The current model rewards:

        - bullish EMA alignment
        - healthy RSI momentum
        - usable ATR volatility

        The result is normalized to 0-100.
        """

        indicators = candidate.indicators

        score = 0.0

        # ------------------------------------------------------------
        # Trend: 50 points
        # ------------------------------------------------------------

        if (
            indicators.ema20 is not None
            and indicators.ema50 is not None
            and indicators.ema200 is not None
        ):
            if (
                indicators.ema20
                > indicators.ema50
                > indicators.ema200
            ):
                score += 50.0

            elif indicators.ema20 > indicators.ema50:
                score += 25.0

        # ------------------------------------------------------------
        # Momentum: 30 points
        # ------------------------------------------------------------

        rsi_value = indicators.rsi14

        if rsi_value is not None:
            if 55.0 <= rsi_value <= 65.0:
                score += 30.0

            elif 50.0 <= rsi_value <= 70.0:
                score += 20.0

            elif 45.0 <= rsi_value <= 75.0:
                score += 10.0

        # ------------------------------------------------------------
        # Volatility: 20 points
        # ------------------------------------------------------------

        atr_value = indicators.atr14

        if (
            atr_value is not None
            and candidate.price > 0
        ):
            atr_percentage = (
                atr_value / candidate.price
            ) * 100.0

            if 1.0 <= atr_percentage <= 4.0:
                score += 20.0

            elif 0.5 <= atr_percentage <= 7.0:
                score += 10.0

        return round(
            min(score, 100.0),
            2,
        )


candidate_scorer = CandidateScorer()