"""
Payment API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.schemas.payment import CheckoutResponse
from app.database.models import User
from app.services.payment_service import payment_service


router = APIRouter(
    prefix="/payment",
    tags=["Payment"],
)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
)
def create_checkout(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CheckoutResponse:
    """
    Create the payment checkout session for the current user.

    The actual provider implementation will be connected later.
    """

    del session

    try:
        checkout = payment_service.create_checkout(
            current_user.id,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return CheckoutResponse(
        checkout_id=checkout.checkout_id,
        checkout_url=checkout.checkout_url,
        status=checkout.status.value,
    )