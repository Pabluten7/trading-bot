"""
Access control service.

Centralizes all checks required before allowing a user to access the bot.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.models import User
from app.services.license_service import license_service
from app.services.subscription_service import subscription_service


@dataclass(frozen=True, slots=True)
class AccessResult:
    """Result of an access validation."""

    allowed: bool
    reason: str


class AccessService:
    """
    Determines whether a user is allowed to use the Trading Bot.

    Access requires:
    - an active user account;
    - an active subscription;
    - an active, non-expired license.
    """

    def check_access(
        self,
        session: Session,
        user: User,
    ) -> AccessResult:
        """Check whether the user can access the bot."""

        if not user.is_active:
            return AccessResult(
                allowed=False,
                reason="user_inactive",
            )

        if not subscription_service.is_active(
            session,
            user.id,
        ):
            return AccessResult(
                allowed=False,
                reason="subscription_inactive",
            )

        if not license_service.is_active(
            session,
            user.id,
        ):
            return AccessResult(
                allowed=False,
                reason="license_inactive",
            )

        return AccessResult(
            allowed=True,
            reason="access_granted",
        )


access_service = AccessService()