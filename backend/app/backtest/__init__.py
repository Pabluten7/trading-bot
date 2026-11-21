"""Backtest: reproduce la estrategia sobre datos históricos."""

from app.backtest.engine import BacktestConfig, BacktestResult, BacktestTrade, run_backtest
from app.backtest.metrics import compute_metrics

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "BacktestTrade",
    "compute_metrics",
    "run_backtest",
]
