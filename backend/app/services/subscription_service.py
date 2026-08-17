"""
Subscription service.

Controls the user's subscription status.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Subscription
from app.database.models.enums import SubscriptionStatus


class SubscriptionService:
    """Business logic for user subscriptions."""

    def get_by_user_id(
        self,
        session: Session,
        user_id: int,
    ) -> Subscription | None:
        """Return the subscription belonging to a user."""

        return session.scalar(
            select(Subscription).where(
                Subscription.user_id == user_id
            )
        )

    def create(
        self,
        session: Session,
        user_id: int,
    ) -> Subscription:
        """
        Create an inactive subscription for a user.

        A subscription is created separately from payment activation.
        """

        existing = self.get_by_user_id(
            session,
            user_id,
        )

        if existing is not None:
            raise ValueError(
                "User already has a subscription."
            )

        subscription = Subscription(
            user_id=user_id,
            status=SubscriptionStatus.INACTIVE.value,
        )

        session.add(subscription)
        session.commit()
        session.refresh(subscription)

        return subscription

    def is_active(
        self,
        session: Session,
        user_id: int,
    ) -> bool:
        """
        Determine whether the user's subscription grants access.

        A subscription must:
        1. Have ACTIVE status.
        2. Have a valid current period.
        3. Not have passed its current period end.
        """

        subscription = self.get_by_user_id(
            session,
            user_id,
        )

        if subscription is None:
            return False

        if subscription.status != SubscriptionStatus.ACTIVE.value:
            return False

        now = datetime.now(timezone.utc)

        if (
            subscription.current_period_end is not None
            and subscription.current_period_end <= now
        ):
            return False

        return True

    def activate(
        self,
        session: Session,
        subscription: Subscription,
        period_start: datetime,
        period_end: datetime,
    ) -> Subscription:
        """Activate or renew a subscription."""

        if period_end <= period_start:
            raise ValueError(
                "Subscription period end must be after "
                "period start."
            )

        subscription.status = (
            SubscriptionStatus.ACTIVE.value
        )

        if subscription.started_at is None:
            subscription.started_at = period_start

        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.cancelled_at = None

        session.add(subscription)
        session.commit()
        session.refresh(subscription)

        return subscription

    def mark_past_due(
        self,
        session: Session,
        subscription: Subscription,
    ) -> Subscription:
        """Mark a subscription as past due."""

        subscription.status = (
            SubscriptionStatus.PAST_DUE.value
        )

        session.add(subscription)
        session.commit()
        session.refresh(subscription)

        return subscription

    def cancel(
        self,
        session: Session,
        subscription: Subscription,
    ) -> Subscription:
        """Cancel a subscription."""

        subscription.status = (
            SubscriptionStatus.CANCELLED.value
        )
        subscription.cancelled_at = (
            datetime.now(timezone.utc)
        )

        session.add(subscription)
        session.commit()
        session.refresh(subscription)

        return subscription


subscription_service = SubscriptionService()