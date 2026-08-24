"""
Portfolio-level risk management.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PortfolioRisk:
    """Current portfolio risk state."""

    account_equity: float
    current_risk_amount: float

    maximum_risk_percent: float

    @property
    def maximum_risk_amount(self) -> float:
        """Return the maximum allowed portfolio risk."""

        return (
            self.account_equity
            * self.maximum_risk_percent
            / 100.0
        )

    @property
    def remaining_risk_amount(self) -> float:
        """Return remaining available portfolio risk."""

        return max(
            self.maximum_risk_amount
            - self.current_risk_amount,
            0.0,
        )

    def can_accept_risk(
        self,
        additional_risk: float,
    ) -> bool:
        """Return whether additional risk can be accepted."""

        if additional_risk < 0:
            raise ValueError(
                "Additional risk cannot be negative."
            )

        return (
            self.current_risk_amount
            + additional_risk
            <= self.maximum_risk_amount
        )