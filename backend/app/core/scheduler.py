"""
Application scheduler.

Provides centralized scheduling for recurring background tasks.

Trading logic must not be implemented directly in this module.
Tasks are registered by the services that own them.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.config.settings import settings


AsyncTask = Callable[[], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    """Description of a registered scheduled task."""

    task_id: str
    name: str
    interval_seconds: int


class SchedulerManager:
    """
    Central scheduler for the application.

    The scheduler is intentionally independent from trading logic.
    Other services register their own asynchronous tasks here.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(
            timezone=settings.scheduler.timezone,
        )

        self._started = False

    @property
    def started(self) -> bool:
        """Return whether the scheduler is currently running."""
        return self._started

    def start(self) -> None:
        """Start the scheduler."""
        if self._started:
            logger.warning("Scheduler is already running.")
            return

        if not settings.scheduler.enabled:
            logger.info("Scheduler is disabled by configuration.")
            return

        self._scheduler.start()

        self._started = True

        logger.info("Scheduler started.")

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._started:
            return

        self._scheduler.shutdown(wait=True)

        self._started = False

        logger.info("Scheduler stopped.")

    def register_interval_task(
        self,
        *,
        task_id: str,
        name: str,
        task: AsyncTask,
        interval_seconds: int,
        replace_existing: bool = True,
    ) -> ScheduledTask:
        """
        Register an asynchronous task to execute at a fixed interval.

        Parameters
        ----------
        task_id:
            Unique identifier for the scheduled task.

        name:
            Human-readable task name.

        task:
            Asynchronous callable to execute.

        interval_seconds:
            Number of seconds between executions.

        replace_existing:
            Replace a previously registered task with the same ID.
        """
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero.")

        self._scheduler.add_job(
            task,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=task_id,
            name=name,
            replace_existing=replace_existing,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )

        logger.debug(
            "Scheduled task registered: {} (every {} seconds).",
            name,
            interval_seconds,
        )

        return ScheduledTask(
            task_id=task_id,
            name=name,
            interval_seconds=interval_seconds,
        )

    def remove_task(self, task_id: str) -> None:
        """Remove a scheduled task."""
        try:
            self._scheduler.remove_job(task_id)
        except Exception:
            logger.debug(
                "Scheduled task '{}' does not exist.",
                task_id,
            )
            return

        logger.debug(
            "Scheduled task removed: {}",
            task_id,
        )

    def has_task(self, task_id: str) -> bool:
        """Return whether a task is registered."""
        return self._scheduler.get_job(task_id) is not None

    def get_tasks(self) -> list[ScheduledTask]:
        """Return currently registered scheduled tasks."""
        return [
            ScheduledTask(
                task_id=job.id,
                name=job.name or job.id,
                interval_seconds=0,
            )
            for job in self._scheduler.get_jobs()
        ]


scheduler = SchedulerManager()