"""
Position sizing service.

Calculates the maximum position size allowed by the configured
risk per trade.
"""

from __future__ import annotations

import math

from app.config.settings import settings
from app.risk.models import PositionSizing, RiskParameters


class PositionSizer:
    """Calculate position size from account and trade risk."""

    def calculate(
        self,
        parameters: RiskParameters,
    ) -> PositionSizing:
        """
        Calculate the position size for a trade.

        Risk is based on the distance between entry price and stop price.
        """

        if parameters.account_equity <= 0:
            raise ValueError(
                "Account equity must be greater than zero."
            )

        if parameters.entry_price <= 0:
            raise ValueError(
                "Entry price must be greater than zero."
            )

        if parameters.stop_price <= 0:
            raise ValueError(
                "Stop price must be greater than zero."
            )

        if parameters.stop_price >= parameters.entry_price:
            raise ValueError(
                "Stop price must be below entry price for a long position."
            )

        if parameters.risk_per_trade_percent <= 0:
            raise ValueError(
                "Risk per trade must be greater than zero."
            )

        risk_amount = (
            parameters.account_equity
            * parameters.risk_per_trade_percent
            / 100.0
        )

        risk_per_share = (
            parameters.entry_price
            - parameters.stop_price
        )

        quantity = math.floor(
            risk_amount / risk_per_share
        )

        if quantity < 1:
            quantity = 0

        position_value = (
            quantity * parameters.entry_price
        )

        actual_risk_amount = (
            quantity * risk_per_share
        )

        actual_risk_percent = (
            actual_risk_amount
            / parameters.account_equity
        ) * 100.0

        return PositionSizing(
            entry_price=parameters.entry_price,
            stop_price=parameters.stop_price,
            risk_per_share=risk_per_share,
            risk_amount=actual_risk_amount,
            quantity=quantity,
            position_value=position_value,
            risk_percent=actual_risk_percent,
        )


position_sizer = PositionSizer()