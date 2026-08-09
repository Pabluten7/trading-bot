"""
Environment helpers.

Centralizes environment-specific behavior and validation.
"""

from __future__ import annotations

from enum import StrEnum

from app.config.settings import settings


class Environment(StrEnum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


def get_environment() -> Environment:
    """
    Return the current application environment.

    Raises
    ------
    ValueError
        If the configured environment is not supported.
    """
    try:
        return Environment(settings.app.environment.lower())
    except ValueError as exc:
        valid_environments = ", ".join(environment.value for environment in Environment)

        raise ValueError(
            f"Unsupported application environment "
            f"'{settings.app.environment}'. "
            f"Expected one of: {valid_environments}."
        ) from exc


def is_development() -> bool:
    """Return whether the application is running in development."""
    return get_environment() == Environment.DEVELOPMENT


def is_testing() -> bool:
    """Return whether the application is running in testing."""
    return get_environment() == Environment.TESTING


def is_production() -> bool:
    """Return whether the application is running in production."""
    return get_environment() == Environment.PRODUCTION


def validate_environment() -> None:
    """
    Validate environment-specific production requirements.

    Production must never run with debug mode enabled.
    """
    environment = get_environment()

    if environment == Environment.PRODUCTION and settings.app.debug:
        raise RuntimeError(
            "APP_DEBUG cannot be enabled in production."
        )