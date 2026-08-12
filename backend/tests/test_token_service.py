from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config.settings import settings
from app.services.token_service import token_service


def test_create_access_token():
    token = token_service.create_access_token(123)

    assert isinstance(token, str)
    assert token


def test_decode_access_token():
    token = token_service.create_access_token(123)

    user_id = token_service.decode_access_token(token)

    assert user_id == 123


def test_token_contains_expected_claims():
    token = token_service.create_access_token(456)

    payload = jwt.decode(
        token,
        settings.security.jwt_secret_key,
        algorithms=[settings.security.jwt_algorithm],
    )

    assert payload["sub"] == "456"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_invalid_token_is_rejected():
    with pytest.raises(ValueError, match="Invalid access token"):
        token_service.decode_access_token(
            "this-is-not-a-valid-token"
        )


def test_tampered_token_is_rejected():
    token = token_service.create_access_token(123)

    tampered_token = token[:-1] + (
        "x" if token[-1] != "x" else "y"
    )

    with pytest.raises(ValueError, match="Invalid access token"):
        token_service.decode_access_token(
            tampered_token
        )


def test_wrong_token_type_is_rejected():
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "123",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "refresh",
        },
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )

    with pytest.raises(
        ValueError,
        match="Invalid token type",
    ):
        token_service.decode_access_token(token)


def test_missing_user_id_is_rejected():
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )

    with pytest.raises(
        ValueError,
        match="Token does not contain a user ID",
    ):
        token_service.decode_access_token(token)


def test_expired_token_is_rejected():
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "123",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
            "type": "access",
        },
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )

    with pytest.raises(ValueError, match="Invalid access token"):
        token_service.decode_access_token(token)