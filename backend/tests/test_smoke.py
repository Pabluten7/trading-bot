"""
Tests de humo — Sprint 0.
Verifican que la aplicación arranca y la DB responde.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.db.session import AsyncSessionLocal


# ── Health endpoint ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["mode"] in ("paper", "live")


# ── Conexión a la base de datos ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_database_connection():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
    assert value == 1


# ── Tablas existen ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_tables_exist():
    expected_tables = [
        "candles", "signals", "trades",
        "positions", "portfolio_snapshots", "strategy_config",
    ]
    async with AsyncSessionLocal() as session:
        for table in expected_tables:
            result = await session.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = :table)"
                ),
                {"table": table},
            )
            exists = result.scalar()
            assert exists, f"Tabla '{table}' no encontrada en la base de datos"
