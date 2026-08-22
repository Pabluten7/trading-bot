"""
Market data layer.

Provides the internal market-data abstractions used by the
Trading Bot independently of the external data provider.
"""

from app.data.alpaca_provider import (
    AlpacaMarketDataProvider,
    alpaca_market_data_provider,
)
from app.data.models import Candle
from app.data.provider import MarketDataProvider
from app.data.service import (
    MarketDataService,
    market_data_service,
)

__all__ = [
    "AlpacaMarketDataProvider",
    "Candle",
    "MarketDataProvider",
    "MarketDataService",
    "alpaca_market_data_provider",
    "market_data_service",
]