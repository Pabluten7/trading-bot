"""
Strategy engine.

Transforms normalized market context into a trading signal.

The engine does not execute orders and does not manage portfolio risk.
"""

from __future__ import annotations

from app.strategy.models import (
    MarketDirection,
    StrategyContext,
)
from app.strategy.signal import (
    SignalAction,
    StrategySignal,
)


class StrategyEngine:
    """Generate trading decisions from market conditions."""

    def evaluate(
        self,
        context: StrategyContext,
    ) -> StrategySignal:
        """
        Evaluate the current market context.

        The engine intentionally returns HOLD when there is not enough
        information to make a valid strategy decision.
        """

        indicators = context.indicators

        if (
            indicators.ema20 is None
            or indicators.ema50 is None
            or indicators.ema200 is None
            or indicators.rsi14 is None
            or indicators.atr14 is None
        ):
            return StrategySignal(
                symbol=context.symbol,
                action=SignalAction.HOLD,
                score=0.0,
                reason="Insufficient indicator history.",
            )

        if context.market_direction == MarketDirection.BULLISH:
            return StrategySignal(
                symbol=context.symbol,
                action=SignalAction.HOLD,
                score=0.0,
                reason=(
                    "Bullish market detected; entry conditions "
                    "are not yet configured."
                ),
            )

        if context.market_direction == MarketDirection.BEARISH:
            return StrategySignal(
                symbol=context.symbol,
                action=SignalAction.HOLD,
                score=0.0,
                reason=(
                    "Bearish market detected; exit conditions "
                    "are not yet configured."
                ),
            )

        return StrategySignal(
            symbol=context.symbol,
            action=SignalAction.HOLD,
            score=0.0,
            reason="No actionable strategy condition.",
        )


strategy_engine = StrategyEngine()