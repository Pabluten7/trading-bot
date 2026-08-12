"""
Authentication API schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


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