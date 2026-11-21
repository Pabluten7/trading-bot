"""Configuración de la aplicación, leída de variables de entorno / `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # En local: SQLite (sin instalar nada). En Docker/producción: Postgres.
    database_url: str = "sqlite:///./trading_bot.db"

    # Alpaca. Se usa a partir de la HU-04.
    alpaca_api_key: SecretStr = SecretStr("")
    alpaca_api_secret: SecretStr = SecretStr("")
    alpaca_paper: bool = True
    # sip = todo el mercado (en plan gratis solo con datos de >15 min); iex = solo la bolsa IEX
    alpaca_feed: Literal["sip", "iex"] = "sip"
    alpaca_data_url: str = "https://data.alpaca.markets"

    @model_validator(mode="after")
    def _produccion_exige_postgres(self) -> "Settings":
        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("En producción DATABASE_URL debe apuntar a Postgres, no a SQLite")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
