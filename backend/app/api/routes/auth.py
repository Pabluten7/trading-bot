"""
Authentication API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from app.database.connection import database
from app.services.auth_service import auth_service


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def get_db() -> Session:
    """
    Provide a database session for API requests.

    The session is always closed after the request finishes.
    """

    session = database.get_session()

    try:
        yield session
    finally:
        session.close()


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