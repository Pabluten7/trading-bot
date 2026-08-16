"""
Authentication API schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    """Credentials submitted during login."""

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class TokenResponse(BaseModel):
    """Authentication token returned after login."""

    access_token: str

    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    """Public representation of the authenticated user."""

    id: int

    email: EmailStr

    is_active: bool


class RegisterResponse(BaseModel):
    """Response returned after successful registration."""

    id: int

    email: EmailStr

    is_active: bool

    message: str


class AccountStatusResponse(BaseModel):
    """Current commercial access state of the account."""

    user_active: bool

    subscription_active: bool

    subscription_status: str | None

    subscription_period_start: datetime | None

    subscription_period_end: datetime | None

    license_active: bool

    license_status: str | None

    license_expires_at: datetime | None

    access_allowed: bool

    access_reason: str