"""
User service.

Contains user-related business operations.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import User
from app.services.password_service import password_service


class UserService:
    """Business logic related to users."""

    def get_by_id(
        self,
        session: Session,
        user_id: int,
    ) -> User | None:
        """Return a user by ID."""
        return session.scalar(
            select(User).where(User.id == user_id)
        )

    def get_by_email(
        self,
        session: Session,
        email: str,
    ) -> User | None:
        """Return a user by email."""
        normalized_email = email.strip().lower()

        return session.scalar(
            select(User).where(
                User.email == normalized_email
            )
        )

    def create_user(
        self,
        session: Session,
        email: str,
        password: str,
    ) -> User:
        """
        Create a new user.

        Raises
        ------
        ValueError
            If the email is already registered.
        """
        normalized_email = email.strip().lower()

        if not normalized_email:
            raise ValueError("Email cannot be empty.")

        if self.get_by_email(
            session,
            normalized_email,
        ):
            raise ValueError(
                "A user with this email already exists."
            )

        user = User(
            email=normalized_email,
            password_hash=password_service.hash(password),
            is_active=True,
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        return user

    def verify_password(
        self,
        user: User,
        password: str,
    ) -> bool:
        """Verify a user's password."""
        return password_service.verify(
            password,
            user.password_hash,
        )


user_service = UserService()