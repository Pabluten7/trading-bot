"""
Market data layer.

Provides the internal market-data abstractions used by the
Trading Bot independently of the external data provider.
"""

from app.data.models import Candle
from app.data.provider import MarketDataProvider
from app.data.service import MarketDataService, market_data_service

__all__ = [
    "Candle",
    "MarketDataProvider",
    "MarketDataService",
    "market_data_service",
]