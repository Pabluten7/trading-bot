"""
Database connection management.

Creates and manages the SQLAlchemy database engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.settings import settings


class Database:
    """
    Database engine manager.

    The implementation supports SQLite during development and can later
    use PostgreSQL simply by changing the configured database URL.
    """

    def __init__(self) -> None:
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        """
        Return the initialized SQLAlchemy engine.

        Raises
        ------
        RuntimeError
            If the database has not been initialized.
        """
        if self._engine is None:
            raise RuntimeError(
                "Database has not been initialized."
            )

        return self._engine

    @property
    def is_initialized(self) -> bool:
        """Return whether the database engine exists."""
        return self._engine is not None

    def initialize(self) -> None:
        """Initialize the SQLAlchemy engine and session factory."""

        if self._engine is not None:
            return

        database_url = settings.database.url

        self._prepare_sqlite_directory(database_url)

        connect_args: dict[str, Any] = {}

        engine_kwargs: dict[str, Any] = {
            "echo": settings.database.echo,
            "future": True,
        }

        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            engine_kwargs["connect_args"] = connect_args

            if ":memory:" in database_url:
                engine_kwargs["poolclass"] = StaticPool

        self._engine = create_engine(
            database_url,
            **engine_kwargs,
        )

        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def get_session(self) -> Session:
        """
        Create and return a new database session.

        Raises
        ------
        RuntimeError
            If the database has not been initialized.
        """

        if self._session_factory is None:
            raise RuntimeError(
                "Database has not been initialized."
            )

        return self._session_factory()

    def dispose(self) -> None:
        """Dispose the database engine and release connections."""

        if self._engine is None:
            return

        self._engine.dispose()

        self._engine = None
        self._session_factory = None

    @staticmethod
    def _prepare_sqlite_directory(database_url: str) -> None:
        """
        Create the parent directory for a SQLite database if necessary.
        """

        prefix = "sqlite:///"

        if not database_url.startswith(prefix):
            return

        database_path = database_url[len(prefix):]

        if database_path == ":memory:":
            return

        path = Path(database_path)

        if not path.is_absolute():
            path = settings.backend_directory / path

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


database = Database()