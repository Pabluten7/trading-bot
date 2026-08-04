"""
settings.py
===========

Configuración centralizada del Trading Bot.

Este módulo es el único punto desde el que debe leerse la configuración
global del sistema.

Toda la configuración proviene de variables de entorno (.env) y queda
organizada en bloques lógicos para facilitar su mantenimiento.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==========================================================
# APP
# ==========================================================

class AppSettings(BaseSettings):
    """Configuración general de la aplicación."""

    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "Trading Bot"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True


# ==========================================================
# DATABASE
# ==========================================================

class DatabaseSettings(BaseSettings):
    """Configuración de la base de datos."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = "sqlite:///./trading_bot.db"
    echo: bool = False


# ==========================================================
# BROKER
# ==========================================================

class BrokerSettings(BaseSettings):
    """Configuración del broker."""

    model_config = SettingsConfigDict(env_prefix="BROKER_")

    provider: str = "alpaca"

    api_key: str = ""
    secret_key: str = ""

    paper_trading: bool = True


# ==========================================================
# MARKET DATA
# ==========================================================

class MarketDataSettings(BaseSettings):
    """Configuración del proveedor de datos."""

    model_config = SettingsConfigDict(env_prefix="MARKET_")

    provider: str = "alpaca"

    cache_minutes: int = 15

    use_adjusted_data: bool = True


# ==========================================================
# LOGGING
# ==========================================================

class LoggingSettings(BaseSettings):
    """Configuración del sistema de logs."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = "INFO"

    folder: str = "logs"

    file_name: str = "trading_bot.log"


# ==========================================================
# LICENSING
# ==========================================================

class LicensingSettings(BaseSettings):
    """
    Configuración del sistema de licencias.

    Aunque todavía no exista el servidor,
    dejamos preparada toda la infraestructura.
    """

    model_config = SettingsConfigDict(env_prefix="LICENSE_")

    enabled: bool = True

    server_url: str = ""

    validation_interval_minutes: int = 60

    offline_grace_hours: int = 72

    minimum_supported_version: str = "0.1.0"


# ==========================================================
# API
# ==========================================================

class ApiSettings(BaseSettings):
    """Configuración de la API."""

    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = "127.0.0.1"

    port: int = 8000


# ==========================================================
# UI
# ==========================================================

class UISettings(BaseSettings):
    """Configuración de la interfaz."""

    model_config = SettingsConfigDict(env_prefix="UI_")

    refresh_seconds: int = 5


# ==========================================================
# SETTINGS ROOT
# ==========================================================

class Settings:
    """
    Objeto principal de configuración.

    Ejemplo:

        settings.database.url

        settings.broker.provider

        settings.logging.level
    """

    def __init__(self):

        self.app = AppSettings()

        self.database = DatabaseSettings()

        self.broker = BrokerSettings()

        self.market = MarketDataSettings()

        self.logging = LoggingSettings()

        self.licensing = LicensingSettings()

        self.api = ApiSettings()

        self.ui = UISettings()


@lru_cache
def get_settings() -> Settings:
    """
    Devuelve una única instancia de Settings
    para toda la aplicación.
    """

    return Settings()


settings = get_settings()
