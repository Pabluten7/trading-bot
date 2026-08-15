"""
Authentication API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from app.database.models import User
from app.services.auth_service import auth_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
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