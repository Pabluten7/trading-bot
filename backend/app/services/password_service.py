"""
Password hashing and verification service.
"""

from __future__ import annotations

from pwdlib import PasswordHash


class PasswordService:
    """Handles secure password hashing and verification."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        """
        Hash a password.

        Parameters
        ----------
        password:
            Plain-text password supplied by the user.
        """
        if not password:
            raise ValueError("Password cannot be empty.")

        return self._password_hash.hash(password)

    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        """
        Verify a plain-text password against its stored hash.
        """
        if not password or not password_hash:
            return False

        return self._password_hash.verify(
            password,
            password_hash,
        )


password_service = PasswordService()