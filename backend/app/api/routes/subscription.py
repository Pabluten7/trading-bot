"""
Subscription API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.schemas.subscription import (
    SubscriptionCancelResponse,
    SubscriptionStatusResponse,
)
from app.database.models import User
from app.services.access_service import access_service
from app.services.subscription_service import (
    subscription_service,
)


router = APIRouter(
    prefix="/subscription",
    tags=["Subscription"],
)


@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
)
def get_subscription_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SubscriptionStatusResponse:
    """
    Return the current user's subscription status.
    """

    subscription = subscription_service.get_by_user_id(
        session,
        current_user.id,
    )

    access_result = access_service.check_access(
        session,
        current_user,
    )

    if subscription is None:
        return SubscriptionStatusResponse(
            exists=False,
            status=None,
            started_at=None,
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
            access_allowed=access_result.allowed,
            access_reason=access_result.reason,
        )

    return SubscriptionStatusResponse(
        exists=True,
        status=subscription.status,
        started_at=subscription.started_at,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=(
            getattr(
                subscription,
                "cancel_at_period_end",
                False,
            )
        ),
        access_allowed=access_result.allowed,
        access_reason=access_result.reason,
    )


@router.post(
    "/cancel",
    response_model=SubscriptionCancelResponse,
)
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SubscriptionCancelResponse:
    """
    Cancel the current user's subscription.

    The actual subscription remains active until the end of the
    current billing period when supported by the model.
    """

    subscription = subscription_service.get_by_user_id(
        session,
        current_user.id,
    )

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found.",
        )

    try:
        subscription_service.cancel(
            session,
            subscription,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SubscriptionCancelResponse(
        success=True,
        status=subscription.status,
        message="Subscription cancelled successfully.",
    )