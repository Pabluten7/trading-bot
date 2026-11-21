"""Sincronización incremental del histórico: solo pide lo que falta."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Timeframe
from app.market_data.provider import MarketDataProvider
from app.market_data.store import last_timestamp, upsert_candles

# Histórico inicial por timeframe (los indicadores necesitan ~200 velas de calentamiento).
DEFAULT_LOOKBACK_DAYS = {Timeframe.D1: 730, Timeframe.H4: 180, Timeframe.H1: 90}


@dataclass
class SyncStats:
    inserted: int = 0
    updated: int = 0
    skipped_invalid: int = 0
    no_data: list[str] = field(default_factory=list)


def sync_history(
    session: Session,
    provider: MarketDataProvider,
    tickers: list[str],
    timeframes: list[Timeframe] | None = None,
    lookback_days: dict[Timeframe, int] | None = None,
    now: datetime | None = None,
) -> dict[Timeframe, SyncStats]:
    now = now or datetime.now(UTC)
    timeframes = timeframes or list(Timeframe)
    lookback = {**DEFAULT_LOOKBACK_DAYS, **(lookback_days or {})}
    stats: dict[Timeframe, SyncStats] = {}

    for tf in timeframes:
        st = stats[tf] = SyncStats()
        # Agrupamos tickers por fecha de inicio para hacer pocas peticiones.
        by_start: dict[datetime, list[str]] = defaultdict(list)
        for ticker in tickers:
            last = last_timestamp(session, ticker, tf)
            # Pedimos desde la última vela guardada (inclusive) para refrescar la
            # vela que estuviera incompleta cuando se guardó.
            start = last or (now - timedelta(days=lookback[tf]))
            by_start[start].append(ticker)

        for start, group in by_start.items():
            fetched = provider.get_bars(group, tf, start, now)
            for ticker in group:
                bars = fetched.get(ticker, [])
                if not bars:
                    st.no_data.append(ticker)
                    continue
                r = upsert_candles(session, ticker, tf, bars)
                st.inserted += r.inserted
                st.updated += r.updated
                st.skipped_invalid += r.skipped_invalid
    return stats
