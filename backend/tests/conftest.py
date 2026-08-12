from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.services.user_service import user_service


@pytest.fixture()
def db_session():
    """Create an isolated in-memory database for each test."""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def user(db_session):
    """Create a test user."""

    return user_service.create_user(
        db_session,
        "test@example.com",
        "StrongPassword123!",
    )