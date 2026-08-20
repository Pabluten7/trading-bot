"""
Indicator calculation service.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.data.models import Candle
from app.indicators.atr import atr
from app.indicators.ema import ema
from app.indicators.rsi import rsi


@dataclass(frozen=True)
class IndicatorSnapshot:
    """Calculated indicators for a single candle."""

    ema20: float | None
    ema50: float | None
    ema200: float | None

    rsi14: float | None
    atr14: float | None


class IndicatorCalculator:
    """Calculate the indicators required by the trading system."""

    def calculate(
        self,
        candles: list[Candle],
    ) -> list[IndicatorSnapshot]:
        """
        Calculate all configured indicators.

        Candles must be ordered from oldest to newest.
        """

        if not candles:
            return []

        closes = [
            candle.close
            for candle in candles
        ]

        ema20_values = ema(
            closes,
            period=20,
        )

        ema50_values = ema(
            closes,
            period=50,
        )

        ema200_values = ema(
            closes,
            period=200,
        )

        rsi_values = rsi(
            closes,
            period=14,
        )

        atr_values = atr(
            candles,
            period=14,
        )

        snapshots: list[IndicatorSnapshot] = []

        for index in range(len(candles)):
            snapshots.append(
                IndicatorSnapshot(
                    ema20=ema20_values[index],
                    ema50=ema50_values[index],
                    ema200=ema200_values[index],
                    rsi14=rsi_values[index],
                    atr14=atr_values[index],
                )
            )

        return snapshots


indicator_calculator = IndicatorCalculator()