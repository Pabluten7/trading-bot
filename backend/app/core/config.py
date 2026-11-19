"""
Configuración central de la aplicación.
Todas las variables se leen desde .env via pydantic-settings.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Base de datos ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://trading:trading_secret@db:5432/trading_bot"
    POSTGRES_USER: str = "trading"
    POSTGRES_PASSWORD: str = "trading_secret"
    POSTGRES_DB: str = "trading_bot"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ── Alpaca ────────────────────────────────────────────────────────────────
    ALPACA_API_KEY: str = ""
    ALPACA_API_SECRET: str = ""
    TRADING_MODE: str = "paper"  # paper | live
    ALPACA_PAPER_BASE_URL: str = "https://paper-api.alpaca.markets"
    ALPACA_LIVE_BASE_URL: str = "https://api.alpaca.markets"
    ALPACA_DATA_BASE_URL: str = "https://data.alpaca.markets"

    @property
    def alpaca_base_url(self) -> str:
        return (
            self.ALPACA_PAPER_BASE_URL
            if self.TRADING_MODE == "paper"
            else self.ALPACA_LIVE_BASE_URL
        )

    # ── Estrategia ────────────────────────────────────────────────────────────
    MAX_POSITIONS: int = 8
    MAX_POSITIONS_PER_SECTOR: int = 3
    MIN_SCORE_THRESHOLD: float = 80.0
    RISK_PER_TRADE: float = 0.01       # 1% del capital
    SL_ATR_MULTIPLIER: float = 2.0
    TP_RISK_RATIO: float = 2.0
    PARTIAL_SELL_PERCENT: float = 0.50

    # ── Notificaciones ────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL_TO: str = ""

    @field_validator("TRADING_MODE")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError("TRADING_MODE must be 'paper' or 'live'")
        return v


settings = Settings()
