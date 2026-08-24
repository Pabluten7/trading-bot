"""
Portfolio domain models.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """Open long position."""

    symbol: str
    sector: str

    quantity: int
    entry_price: float
    stop_price: float

    risk_amount: float

    @property
    def market_value(self) -> float:
        """Return the position value at entry."""

        return self.quantity * self.entry_price


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Current portfolio state."""

    account_equity: float
    positions: tuple[Position, ...]

    @property
    def position_count(self) -> int:
        """Return the number of open positions."""

        return len(self.positions)

    @property
    def total_risk_amount(self) -> float:
        """Return the total monetary risk of open positions."""

        return sum(
            position.risk_amount
            for position in self.positions
        )

    @property
    def total_position_value(self) -> float:
        """Return the total value of open positions."""

        return sum(
            position.market_value
            for position in self.positions
        )

    def positions_in_sector(
        self,
        sector: str,
    ) -> int:
        """Return the number of positions in a sector."""

        return sum(
            position.sector == sector
            for position in self.positions
        )