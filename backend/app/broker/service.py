"""
Broker service.

Provides the application-level interface to the configured broker.
"""

from __future__ import annotations

from decimal import Decimal

from app.broker.models import (
    Account,
    Order,
    OrderSide,
    OrderType,
    Position,
)
from app.broker.provider import BrokerProvider


class BrokerService:
    """Application-level broker service."""

    def __init__(
        self,
        provider: BrokerProvider | None = None,
    ) -> None:
        self._provider = provider

    @property
    def provider(self) -> BrokerProvider | None:
        """Return the configured broker provider."""

        return self._provider

    def configure_provider(
        self,
        provider: BrokerProvider | None,
    ) -> None:
        """Configure the broker provider."""

        self._provider = provider

    def is_configured(self) -> bool:
        """Return whether a broker provider is configured."""

        return self._provider is not None

    def get_account(self) -> Account:
        """Return account information."""

        return self._require_provider().get_account()

    def get_positions(self) -> list[Position]:
        """Return open positions."""

        return self._require_provider().get_positions()

    def get_position(
        self,
        symbol: str,
    ) -> Position | None:
        """Return an open position."""

        return self._require_provider().get_position(
            symbol
        )

    def submit_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
    ) -> Order:
        """Submit an order."""

        return self._require_provider().submit_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
        )

    def cancel_order(
        self,
        order_id: str,
    ) -> None:
        """Cancel an order."""

        self._require_provider().cancel_order(
            order_id
        )

    def get_order(
        self,
        order_id: str,
    ) -> Order | None:
        """Return an order."""

        return self._require_provider().get_order(
            order_id
        )

    def _require_provider(self) -> BrokerProvider:
        """Return the provider or raise if unavailable."""

        if self._provider is None:
            raise RuntimeError(
                "Broker provider is not configured."
            )

        return self._provider


broker_service = BrokerService()