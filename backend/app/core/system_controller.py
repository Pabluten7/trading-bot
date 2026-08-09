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

    This class does not contain trading logic.
    Its responsibility is to coordinate application-level services.
    """

    def __init__(self) -> None:
        self._state = SystemState.STOPPED

    @property
    def state(self) -> SystemState:
        """Return the current system state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return whether the system is running."""
        return self._state == SystemState.RUNNING

    async def startup(self) -> None:
        """
        Start the application.

        Startup failures move the system into ERROR state and are
        propagated to the caller.
        """
        if self._state == SystemState.RUNNING:
            logger.warning("System is already running.")
            return

        if self._state == SystemState.STARTING:
            raise RuntimeError("System startup is already in progress.")

        self._state = SystemState.STARTING

        try:
            # Validate configuration before starting services.
            validate_environment()

            # Logging must be available before starting the rest
            # of the application.
            configure_logging()

            logger.info("Starting Trading Bot.")

            # Scheduler is started only after configuration has been
            # validated and logging is ready.
            scheduler.start()

            self._state = SystemState.RUNNING

            logger.info("Trading Bot started successfully.")

        except Exception:
            self._state = SystemState.ERROR

            # Re-raise so the application entry point can terminate
            # with a non-zero exit code.
            raise

    async def shutdown(self) -> None:
        """
        Stop the application gracefully.
        """
        if self._state == SystemState.STOPPED:
            return

        if self._state == SystemState.STOPPING:
            return

        self._state = SystemState.STOPPING

        try:
            logger.info("Stopping Trading Bot.")

            scheduler.stop()

            self._state = SystemState.STOPPED

            logger.info("Trading Bot stopped successfully.")

        finally:
            shutdown_logging()

    async def restart(self) -> None:
        """Restart the application."""
        logger.info("Restarting Trading Bot.")

        await self.shutdown()
        await self.startup()


system_controller = SystemController()