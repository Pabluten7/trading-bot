"""
Database health checks.

Provides lightweight checks to determine whether the configured database
is reachable.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import database


def check_database_connection() -> bool:
    """
    Check whether the database is reachable.

    Returns
    -------
    bool
        True when the database responds successfully, otherwise False.
    """
    if not database.is_initialized:
        database.initialize()

    try:
        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except SQLAlchemyError:
        return False