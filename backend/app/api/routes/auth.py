"""
Authentication API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.schemas.auth import (
    AccountStatusResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.database.models import User
from app.services.access_service import access_service
from app.services.auth_service import auth_service
from app.services.license_service import license_service
from app.services.subscription_service import (
    subscription_service,
)
from app.services.user_service import user_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    session: Session = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new user account.

    A new account starts without an active subscription.
    An inactive license is provisioned for the account and will
    become active when the commercial subscription is activated.
    """

    try:
        user = user_service.create_user(
            session,
            request.email,
            request.password,
        )

        license_service.create(
            session,
            user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RegisterResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        message="User registered successfully.",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    session: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and return an access token.
    """

    try:
        access_token = auth_service.authenticate(
            session,
            request.email,
            request.password,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "User account is inactive.":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        ) from exc

    return TokenResponse(
        access_token=access_token,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """
    Return the currently authenticated user.
    """

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
    )


@router.get(
    "/account-status",
    response_model=AccountStatusResponse,
)
def get_account_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AccountStatusResponse:
    """
    Return the complete commercial access state of the account.
    """

    subscription = subscription_service.get_by_user_id(
        session,
        current_user.id,
    )

    license_record = license_service.get_by_user_id(
        session,
        current_user.id,
    )

    access_result = access_service.check_access(
        session,
        current_user,
    )

    subscription_active = (
        subscription_service.is_active(
            session,
            current_user.id,
        )
    )

    license_active = (
        license_service.is_active(
            session,
            current_user.id,
        )
    )

    return AccountStatusResponse(
        user_active=current_user.is_active,
        subscription_active=subscription_active,
        subscription_status=(
            subscription.status
            if subscription is not None
            else None
        ),
        subscription_period_start=(
            subscription.current_period_start
            if subscription is not None
            else None
        ),
        subscription_period_end=(
            subscription.current_period_end
            if subscription is not None
            else None
        ),
        license_active=license_active,
        license_status=(
            license_record.status
            if license_record is not None
            else None
        ),
        license_expires_at=(
            license_record.expires_at
            if license_record is not None
            else None
        ),
        access_allowed=access_result.allowed,
        access_reason=access_result.reason,
    )