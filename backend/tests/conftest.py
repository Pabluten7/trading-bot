"""
Fixtures globales de pytest para el Trading Bot.
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import engine
from app.db.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Reutiliza el mismo event loop para todos los tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Crea todas las tablas antes de los tests y las elimina al terminar."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Cliente HTTP async para tests de endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
