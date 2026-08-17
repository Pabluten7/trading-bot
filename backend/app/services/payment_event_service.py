"""
Payment event processing service.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import PaymentEvent
from app.services.payment_service import PaymentEvent as NormalizedPaymentEvent


class PaymentEventService:
    """Manage persisted payment-provider events."""

    def get_by_provider_event_id(
        self,
        session: Session,
        provider: str,
        event_id: str,
    ) -> PaymentEvent | None:
        """Return an existing payment event."""

        statement = select(PaymentEvent).where(
            PaymentEvent.provider == provider,
            PaymentEvent.event_id == event_id,
        )

        return session.execute(statement).scalar_one_or_none()

    def create(
        self,
        session: Session,
        event: NormalizedPaymentEvent,
    ) -> tuple[PaymentEvent, bool]:
        """
        Persist an event.

        Returns:
            tuple[event, created]

        `created` is False when the event already exists.
        """

        existing = self.get_by_provider_event_id(
            session,
            event.provider,
            event.event_id,
        )

        if existing is not None:
            return existing, False

        record = PaymentEvent(
            provider=event.provider,
            event_id=event.event_id,
            user_id=event.user_id,
            status=event.status.value,
            amount=event.amount,
            currency=event.currency,
            raw_data=json.dumps(
                event.raw_data,
                default=str,
            ),
        )

        session.add(record)

        try:
            session.commit()

        except IntegrityError:
            session.rollback()

            existing = self.get_by_provider_event_id(
                session,
                event.provider,
                event.event_id,
            )

            if existing is None:
                raise

            return existing, False

        session.refresh(record)

        return record, True

    def mark_processed(
        self,
        session: Session,
        event: PaymentEvent,
    ) -> PaymentEvent:
        """Mark an event as successfully processed."""

        event.processed_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(event)

        return event


payment_event_service = PaymentEventService()