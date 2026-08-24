"""
Market scanner.

Transforms market candles into ranked trading candidates.
"""

from __future__ import annotations

from datetime import datetime

from app.data.provider import MarketDataProvider
from app.indicators.calculator import IndicatorCalculator
from app.scanner.filters import is_candidate_eligible
from app.scanner.models import ScanCandidate
from app.scanner.scoring import CandidateScorer


class MarketScanner:
    """
    Scan a universe of symbols and produce ranked candidates.

    The scanner does not execute trades.
    """

    def __init__(
        self,
        market_data: MarketDataProvider,
        indicator_calculator: IndicatorCalculator,
        scorer: CandidateScorer,
    ) -> None:
        self._market_data = market_data
        self._indicator_calculator = indicator_calculator
        self._scorer = scorer

    def scan(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> list[ScanCandidate]:
        """
        Scan the requested symbols.

        Candidates are returned ordered by score descending.
        """

        if not symbols:
            return []

        candles_by_symbol = (
            self._market_data.get_candles(
                symbols=symbols,
                start=start,
                end=end,
            )
        )

        candidates: list[ScanCandidate] = []

        for symbol in symbols:
            candles = candles_by_symbol.get(
                symbol,
                [],
            )

            if not candles:
                continue

            candles = sorted(
                candles,
                key=lambda candle: candle.timestamp,
            )

            snapshots = (
                self._indicator_calculator.calculate(
                    candles
                )
            )

            if not snapshots:
                continue

            latest_candle = candles[-1]
            latest_indicators = snapshots[-1]

            candidate = ScanCandidate(
                symbol=symbol,
                price=float(latest_candle.close),
                indicators=latest_indicators,
                score=0.0,
                eligible=False,
                candle=latest_candle,
            )

            eligible = is_candidate_eligible(
                candidate
            )

            candidate = ScanCandidate(
                symbol=candidate.symbol,
                price=candidate.price,
                indicators=candidate.indicators,
                score=candidate.score,
                eligible=eligible,
                candle=candidate.candle,
            )

            if not eligible:
                continue

            score = self._scorer.score(
                candidate
            )

            candidate = ScanCandidate(
                symbol=candidate.symbol,
                price=candidate.price,
                indicators=candidate.indicators,
                score=score,
                eligible=True,
                candle=candidate.candle,
            )

            candidates.append(candidate)

        candidates.sort(
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        return candidates