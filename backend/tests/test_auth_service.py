import pytest

from app.services.auth_service import auth_service
from app.services.user_service import user_service


def test_authenticate_returns_access_token(
    db_session,
):
    user = user_service.create_user(
        db_session,
        "auth@example.com",
        "StrongPassword123!",
    )

    token = auth_service.authenticate(
        db_session,
        user.email,
        "StrongPassword123!",
    )

    assert isinstance(token, str)
    assert token


def test_authenticate_rejects_wrong_password(
    db_session,
):
    user_service.create_user(
        db_session,
        "auth@example.com",
        "StrongPassword123!",
    )

    with pytest.raises(
        ValueError,
        match="Invalid credentials",
    ):
        auth_service.authenticate(
            db_session,
            "auth@example.com",
            "WrongPassword!",
        )


def test_authenticate_rejects_unknown_user(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Invalid credentials",
    ):
        auth_service.authenticate(
            db_session,
            "unknown@example.com",
            "StrongPassword123!",
        )


def test_authenticate_rejects_inactive_user(
    db_session,
):
    user = user_service.create_user(
        db_session,
        "inactive@example.com",
        "StrongPassword123!",
    )

    user.is_active = False
    db_session.commit()

    with pytest.raises(
        ValueError,
        match="User account is inactive",
    ):
        auth_service.authenticate(
            db_session,
            user.email,
            "StrongPassword123!",
        )


def test_get_user_from_token(
    db_session,
):
    user = user_service.create_user(
        db_session,
        "token@example.com",
        "StrongPassword123!",
    )

    token = auth_service.authenticate(
        db_session,
        user.email,
        "StrongPassword123!",
    )

    authenticated_user = (
        auth_service.get_user_from_token(
            db_session,
            token,
        )
    )

    assert authenticated_user.id == user.id
    assert authenticated_user.email == user.email


def test_get_user_from_invalid_token(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Invalid access token",
    ):
        auth_service.get_user_from_token(
            db_session,
            "invalid-token",
        )


def test_get_user_from_inactive_user(
    db_session,
):
    user = user_service.create_user(
        db_session,
        "inactive-token@example.com",
        "StrongPassword123!",
    )

    token = auth_service.authenticate(
        db_session,
        user.email,
        "StrongPassword123!",
    )

    user.is_active = False
    db_session.commit()

    with pytest.raises(
        ValueError,
        match="User account is inactive",
    ):
        auth_service.get_user_from_token(
            db_session,
            token,
        )