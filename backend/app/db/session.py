"""
Gestión de sesiones de base de datos con SQLAlchemy 2.0 async.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import logger

# ── Motor async ───────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=(settings.APP_ENV == "development"),
)

# ── Fábrica de sesiones ───────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Verifica la conexión a la base de datos al iniciar la app."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: c.execute(__import__("sqlalchemy").text("SELECT 1")))
        logger.info("db.connected", url=settings.DATABASE_URL.split("@")[-1])
    except Exception as e:
        logger.error("db.connection_failed", error=str(e))
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency de FastAPI que provee una sesión de base de datos.

    Uso:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
