import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_valores_por_defecto():
    s = Settings(_env_file=None)
    assert s.app_env == "development"
    assert s.database_url.startswith("sqlite")
    assert s.alpaca_paper is True


def test_lee_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALPACA_API_KEY", "abc")
    s = Settings(_env_file=None)
    assert s.app_env == "test"
    assert s.alpaca_api_key.get_secret_value() == "abc"


def test_los_secretos_no_salen_en_el_repr():
    s = Settings(_env_file=None, alpaca_api_secret="muy-secreto")
    assert "muy-secreto" not in repr(s)


def test_entorno_invalido_falla():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="staging")


def test_produccion_no_admite_sqlite():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", database_url="sqlite:///x.db")


def test_produccion_con_postgres_ok():
    s = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql+psycopg://u:p@db:5432/bot",
    )
    assert s.app_env == "production"
