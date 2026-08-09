"""
Application startup compatibility layer.

The SystemController owns the actual application lifecycle.
This module provides a simple startup interface for the entry point
and for future application runners.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.system_controller import (
    SystemController,
    SystemState,
    system_controller,
)


@dataclass(frozen=True, slots=True)
class StartupStatus:
    """Result of the application startup process."""

    completed: bool
    state: SystemState


class StartupManager:
    """
    Compatibility facade for application startup.

    The manager deliberately remains small. Lifecycle logic belongs to
    SystemController.
    """

    def __init__(
        self,
        controller: SystemController = system_controller,
    ) -> None:
        self._controller = controller

    async def initialize(self) -> StartupStatus:
        """
        Initialize the application.

        Returns
        -------
        StartupStatus
            Current startup state.
        """
        await self._controller.startup()

        return StartupStatus(
            completed=self._controller.state == SystemState.RUNNING,
            state=self._controller.state,
        )

    async def shutdown(self) -> None:
        """Shutdown the application."""
        await self._controller.shutdown()


startup_manager = StartupManager()