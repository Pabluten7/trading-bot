"""
Trend indicators.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.data.models import Candle
from app.indicators.base import Indicator
from app.indicators.models import (
    IndicatorSeries,
    IndicatorValue,
)


class EMA(Indicator):
    """
    Exponential Moving Average.

    The EMA gives greater weight to recent prices and is used by
    the strategy to determine market trend and trend alignment.
    """

    def __init__(
        self,
        period: int,
    ) -> None:
        if period <= 0:
            raise ValueError(
                "EMA period must be greater than zero."
            )

        self.period = period
        self.name = f"EMA_{period}"

    def calculate(
        self,
        candles: Sequence[Candle],
    ) -> IndicatorSeries:
        """Calculate the EMA from candle closing prices."""

        if not candles:
            return IndicatorSeries(
                name=self.name,
                values=(),
            )

        closes = [
            candle.close
            for candle in candles
        ]

        multiplier = Decimal("2") / (
            Decimal(self.period) + Decimal("1")
        )

        values: list[IndicatorValue] = []

        ema = closes[0]

        values.append(
            IndicatorValue(
                name=self.name,
                timestamp=candles[0].timestamp,
                value=ema,
            )
        )

        for candle, close in zip(
            candles[1:],
            closes[1:],
        ):
            ema = (
                (close - ema) * multiplier
            ) + ema

            values.append(
                IndicatorValue(
                    name=self.name,
                    timestamp=candle.timestamp,
                    value=ema,
                )
            )

        return IndicatorSeries(
            name=self.name,
            values=tuple(values),
        )


class EMA20(EMA):
    """20-period exponential moving average."""

    def __init__(self) -> None:
        super().__init__(20)


class EMA50(EMA):
    """50-period exponential moving average."""

    def __init__(self) -> None:
        super().__init__(50)


class EMA200(EMA):
    """200-period exponential moving average."""

    def __init__(self) -> None:
        super().__init__(200)