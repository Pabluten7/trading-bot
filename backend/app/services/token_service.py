"""
JWT token service.

Handles creation and validation of authentication tokens.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config.settings import settings


class TokenService:
    """Creates and validates JWT access tokens."""

    def __init__(self) -> None:
        self._algorithm = settings.security.jwt_algorithm
        self._secret_key = settings.security.jwt_secret_key
        self._expiration_minutes = (
            settings.security.access_token_expire_minutes
        )

    def create_access_token(
        self,
        user_id: int,
    ) -> str:
        """Create an access token for a user."""

        now = datetime.now(timezone.utc)

        expires_at = now + timedelta(
            minutes=self._expiration_minutes
        )

        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": expires_at,
            "type": "access",
        }

        return jwt.encode(
            payload,
            self._secret_key,
            algorithm=self._algorithm,
        )

    def decode_access_token(
        self,
        token: str,
    ) -> int:
        """
        Validate an access token and return its user ID.

        Raises
        ------
        ValueError
            If the token is invalid, expired, or does not represent
            an access token.
        """

        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
        except jwt.PyJWTError as exc:
            raise ValueError(
                "Invalid access token."
            ) from exc

        if payload.get("type") != "access":
            raise ValueError(
                "Invalid token type."
            )

        subject = payload.get("sub")

        if subject is None:
            raise ValueError(
                "Token does not contain a user ID."
            )

        try:
            return int(subject)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Invalid user ID in token."
            ) from exc


token_service = TokenService()