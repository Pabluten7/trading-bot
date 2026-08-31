"""
Trading cycle.

Runs one complete analysis/execution cycle for the configured
trading universe.
"""

from __future__ import annotations

from loguru import logger

from app.broker.service import broker_service
from app.config.settings import settings
from app.data.service import market_data_service
from app.indicators.calculator import indicator_calculator
from app.portfolio.models import Position, PortfolioSnapshot
from app.trading.engine import trading_engine


class TradingCycle:
    """Execute one complete trading cycle."""

    def run(self) -> None:
        """
        Execute one trading cycle.

        The cycle:
        1. Reads the broker account.
        2. Reads current positions.
        3. Obtains market data.
        4. Calculates indicators.
        5. Evaluates the strategy.
        6. Applies risk controls.
        7. Sends permitted orders to the broker.
        """

        if not broker_service.is_configured():
            logger.warning(
                "Trading cycle skipped: broker is not configured."
            )
            return

        account = broker_service.get_account()
        broker_positions = broker_service.get_positions()

        portfolio = self._build_portfolio_snapshot(
            account_equity=float(account.equity),
            broker_positions=broker_positions,
        )

        symbols = self._get_symbols()

        if not symbols:
            logger.warning(
                "Trading cycle skipped: no symbols configured."
            )
            return

        for symbol in symbols:
            self._process_symbol(
                symbol=symbol,
                portfolio=portfolio,
            )

    def _process_symbol(
        self,
        *,
        symbol: str,
        portfolio: PortfolioSnapshot,
    ) -> None:
        """Process one symbol."""

        candles = market_data_service.get_candles(
            symbols=[symbol],
        )

        symbol_candles = candles.get(symbol, [])

        if not symbol_candles:
            logger.debug(
                "No candles available for {}.",
                symbol,
            )
            return

        snapshots = indicator_calculator.calculate(
            symbol_candles
        )

        if not snapshots:
            return

        latest_candle = symbol_candles[-1]
        latest_indicators = snapshots[-1]

        context = self._build_context(
            symbol=symbol,
            close=float(latest_candle.close),
            indicators=latest_indicators,
        )

        result = trading_engine.evaluate_and_execute(
            context=context,
            portfolio=portfolio,
            sector=self._get_sector(symbol),
        )

        logger.info(
            "Trading cycle result for {}: {} - {}",
            symbol,
            result.decision,
            result.reason,
        )

    @staticmethod
    def _build_portfolio_snapshot(
        *,
        account_equity: float,
        broker_positions: list,
    ) -> PortfolioSnapshot:
        """Convert broker positions into the internal portfolio model."""

        positions = tuple(
            Position(
                symbol=position.symbol,
                sector="unknown",
                quantity=int(position.quantity),
                entry_price=float(
                    position.average_entry_price
                ),
                stop_price=0.0,
                risk_amount=0.0,
            )
            for position in broker_positions
        )

        return PortfolioSnapshot(
            account_equity=account_equity,
            positions=positions,
        )

    @staticmethod
    def _build_context(
        *,
        symbol: str,
        close: float,
        indicators,
    ):
        """Build the strategy context."""

        from app.strategy.models import StrategyContext

        return StrategyContext(
            symbol=symbol,
            close=close,
            indicators=indicators,
        )

    @staticmethod
    def _get_symbols() -> list[str]:
        """
        Return the symbols to process.

        The scanner/universe integration will replace this temporary
        configuration-driven source.
        """

        return []

    @staticmethod
    def _get_sector(symbol: str) -> str:
        """
        Return the sector for a symbol.

        Sector metadata will later come from the scanner/universe layer.
        """

        del symbol

        return "unknown"


trading_cycle = TradingCycle()