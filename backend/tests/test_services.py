from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models import Subscription
from app.database.models.enums import SubscriptionStatus
from app.services.access_service import access_service
from app.services.license_service import license_service
from app.services.user_service import user_service


def test_user_creation(db_session):
    user = user_service.create_user(
        db_session,
        "USER@EXAMPLE.COM",
        "StrongPassword123!",
    )

    assert user.id is not None
    assert user.email == "user@example.com"
    assert user.is_active is True


def test_password_verification(db_session, user):
    assert user_service.verify_password(
        user,
        "StrongPassword123!",
    )

    assert not user_service.verify_password(
        user,
        "WrongPassword!",
    )


def test_inactive_subscription_denies_access(
    db_session,
    user,
):
    license_service.create(
        db_session,
        user.id,
    )

    result = access_service.check_access(
        db_session,
        user,
    )

    assert result.allowed is False
    assert result.reason == "subscription_inactive"


def test_active_subscription_without_license_denies_access(
    db_session,
    user,
):
    now = datetime.now(timezone.utc)

    subscription = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.ACTIVE.value,
        started_at=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )

    db_session.add(subscription)
    db_session.commit()

    result = access_service.check_access(
        db_session,
        user,
    )

    assert result.allowed is False
    assert result.reason == "license_inactive"


def test_active_subscription_and_license_grant_access(
    db_session,
    user,
):
    now = datetime.now(timezone.utc)

    subscription = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.ACTIVE.value,
        started_at=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )

    db_session.add(subscription)
    db_session.commit()

    license_record, _ = license_service.create(
        db_session,
        user.id,
    )

    license_service.activate(
        db_session,
        license_record,
        expires_at=now + timedelta(days=30),
    )

    result = access_service.check_access(
        db_session,
        user,
    )

    assert result.allowed is True
    assert result.reason == "access_granted"


def test_expired_subscription_denies_access(
    db_session,
    user,
):
    now = datetime.now(timezone.utc)

    subscription = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.ACTIVE.value,
        started_at=now - timedelta(days=60),
        current_period_start=now - timedelta(days=30),
        current_period_end=now - timedelta(seconds=1),
    )

    db_session.add(subscription)
    db_session.commit()

    license_record, _ = license_service.create(
        db_session,
        user.id,
    )

    license_service.activate(
        db_session,
        license_record,
        expires_at=now + timedelta(days=30),
    )

    result = access_service.check_access(
        db_session,
        user,
    )

    assert result.allowed is False
    assert result.reason == "subscription_inactive"


def test_revoked_license_denies_access(
    db_session,
    user,
):
    now = datetime.now(timezone.utc)

    subscription = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.ACTIVE.value,
        started_at=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )

    db_session.add(subscription)
    db_session.commit()

    license_record, _ = license_service.create(
        db_session,
        user.id,
    )

    license_service.activate(
        db_session,
        license_record,
        expires_at=now + timedelta(days=30),
    )

    license_service.revoke(
        db_session,
        license_record,
    )

    result = access_service.check_access(
        db_session,
        user,
    )

    assert result.allowed is False
    assert result.reason == "license_inactive"


def test_inactive_user_denies_access(
    db_session,
    user,
):
    user.is_active = False
    db_session.commit()

    result = access_service.check_access(
        db_session,
        user,
    )

    assert result.allowed is False
    assert result.reason == "user_inactive"