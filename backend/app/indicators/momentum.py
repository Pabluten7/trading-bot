"""
Momentum indicators.
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


class RSI(Indicator):
    """
    Relative Strength Index.

    Uses Wilder's smoothing method to measure price momentum.
    """

    def __init__(
        self,
        period: int = 14,
    ) -> None:
        if period <= 0:
            raise ValueError(
                "RSI period must be greater than zero."
            )

        self.period = period
        self.name = f"RSI_{period}"

    def calculate(
        self,
        candles: Sequence[Candle],
    ) -> IndicatorSeries:
        """Calculate RSI values."""

        if len(candles) <= self.period:
            return IndicatorSeries(
                name=self.name,
                values=(),
            )

        gains: list[Decimal] = []
        losses: list[Decimal] = []

        for previous, current in zip(
            candles[:-1],
            candles[1:],
        ):
            change = current.close - previous.close

            if change > 0:
                gains.append(change)
                losses.append(Decimal("0"))
            else:
                gains.append(Decimal("0"))
                losses.append(abs(change))

        average_gain = (
            sum(gains[:self.period], Decimal("0"))
            / Decimal(self.period)
        )

        average_loss = (
            sum(losses[:self.period], Decimal("0"))
            / Decimal(self.period)
        )

        values: list[IndicatorValue] = []

        for index in range(
            self.period,
            len(gains),
        ):
            if index > self.period:
                average_gain = (
                    (
                        average_gain
                        * Decimal(self.period - 1)
                    )
                    + gains[index]
                ) / Decimal(self.period)

                average_loss = (
                    (
                        average_loss
                        * Decimal(self.period - 1)
                    )
                    + losses[index]
                ) / Decimal(self.period)

            if average_loss == 0:
                rsi = Decimal("100")
            else:
                relative_strength = (
                    average_gain / average_loss
                )

                rsi = (
                    Decimal("100")
                    - (
                        Decimal("100")
                        / (
                            Decimal("1")
                            + relative_strength
                        )
                    )
                )

            candle = candles[index + 1]

            values.append(
                IndicatorValue(
                    name=self.name,
                    timestamp=candle.timestamp,
                    value=rsi,
                )
            )

        return IndicatorSeries(
            name=self.name,
            values=tuple(values),
        )


class RSI14(RSI):
    """14-period RSI."""

    def __init__(self) -> None:
        super().__init__(14)