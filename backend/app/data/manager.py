"""
Market data manager.

Initializes and manages the configured market-data provider.
"""

from __future__ import annotations

from loguru import logger

from app.config.environment import (
    is_development,
    is_production,
    is_testing,
)
from app.config.settings import settings
from app.data.alpaca_provider import AlpacaMarketDataProvider
from app.data.mock_provider import MockMarketDataProvider
from app.data.service import market_data_service


class MarketDataManager:
    """
    Manages market-data provider initialization and shutdown.
    """

    def __init__(self) -> None:
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Return whether market data has been initialized."""

        return self._initialized

    def initialize(self) -> None:
        """Initialize the configured market-data provider."""

        if self._initialized:
            logger.warning(
                "Market-data manager is already initialized."
            )
            return

        provider_name = (
            settings.market_data.provider
            .lower()
            .strip()
        )

        if provider_name != "alpaca":
            raise ValueError(
                f"Unsupported market-data provider: "
                f"{provider_name}"
            )

        has_credentials = bool(
            settings.broker.api_key
            and settings.broker.secret_key
        )

        if is_production():
            if not has_credentials:
                raise RuntimeError(
                    "Alpaca credentials are required "
                    "in production."
                )

            provider = AlpacaMarketDataProvider()

            logger.info(
                "Using Alpaca market data in production."
            )

        elif is_testing():
            provider = MockMarketDataProvider()

            logger.info(
                "Using mock market data in testing."
            )

        elif is_development():
            if has_credentials:
                provider = AlpacaMarketDataProvider()

                logger.info(
                    "Using Alpaca market data in development."
                )

            else:
                provider = MockMarketDataProvider()

                logger.warning(
                    "Alpaca credentials are not configured. "
                    "Using mock market data for development."
                )

        else:
            raise RuntimeError(
                "Unsupported application environment."
            )

        market_data_service.configure_provider(
            provider
        )

        self._initialized = True

        logger.info(
            "Market-data manager initialized."
        )

    def shutdown(self) -> None:
        """Release market-data resources."""

        if not self._initialized:
            return

        market_data_service.configure_provider(
            None
        )

        self._initialized = False

        logger.info(
            "Market-data manager stopped."
        )


market_data_manager = MarketDataManager()