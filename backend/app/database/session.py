"""
Database session management.

Provides SQLAlchemy sessions for application services and API endpoints.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import database


SessionFactory = sessionmaker(
    bind=None,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def initialize_session_factory() -> None:
    """Bind the session factory to the initialized database engine."""

    if not database.is_initialized:
        database.initialize()

    SessionFactory.configure(
        bind=database.engine,
    )


def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a database session.

    The session is automatically closed when the caller finishes using it.

    This function is also suitable for dependency injection in FastAPI.
    """

    if SessionFactory.kw.get("bind") is None:
        initialize_session_factory()

    session = SessionFactory()

    try:
        yield session

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()