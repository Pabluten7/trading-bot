"""
Authentication service.

Coordinates user credential verification and JWT creation.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.token_service import token_service
from app.services.user_service import user_service


class AuthService:
    """Application authentication logic."""

    def authenticate(
        self,
        session: Session,
        email: str,
        password: str,
    ) -> str:
        """
        Authenticate a user and return an access token.

        Raises
        ------
        ValueError
            If the user does not exist, is inactive, or the password
            is incorrect.
        """

        user = user_service.get_by_email(
            session,
            email,
        )

        if user is None:
            raise ValueError(
                "Invalid credentials."
            )

        if not user.is_active:
            raise ValueError(
                "User account is inactive."
            )

        if not user_service.verify_password(
            user,
            password,
        ):
            raise ValueError(
                "Invalid credentials."
            )

        return token_service.create_access_token(
            user.id
        )

    def get_user_from_token(
        self,
        session: Session,
        token: str,
    ):
        """
        Validate a token and return the corresponding user.

        Raises
        ------
        ValueError
            If the token is invalid or the user no longer exists.
        """

        user_id = token_service.decode_access_token(
            token
        )

        user = user_service.get_by_id(
            session,
            user_id,
        )

        if user is None:
            raise ValueError(
                "User not found."
            )

        if not user.is_active:
            raise ValueError(
                "User account is inactive."
            )

        return user


auth_service = AuthService()