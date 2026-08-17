"""
Payment processing service.

Converts verified payment events into subscription and license
state changes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.models import Subscription
from app.database.models.enums import SubscriptionStatus
from app.services.license_service import license_service
from app.services.payment_event_service import payment_event_service
from app.services.payment_service import (
    PaymentEvent,
    PaymentStatus,
)
from app.services.subscription_service import (
    subscription_service,
)


class PaymentProcessingService:
    """Process verified payment events."""

    SUBSCRIPTION_PERIOD_DAYS = 30

    def process(
        self,
        session: Session,
        event: PaymentEvent,
    ) -> bool:
        """
        Process a normalized payment event.

        Returns:
            True when the event was newly processed.
            False when the event had already been processed.
        """

        payment_record, created = (
            payment_event_service.create(
                session,
                event,
            )
        )

        if not created:
            return False

        try:
            if event.status == PaymentStatus.COMPLETED:
                self._activate_subscription(
                    session,
                    event.user_id,
                )

            elif event.status == PaymentStatus.FAILED:
                self._mark_payment_failure(
                    session,
                    event.user_id,
                )

            payment_event_service.mark_processed(
                session,
                payment_record,
            )

        except Exception:
            session.rollback()
            raise

        return True

    def _activate_subscription(
        self,
        session: Session,
        user_id: int,
    ) -> None:
        """Activate or renew the user's subscription."""

        now = datetime.now(timezone.utc)

        period_end = now + timedelta(
            days=self.SUBSCRIPTION_PERIOD_DAYS,
        )

        subscription = subscription_service.get_by_user_id(
            session,
            user_id,
        )

        if subscription is None:
            subscription = subscription_service.create(
                session,
                user_id,
            )

        subscription_service.activate(
            session,
            subscription,
            period_start=now,
            period_end=period_end,
        )

        license_service.activate_for_subscription_period(
            session,
            user_id,
            expires_at=period_end,
        )

    def _mark_payment_failure(
        self,
        session: Session,
        user_id: int,
    ) -> None:
        """Mark an existing subscription as past due."""

        subscription = subscription_service.get_by_user_id(
            session,
            user_id,
        )

        if subscription is None:
            return

        subscription_service.mark_past_due(
            session,
            subscription,
        )


payment_processing_service = PaymentProcessingService()