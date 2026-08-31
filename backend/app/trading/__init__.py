"""
Trading execution package.

Coordinates market analysis, strategy decisions, risk validation,
and broker order execution.
"""

from app.trading.engine import TradingEngine
from app.trading.models import TradeDecision, TradeResult

__all__ = [
    "TradeDecision",
    "TradeResult",
    "TradingEngine",
]