"""
Market scanner.

Filters and ranks market symbols according to the configured
technical criteria.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.data.models import Candle
from app.indicators.calculator import IndicatorCalculator
from app.scanner.filters import is_eligible
from app.scanner.models import ScanCandidate, ScanResult
from app.scanner.scoring import calculate_total_score


@dataclass(frozen=True)
class SymbolMarketData:
    """
    Market data required by the scanner for one symbol.
    """

    symbol: str
    sector: str
    candles: list[Candle]


class MarketScanner:
    """
    Scans and ranks market symbols.
    """

    def __init__(
        self,
        indicator_calculator: IndicatorCalculator | None = None,
    ) -> None:
        self._indicator_calculator = (
            indicator_calculator
            or IndicatorCalculator()
        )

    def scan(
        self,
        symbols: list[SymbolMarketData],
        maximum_candidates: int = 8,
    ) -> ScanResult:
        """
        Scan symbols and return the best candidates.

        Candidates are always ordered by descending score.
        """

        if maximum_candidates <= 0:
            raise ValueError(
                "maximum_candidates must be greater than zero."
            )

        candidates: list[ScanCandidate] = []

        for market_data in symbols:
            if not market_data.candles:
                continue

            candles = market_data.candles

            indicators = (
                self._indicator_calculator.calculate(
                    candles
                )
            )

            if not indicators:
                continue

            latest_indicators = indicators[-1]
            latest_candle = candles[-1]

            price = latest_candle.close

            if not is_eligible(
                latest_indicators,
                price,
            ):
                continue

            (
                total_score,
                trend_score,
                momentum_score,
                volatility_score,
            ) = calculate_total_score(
                latest_indicators,
                price,
            )

            candidates.append(
                ScanCandidate(
                    symbol=market_data.symbol,
                    sector=market_data.sector,
                    price=price,
                    indicators=latest_indicators,
                    score=total_score,
                    trend_score=trend_score,
                    momentum_score=momentum_score,
                    volatility_score=volatility_score,
                )
            )

        candidates.sort(
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        selected = self._apply_sector_limit(
            candidates,
            maximum_candidates,
        )

        return ScanResult(
            candidates=selected,
            scanned_symbols=len(symbols),
            eligible_symbols=len(candidates),
            maximum_candidates=maximum_candidates,
        )

    @staticmethod
    def _apply_sector_limit(
        candidates: list[ScanCandidate],
        maximum_candidates: int,
        maximum_per_sector: int = 3,
    ) -> list[ScanCandidate]:
        """
        Limit the number of selected stocks per sector.

        Candidates must already be sorted by score.
        """

        sector_counts: dict[str, int] = {}
        selected: list[ScanCandidate] = []

        for candidate in candidates:
            sector = candidate.sector

            current_count = sector_counts.get(
                sector,
                0,
            )

            if current_count >= maximum_per_sector:
                continue

            selected.append(candidate)

            sector_counts[sector] = (
                current_count + 1
            )

            if len(selected) >= maximum_candidates:
                break

        return selected


scanner = MarketScanner()