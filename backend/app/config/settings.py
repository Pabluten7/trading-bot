"""
Central application settings.

All configurable values used by the backend should be exposed through
this module instead of being hard-coded throughout the application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class AppSettings(BaseSettings):
    """General application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        extra="ignore",
    )

    name: str = "Trading Bot"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )

    url: str = "sqlite:///./trading_bot.db"
    echo: bool = False


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------

class BrokerSettings(BaseSettings):
    """Broker connection configuration."""

    model_config = SettingsConfigDict(
        env_prefix="BROKER_",
        extra="ignore",
    )

    provider: str = "alpaca"

    api_key: str = ""
    secret_key: str = ""

    paper_trading: bool = True


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

class MarketDataSettings(BaseSettings):
    """Market data provider configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MARKET_",
        extra="ignore",
    )

    provider: str = "alpaca"

    cache_minutes: int = Field(
        default=15,
        ge=0,
    )

    use_adjusted_data: bool = True


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class LoggingSettings(BaseSettings):
    """Application logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        extra="ignore",
    )

    level: str = "INFO"

    directory: str = "logs"

    filename: str = "trading_bot.log"

    rotation: str = "10 MB"

    retention: str = "30 days"


# ---------------------------------------------------------------------------
# Licensing
# ---------------------------------------------------------------------------

class LicensingSettings(BaseSettings):
    """
    Commercial licensing configuration.

    The product uses one subscription plan with full access to the bot.
    Payment processing and license validation will be handled by the
    dedicated licensing service.
    """

    model_config = SettingsConfigDict(
        env_prefix="LICENSE_",
        extra="ignore",
    )

    enabled: bool = True

    server_url: str = ""

    validation_interval_minutes: int = Field(
        default=60,
        ge=1,
    )

    offline_grace_hours: int = Field(
        default=72,
        ge=0,
    )

    minimum_supported_version: str = "0.1.0"

    product_id: str = "trading-bot"

    subscription_required: bool = True


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

class SecuritySettings(BaseSettings):
    """Authentication and security configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        extra="ignore",
    )

    jwt_secret_key: str = (
        "development-only-change-this-secret"
    )

    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
    )

    refresh_token_expire_days: int = Field(
        default=30,
        ge=1,
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class ApiSettings(BaseSettings):
    """Backend API configuration."""

    model_config = SettingsConfigDict(
        env_prefix="API_",
        extra="ignore",
    )

    host: str = "127.0.0.1"

    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
    )

    reload: bool = False

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
        ]
    )


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

class FrontendSettings(BaseSettings):
    """Frontend-related configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FRONTEND_",
        extra="ignore",
    )

    url: str = "http://localhost:5173"


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------

class TradingSettings(BaseSettings):
    """General trading configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TRADING_",
        extra="ignore",
    )

    market_timezone: str = "America/New_York"

    candle_timeframe: str = "4Hour"

    maximum_simultaneous_positions: int = Field(
        default=8,
        ge=1,
    )

    maximum_positions_per_sector: int = Field(
        default=3,
        ge=1,
    )


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class RiskSettings(BaseSettings):
    """Global risk configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RISK_",
        extra="ignore",
    )

    max_risk_per_trade_percent: float = Field(
        default=1.0,
        gt=0,
        le=100,
    )

    maximum_portfolio_risk_percent: float = Field(
        default=5.0,
        gt=0,
        le=100,
    )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class SchedulerSettings(BaseSettings):
    """Background task scheduler configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_",
        extra="ignore",
    )

    enabled: bool = True

    timezone: str = "America/New_York"


# ---------------------------------------------------------------------------
# Main settings
# ---------------------------------------------------------------------------

class Settings:
    """
    Root configuration object.

    All application modules should obtain configuration through the
    ``settings`` singleton rather than instantiating configuration classes
    themselves.
    """

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.broker = BrokerSettings()
        self.market_data = MarketDataSettings()
        self.logging = LoggingSettings()
        self.licensing = LicensingSettings()
        self.security = SecuritySettings()
        self.api = ApiSettings()
        self.frontend = FrontendSettings()
        self.trading = TradingSettings()
        self.risk = RiskSettings()
        self.scheduler = SchedulerSettings()

    @property
    def backend_directory(self) -> Path:
        """Return the backend root directory."""

        return BACKEND_DIR

    @property
    def project_directory(self) -> Path:
        """Return the project root directory."""

        return PROJECT_DIR

    @property
    def log_directory(self) -> Path:
        """Return the absolute log directory."""

        directory = Path(self.logging.directory)

        if not directory.is_absolute():
            directory = self.backend_directory / directory

        return directory


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the application-wide settings singleton.

    ``lru_cache`` guarantees that the same Settings instance is reused
    throughout the lifetime of the process.
    """

    return Settings()


settings = get_settings()