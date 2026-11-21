"""Contrato común de los proveedores de datos (Alpaca hoy, otros mañana)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.db.models import Timeframe


class MarketDataError(RuntimeError):
    """Fallo al obtener datos del proveedor."""


@dataclass(frozen=True)
class Bar:
    timestamp: datetime  # inicio de la vela, UTC
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class MarketDataProvider(Protocol):
    def get_bars(
        self, tickers: list[str], timeframe: Timeframe, start: datetime, end: datetime
    ) -> dict[str, list[Bar]]:
        """Velas de cada ticker entre start y end, ordenadas por fecha."""
        ...
