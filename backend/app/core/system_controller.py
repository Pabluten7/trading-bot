"""
System controller.

Coordinates the lifecycle of the Trading Bot application.
"""

from __future__ import annotations

from enum import StrEnum

from loguru import logger

from app.config.environment import validate_environment
from app.config.logging import configure_logging, shutdown_logging
from app.core.scheduler import scheduler
from app.data.manager import market_data_manager
from app.database.initializer import database_initializer


class SystemState(StrEnum):
    """Possible system lifecycle states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class SystemController:
    """
    Controls application startup and shutdown.

    This class coordinates infrastructure services but contains no
    trading logic.
    """

    def __init__(self) -> None:
        self._state = SystemState.STOPPED

    @property
    def state(self) -> SystemState:
        """Return the current system state."""

        return self._state

    @property
    def is_running(self) -> bool:
        """Return whether the system is currently running."""

        return self._state == SystemState.RUNNING

    async def startup(self) -> None:
        """Start all required application infrastructure."""

        if self._state == SystemState.RUNNING:
            logger.warning(
                "System is already running."
            )
            return

        if self._state == SystemState.STARTING:
            raise RuntimeError(
                "System startup is already in progress."
            )

        self._state = SystemState.STARTING

        try:
            validate_environment()

            configure_logging()

            logger.info(
                "Starting Trading Bot."
            )

            database_initializer.initialize()

            market_data_manager.initialize()

            scheduler.start()

            self._state = SystemState.RUNNING

            logger.info(
                "Trading Bot started successfully."
            )

        except Exception:
            self._state = SystemState.ERROR

            logger.exception(
                "Failed to start Trading Bot."
            )

            await self._cleanup_after_failed_startup()

            raise

    async def shutdown(self) -> None:
        """Stop all application infrastructure gracefully."""

        if self._state == SystemState.STOPPED:
            return

        if self._state == SystemState.STOPPING:
            return

        self._state = SystemState.STOPPING

        try:
            logger.info(
                "Stopping Trading Bot."
            )

            scheduler.stop()

            market_data_manager.shutdown()

            database_initializer.shutdown()

            self._state = SystemState.STOPPED

            logger.info(
                "Trading Bot stopped successfully."
            )

        finally:
            shutdown_logging()

    async def restart(self) -> None:
        """Restart the application."""

        logger.info(
            "Restarting Trading Bot."
        )

        await self.shutdown()
        await self.startup()

    async def _cleanup_after_failed_startup(self) -> None:
        """Release resources acquired before a failed startup."""

        try:
            scheduler.stop()

        except Exception:
            logger.exception(
                "Failed to stop scheduler after startup failure."
            )

        try:
            market_data_manager.shutdown()

        except Exception:
            logger.exception(
                "Failed to stop market-data manager "
                "after startup failure."
            )

        try:
            database_initializer.shutdown()

        except Exception:
            logger.exception(
                "Failed to close database after startup failure."
            )


system_controller = SystemController()