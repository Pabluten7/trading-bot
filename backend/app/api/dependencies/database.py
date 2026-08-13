"""
Database dependencies for API routes.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.connection import database


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for an API request.
    """

    session = database.get_session()

    try:
        yield session
    finally:
        session.close()