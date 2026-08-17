"""
Payment API routes.
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.schemas.payment import CheckoutResponse
from app.database.models import User
from app.services.payment_processing_service import (
    payment_processing_service,
)
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

    The actual payment provider implementation is configured
    independently from the API.
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


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
)
async def payment_webhook(
    request: Request,
    session: Session = Depends(get_db),
    payment_signature: str | None = Header(
        default=None,
        alias="X-Payment-Signature",
    ),
) -> dict[str, str]:
    """
    Receive and process a payment-provider webhook.

    The raw request body is passed to the configured payment provider
    so that its signature can be cryptographically verified before
    any account state is modified.
    """

    if not payment_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment signature.",
        )

    payload = await request.body()

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty webhook payload.",
        )

    try:
        event = payment_service.verify_event(
            payload=payload,
            signature=payment_signature,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment webhook.",
        ) from exc

    try:
        processed = payment_processing_service.process(
            session,
            event,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "status": (
            "processed"
            if processed
            else "already_processed"
        ),
    }