"""
Trading execution engine.

Coordinates strategy, portfolio risk, position sizing, and broker
execution without embedding strategy rules inside the execution layer.
"""

from __future__ import annotations

from decimal import Decimal

from app.broker.models import OrderSide, OrderType
from app.broker.service import broker_service
from app.portfolio.models import PortfolioSnapshot
from app.risk.manager import risk_manager
from app.strategy.models import StrategyContext
from app.strategy.signal import SignalAction
from app.strategy.strategy import strategy
from app.trading.models import TradeDecision, TradeResult


class TradingEngine:
    """Coordinate strategy decisions with risk and broker execution."""

    def evaluate_and_execute(
        self,
        *,
        context: StrategyContext,
        portfolio: PortfolioSnapshot,
        sector: str,
    ) -> TradeResult:
        """
        Evaluate a symbol and execute an order when permitted.

        Strategy determines the signal.
        Risk determines whether the trade is acceptable.
        Broker executes the resulting order.
        """

        signal = strategy.evaluate(context)

        if signal.action == SignalAction.HOLD:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.HOLD,
                reason=signal.reason,
            )

        if signal.action == SignalAction.SELL:
            return self._handle_sell(
                context=context,
                portfolio=portfolio,
            )

        if signal.action == SignalAction.BUY:
            return self._handle_buy(
                context=context,
                portfolio=portfolio,
                sector=sector,
            )

        return TradeResult(
            symbol=context.symbol,
            decision=TradeDecision.REJECTED,
            reason="Unsupported strategy action.",
        )

    def _handle_buy(
        self,
        *,
        context: StrategyContext,
        portfolio: PortfolioSnapshot,
        sector: str,
    ) -> TradeResult:
        """Validate and execute a long entry."""

        if portfolio.position_count >= 8:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="Maximum simultaneous positions reached.",
            )

        if portfolio.positions_in_sector(sector) >= 3:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="Maximum positions in sector reached.",
            )

        if context.indicators.atr14 is None:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="ATR is unavailable.",
            )

        entry_price = context.close

        stop_price = (
            entry_price
            - (context.indicators.atr14 * 2.0)
        )

        if stop_price <= 0:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="Calculated stop price is invalid.",
            )

        sizing = risk_manager.calculate_position(
            account_equity=portfolio.account_equity,
            entry_price=entry_price,
            stop_price=stop_price,
        )

        if sizing.quantity <= 0:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="Calculated position size is zero.",
            )

        if not risk_manager.can_accept_position_risk(
            portfolio,
            sizing.risk_amount,
        ):
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="Portfolio risk limit would be exceeded.",
            )

        order = broker_service.submit_order(
            symbol=context.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal(str(sizing.quantity)),
        )

        return TradeResult(
            symbol=context.symbol,
            decision=TradeDecision.BUY,
            reason="Buy order submitted.",
            quantity=Decimal(str(sizing.quantity)),
            order=order,
        )

    def _handle_sell(
        self,
        *,
        context: StrategyContext,
        portfolio: PortfolioSnapshot,
    ) -> TradeResult:
        """Handle an exit signal."""

        position = next(
            (
                position
                for position in portfolio.positions
                if position.symbol == context.symbol
            ),
            None,
        )

        if position is None:
            return TradeResult(
                symbol=context.symbol,
                decision=TradeDecision.REJECTED,
                reason="No open position exists for symbol.",
            )

        order = broker_service.submit_order(
            symbol=context.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal(str(position.quantity)),
        )

        return TradeResult(
            symbol=context.symbol,
            decision=TradeDecision.SELL,
            reason="Sell order submitted.",
            quantity=Decimal(str(position.quantity)),
            order=order,
        )


trading_engine = TradingEngine()