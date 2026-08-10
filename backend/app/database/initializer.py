"""
Database initialization.

Responsible for preparing the database infrastructure during application
startup.
"""

from __future__ import annotations

from loguru import logger

from app.database.connection import database
from app.database.health import check_database_connection
from app.database.session import initialize_session_factory


class DatabaseInitializer:
    """Coordinates database initialization."""

    def __init__(self) -> None:
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Return whether database initialization completed."""
        return self._initialized

    def initialize(self) -> None:
        """
        Initialize the database infrastructure.

        This does not create application tables. Schema creation and
        migrations are handled separately by Alembic.
        """
        if self._initialized:
            return

        logger.info("Initializing database.")

        database.initialize()
        initialize_session_factory()

        if not check_database_connection():
            raise RuntimeError(
                "Database connection check failed."
            )

        self._initialized = True

        logger.info("Database initialized successfully.")

    def shutdown(self) -> None:
        """Release database resources."""

        if not self._initialized:
            return

        logger.info("Closing database connection.")

        database.dispose()

        self._initialized = False

        logger.info("Database connection closed.")


database_initializer = DatabaseInitializer()