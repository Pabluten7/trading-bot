"""
License service.

Validates and manages software licenses.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import License
from app.database.models.enums import LicenseStatus


class LicenseService:
    """Business logic for software licenses."""

    @staticmethod
    def _hash_license_key(
        license_key: str,
    ) -> str:
        """Create a one-way hash of a license key."""

        return hashlib.sha256(
            license_key.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _normalize_datetime(
        value: datetime,
    ) -> datetime:
        """
        Normalize a datetime to timezone-aware UTC.

        SQLite may return naive datetimes even when the SQLAlchemy
        column is configured with timezone=True.
        """

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(timezone.utc)

    @classmethod
    def _is_expired(
        cls,
        expires_at: datetime | None,
    ) -> bool:
        """Determine whether a license expiration date has passed."""

        if expires_at is None:
            return False

        expires_at = cls._normalize_datetime(
            expires_at
        )

        now = datetime.now(timezone.utc)

        return expires_at <= now

    @staticmethod
    def generate_license_key() -> str:
        """Generate a new random license key."""

        raw_key = secrets.token_urlsafe(32)

        return f"TB-{raw_key}"

    def get_by_user_id(
        self,
        session: Session,
        user_id: int,
    ) -> License | None:
        """Return a user's license."""

        return session.scalar(
            select(License).where(
                License.user_id == user_id
            )
        )

    def create(
        self,
        session: Session,
        user_id: int,
    ) -> tuple[License, str]:
        """
        Create a license.

        Returns
        -------
        tuple[License, str]
            The database license and the plain license key.

        The plain key is returned only at creation time.
        """

        existing_license = self.get_by_user_id(
            session,
            user_id,
        )

        if existing_license is not None:
            raise ValueError(
                "User already has a license."
            )

        plain_key = self.generate_license_key()

        license_record = License(
            user_id=user_id,
            license_key_hash=self._hash_license_key(
                plain_key
            ),
            status=LicenseStatus.INACTIVE.value,
        )

        session.add(license_record)
        session.commit()
        session.refresh(license_record)

        return license_record, plain_key

    def is_active(
        self,
        session: Session,
        user_id: int,
    ) -> bool:
        """Determine whether a user's license is currently valid."""

        license_record = self.get_by_user_id(
            session,
            user_id,
        )

        if license_record is None:
            return False

        if license_record.status != LicenseStatus.ACTIVE.value:
            return False

        if self._is_expired(
            license_record.expires_at
        ):
            return False

        return True

    def activate(
        self,
        session: Session,
        license_record: License,
        expires_at: datetime | None = None,
    ) -> License:
        """Activate a license."""

        license_record.status = (
            LicenseStatus.ACTIVE.value
        )

        license_record.activated_at = datetime.now(
            timezone.utc
        )

        license_record.expires_at = expires_at

        session.add(license_record)
        session.commit()
        session.refresh(license_record)

        return license_record

    def activate_for_subscription_period(
        self,
        session: Session,
        user_id: int,
        expires_at: datetime,
    ) -> License:
        """
        Activate or renew the license associated with a subscription.

        A user must have a license before it can be activated.
        If no license exists, one is created automatically.
        """

        expires_at = self._normalize_datetime(
            expires_at
        )

        license_record = self.get_by_user_id(
            session,
            user_id,
        )

        if license_record is None:
            license_record, _ = self.create(
                session,
                user_id,
            )

        return self.activate(
            session,
            license_record,
            expires_at=expires_at,
        )

    def expire(
        self,
        session: Session,
        license_record: License,
    ) -> License:
        """Mark a license as expired."""

        license_record.status = (
            LicenseStatus.EXPIRED.value
        )

        session.add(license_record)
        session.commit()
        session.refresh(license_record)

        return license_record

    def suspend(
        self,
        session: Session,
        license_record: License,
    ) -> License:
        """Suspend a license."""

        license_record.status = (
            LicenseStatus.SUSPENDED.value
        )

        session.add(license_record)
        session.commit()
        session.refresh(license_record)

        return license_record

    def revoke(
        self,
        session: Session,
        license_record: License,
    ) -> License:
        """Revoke a license."""

        license_record.status = (
            LicenseStatus.REVOKED.value
        )

        session.add(license_record)
        session.commit()
        session.refresh(license_record)

        return license_record


license_service = LicenseService()