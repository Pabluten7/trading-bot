import pytest

from app.core.scheduler import scheduler
from app.core.system_controller import (
    SystemState,
    SystemController,
)


@pytest.mark.asyncio
async def test_system_controller_startup_and_shutdown():
    controller = SystemController()

    await controller.startup()

    assert controller.state == SystemState.RUNNING
    assert controller.is_running is True

    await controller.shutdown()

    assert controller.state == SystemState.STOPPED
    assert controller.is_running is False


def test_scheduler_initial_state():
    assert scheduler.started is False