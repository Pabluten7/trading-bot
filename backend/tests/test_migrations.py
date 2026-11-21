from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from alembic import command

BACKEND = Path(__file__).resolve().parents[1]


def _cfg(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_migraciones_suben_y_bajan(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = _cfg(url)
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"strategies", "signals", "trades", "orders"} <= tables
    command.downgrade(cfg, "base")
    assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}


def test_los_modelos_coinciden_con_las_migraciones(tmp_path):
    """Si cambias un modelo sin crear migración, este test falla."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    from app.db.models import Base

    url = f"sqlite:///{tmp_path / 'd.db'}"
    command.upgrade(_cfg(url), "head")
    with create_engine(url).connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_una_sola_cabeza_de_migraciones():
    assert len(ScriptDirectory(str(BACKEND / "alembic")).get_heads()) == 1
