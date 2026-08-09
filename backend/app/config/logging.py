"""
Application logging configuration.

This module centralizes the logging system used by the backend.

The application uses Loguru for structured, readable and rotating logs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from loguru import logger

from app.config.settings import settings


DEFAULT_LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:"
    "<cyan>{function}</cyan>:"
    "<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


class LoggingManager:
    """
    Configure and manage application logging.

    The manager is intentionally isolated from the rest of the application
    so the logging implementation can be changed later without modifying
    business logic.
    """

    def __init__(self) -> None:
        self._configured = False

    @property
    def configured(self) -> bool:
        """Return whether the logging system has been configured."""
        return self._configured

    def configure(self) -> None:
        """
        Configure application logging.

        Existing Loguru handlers are removed before the application handlers
        are registered. This prevents duplicated log messages when the
        application is reloaded during development.
        """
        if self._configured:
            return

        log_directory = settings.log_directory
        log_directory.mkdir(parents=True, exist_ok=True)

        logger.remove()

        self._configure_console()
        self._configure_file(log_directory)

        self._configured = True

        logger.debug("Logging system configured.")

    def _configure_console(self) -> None:
        """Configure console logging."""

        logger.add(
            sys.stderr,
            level=settings.logging.level,
            format=DEFAULT_LOG_FORMAT,
            colorize=True,
            enqueue=True,
            backtrace=settings.app.debug,
            diagnose=settings.app.debug,
        )

    def _configure_file(self, log_directory: Path) -> None:
        """Configure persistent rotating file logging."""

        log_file = log_directory / settings.logging.filename

        logger.add(
            log_file,
            level=settings.logging.level,
            format=DEFAULT_LOG_FORMAT,
            rotation=settings.logging.rotation,
            retention=settings.logging.retention,
            compression="zip",
            encoding="utf-8",
            enqueue=True,
            backtrace=settings.app.debug,
            diagnose=settings.app.debug,
        )

    def shutdown(self) -> None:
        """
        Flush and remove application logging handlers.

        This should be called during an orderly application shutdown.
        """
        if not self._configured:
            return

        logger.info("Shutting down logging system.")

        logger.complete()
        logger.remove()

        self._configured = False


logging_manager = LoggingManager()


def configure_logging() -> None:
    """Configure the global application logger."""
    logging_manager.configure()


def shutdown_logging() -> None:
    """Shutdown the global application logger."""
    logging_manager.shutdown()