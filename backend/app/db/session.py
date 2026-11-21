"""Engine y sesiones de SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def make_engine(url: str | None = None) -> Engine:
    url = url or get_settings().database_url
    engine = create_engine(url, pool_pre_ping=True)
    if url.startswith("sqlite"):
        # SQLite no aplica claves foráneas salvo que se lo pidas.
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine()
        _SessionLocal = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición."""
    get_engine()
    assert _SessionLocal is not None
    with _SessionLocal() as session:
        yield session
