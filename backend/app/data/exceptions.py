"""
Market data exceptions.
"""

from __future__ import annotations


class MarketDataError(Exception):
    """Base exception for market-data errors."""


class MarketDataProviderError(MarketDataError):
    """Raised when an external market-data provider fails."""


class MarketDataUnavailableError(MarketDataError):
    """Raised when requested market data is unavailable."""


class InvalidMarketDataError(MarketDataError):
    """Raised when received market data is invalid."""