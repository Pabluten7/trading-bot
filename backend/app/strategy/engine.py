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

    # ------------------------------------------------------------
    # Strategy thresholds
    # ------------------------------------------------------------

    RSI_OVERSOLD = 30.0
    RSI_OVERBOUGHT = 70.0

    # Minimum score required to generate an actionable signal.
    MIN_ENTRY_SCORE = 0.60

    def evaluate(
        self,
        context: StrategyContext,
    ) -> StrategySignal:
        """
        Evaluate the current market context.

        The strategy currently uses:
        - EMA20 / EMA50 / EMA200 for trend alignment.
        - RSI14 for momentum confirmation.
        - ATR14 for volatility-aware stop and target calculation.
        - Market direction as an additional trend filter.

        The strategy only generates long signals.
        """

        indicators = context.indicators

        if (
            indicators.ema20 is None
            or indicators.ema50 is None
            or indicators.ema200 is None
            or indicators.rsi14 is None
            or indicators.atr14 is None
        ):
            return self._hold(
                context,
                "Insufficient indicator history.",
            )

        if indicators.atr14 <= 0:
            return self._hold(
                context,
                "Invalid ATR value.",
            )

        close = context.close
        ema20 = indicators.ema20
        ema50 = indicators.ema50
        ema200 = indicators.ema200
        rsi14 = indicators.rsi14
        atr14 = indicators.atr14

        # --------------------------------------------------------
        # Long trend alignment
        # --------------------------------------------------------

        bullish_alignment = (
            close > ema20
            and ema20 > ema50
            and ema50 > ema200
        )

        if not bullish_alignment:
            return self._hold(
                context,
                "Bullish EMA alignment is not present.",
            )

        if context.market_direction != MarketDirection.BULLISH:
            return self._hold(
                context,
                "Market direction is not bullish.",
            )

        # --------------------------------------------------------
        # Momentum confirmation
        # --------------------------------------------------------

        if rsi14 >= self.RSI_OVERBOUGHT:
            return self._hold(
                context,
                "RSI is overbought.",
            )

        # Avoid entering when momentum is excessively weak.
        if rsi14 <= self.RSI_OVERSOLD:
            return self._hold(
                context,
                "RSI indicates excessive weakness.",
            )

        # --------------------------------------------------------
        # Signal scoring
        # --------------------------------------------------------

        score = self._calculate_entry_score(
            close=close,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            rsi14=rsi14,
        )

        if score < self.MIN_ENTRY_SCORE:
            return self._hold(
                context,
                "Entry conditions do not reach the minimum score.",
            )

        # --------------------------------------------------------
        # Volatility-based protection
        # --------------------------------------------------------

        stop_loss = close - (2.0 * atr14)

        take_profit = close + (4.0 * atr14)

        return StrategySignal(
            symbol=context.symbol,
            action=SignalAction.BUY,
            score=score,
            reason=(
                "Bullish EMA alignment with confirmed market "
                "direction and acceptable RSI momentum."
            ),
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
        )

    @staticmethod
    def _calculate_entry_score(
        *,
        close: float,
        ema20: float,
        ema50: float,
        ema200: float,
        rsi14: float,
    ) -> float:
        """
        Calculate the confidence score for a long entry.

        Score components:

        0.30 -> price above EMA20
        0.25 -> EMA20 above EMA50
        0.25 -> EMA50 above EMA200
        0.20 -> RSI in the preferred momentum zone
        """

        score = 0.0

        if close > ema20:
            score += 0.30

        if ema20 > ema50:
            score += 0.25

        if ema50 > ema200:
            score += 0.25

        # Prefer positive momentum without buying an overbought market.
        if 50.0 <= rsi14 < 70.0:
            score += 0.20
        elif 40.0 <= rsi14 < 50.0:
            score += 0.10

        return min(score, 1.0)

    @staticmethod
    def _hold(
        context: StrategyContext,
        reason: str,
    ) -> StrategySignal:
        """Create a HOLD signal."""

        return StrategySignal(
            symbol=context.symbol,
            action=SignalAction.HOLD,
            score=0.0,
            reason=reason,
        )


strategy_engine = StrategyEngine()