"""
Portfolio management service.
"""

from __future__ import annotations

from app.config.settings import settings
from app.portfolio.models import (
    PortfolioSnapshot,
    Position,
)


class PortfolioManager:
    """Manage portfolio-level position constraints."""

    def can_open_position(
        self,
        portfolio: PortfolioSnapshot,
        position: Position,
    ) -> bool:
        """
        Determine whether a new position satisfies portfolio limits.

        Limits:
        - Maximum 8 simultaneous positions.
        - Maximum 3 positions per sector.
        """

        if position.quantity <= 0:
            return False

        if portfolio.position_count >= (
            settings.trading.maximum_simultaneous_positions
        ):
            return False

        if portfolio.positions_in_sector(
            position.sector
        ) >= settings.trading.maximum_positions_per_sector:
            return False

        return True

    def add_position(
        self,
        portfolio: PortfolioSnapshot,
        position: Position,
    ) -> PortfolioSnapshot:
        """Return a new portfolio snapshot with a position added."""

        if not self.can_open_position(
            portfolio,
            position,
        ):
            raise ValueError(
                "Position violates portfolio constraints."
            )

        return PortfolioSnapshot(
            account_equity=portfolio.account_equity,
            positions=(
                *portfolio.positions,
                position,
            ),
        )

    def remove_position(
        self,
        portfolio: PortfolioSnapshot,
        symbol: str,
    ) -> PortfolioSnapshot:
        """Return a new portfolio snapshot without a position."""

        positions = tuple(
            position
            for position in portfolio.positions
            if position.symbol != symbol
        )

        return PortfolioSnapshot(
            account_equity=portfolio.account_equity,
            positions=positions,
        )


portfolio_manager = PortfolioManager()