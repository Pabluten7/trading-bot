
"""
Trading cycle.

Runs one complete analysis/execution cycle for the configured
trading universe.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from loguru import logger

from app.broker.service import broker_service
from app.data.service import market_data_service
from app.indicators.calculator import indicator_calculator
from app.portfolio.models import Position, PortfolioSnapshot
from app.scanner.scanner import MarketScanner
from app.scanner.scoring import candidate_scorer
from app.trading.engine import trading_engine


class TradingCycle:
    """Execute one complete trading cycle."""

    def __init__(self) -> None:
        self._scanner = MarketScanner(
            market_data=market_data_service,
            indicator_calculator=indicator_calculator,
            scorer=candidate_scorer,
        )

    def run(self) -> None:
        """
        Execute one trading cycle.

        The cycle:
        1. Reads the broker account.
        2. Reads current positions.
        3. Scans the configured universe.
        4. Ranks eligible candidates.
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

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=90)

        candidates = self._scanner.scan(
            symbols=symbols,
            start=start,
            end=end,
        )

        for candidate in candidates:
            self._process_candidate(
                candidate=candidate,
                portfolio=portfolio,
            )

    def _process_candidate(
        self,
        *,
        candidate,
        portfolio: PortfolioSnapshot,
    ) -> None:
        """Process one ranked scanner candidate."""

        context = self._build_context(
            symbol=candidate.symbol,
            close=candidate.price,
            indicators=candidate.indicators,
        )

        result = trading_engine.evaluate_and_execute(
            context=context,
            portfolio=portfolio,
            sector=self._get_sector(candidate.symbol),
        )

        logger.info(
            "Trading cycle result for {}: {} - {}",
            candidate.symbol,
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
        Return the configured trading universe.

        The S&P 500 universe integration will provide these symbols.
        """

        return []

    @staticmethod
    def _get_sector(symbol: str) -> str:
        """
        Return the sector for a symbol.

        Sector metadata will come from the universe layer.
        """

        del symbol

        return "unknown"


trading_cycle = TradingCycle()
