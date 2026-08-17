"""
Payment service.

Provides a provider-independent payment abstraction.

The service does not directly activate subscriptions or licenses.
Payment confirmation is handled separately so that payment providers
cannot bypass the application's subscription and licensing rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PaymentStatus(str, Enum):
    """Supported payment states."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PaymentCheckout:
    """Checkout information returned to the API."""

    checkout_id: str
    checkout_url: str
    status: PaymentStatus


@dataclass(frozen=True)
class PaymentEvent:
    """
    Normalized payment event.

    Payment providers will be converted into this internal format
    before reaching the subscription system.
    """

    event_id: str
    user_id: int
    status: PaymentStatus
    amount: int
    currency: str
    provider: str
    raw_data: dict[str, Any]


class PaymentService:
    """
    Provider-independent payment service.

    The actual payment provider will be injected later.
    """

    def __init__(self) -> None:
        self._provider: Any | None = None

    @property
    def provider(self) -> Any | None:
        """Return the configured payment provider."""

        return self._provider

    def configure_provider(
        self,
        provider: Any,
    ) -> None:
        """
        Configure the payment provider.

        The provider must implement the methods required by the
        payment service.
        """

        self._provider = provider

    def is_configured(self) -> bool:
        """Return whether a payment provider is configured."""

        return self._provider is not None

    def create_checkout(
        self,
        user_id: int,
    ) -> PaymentCheckout:
        """
        Create a checkout session.

        A real payment provider must be configured before this
        operation can be performed.
        """

        if self._provider is None:
            raise RuntimeError(
                "Payment provider is not configured."
            )

        checkout = self._provider.create_checkout(
            user_id=user_id,
        )

        return PaymentCheckout(
            checkout_id=checkout.checkout_id,
            checkout_url=checkout.checkout_url,
            status=PaymentStatus.PENDING,
        )

    def verify_event(
        self,
        payload: bytes,
        signature: str,
    ) -> PaymentEvent:
        """
        Verify and normalize a payment webhook event.

        The provider is responsible for cryptographic verification.
        """

        if self._provider is None:
            raise RuntimeError(
                "Payment provider is not configured."
            )

        event = self._provider.verify_event(
            payload=payload,
            signature=signature,
        )

        return PaymentEvent(
            event_id=event.event_id,
            user_id=event.user_id,
            status=event.status,
            amount=event.amount,
            currency=event.currency,
            provider=event.provider,
            raw_data=event.raw_data,
        )


payment_service = PaymentService()