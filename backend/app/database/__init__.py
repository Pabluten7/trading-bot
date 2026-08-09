"""
Database package.

Provides database connectivity, session management and persistence
infrastructure for the Trading Bot.
"""

from app.database.connection import database
from app.database.session import get_db_session

__all__ = [
    "database",
    "get_db_session",
]