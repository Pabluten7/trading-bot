"""
Central risk management service.
"""

from __future__ import annotations

from app.config.settings import settings
from app.risk.models import PositionSizing, RiskParameters
from app.risk.portfolio_risk import PortfolioRisk
from app.risk.position_sizer import position_sizer


class RiskManager:
    """Coordinate trade-level and portfolio-level risk."""

    def calculate_position(
        self,
        *,
        account_equity: float,
        entry_price: float,
        stop_price: float,
    ) -> PositionSizing:
        """
        Calculate a position using the configured trade risk.
        """

        parameters = RiskParameters(
            account_equity=account_equity,
            entry_price=entry_price,
            stop_price=stop_price,
            risk_per_trade_percent=(
                settings.risk.max_risk_per_trade_percent
            ),
        )

        return position_sizer.calculate(
            parameters
        )

    def can_open_position(
        self,
        *,
        account_equity: float,
        current_risk_amount: float,
        additional_risk: float,
    ) -> bool:
        """Check whether a new position fits portfolio risk limits."""

        portfolio_risk = PortfolioRisk(
            account_equity=account_equity,
            current_risk_amount=current_risk_amount,
            maximum_risk_percent=(
                settings.risk.maximum_portfolio_risk_percent
            ),
        )

        return portfolio_risk.can_accept_risk(
            additional_risk
        )


risk_manager = RiskManager()