"""
Database migration helpers.

Alembic remains responsible for the actual schema migrations. This module
provides application-level helpers for checking migration state.
"""

from __future__ import annotations

from pathlib import Path

from app.config.settings import settings


MIGRATIONS_DIRECTORY = (
    settings.backend_directory / "migrations"
)


def migrations_directory() -> Path:
    """
    Return the absolute path to the Alembic migrations directory.
    """
    return MIGRATIONS_DIRECTORY


def migrations_directory_exists() -> bool:
    """Return whether the migrations directory exists."""
    return MIGRATIONS_DIRECTORY.is_dir()