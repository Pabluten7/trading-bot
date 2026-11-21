"""Escáner: puntúa los valores del universo y guarda el resultado como señales.

Regla clave anti-trampa: solo se usan velas YA CERRADAS en el momento del escaneo
(`as_of`). Una vela de 1 hora que empezó a las 09:00 no se usa hasta las 10:00.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Signal, Strategy, Timeframe
from app.indicators import IndicatorSnapshot, compute_series, from_candles
from app.market_data.store import as_utc, recent_candles
from app.strategy.params import StrategyParams
from app.strategy.registry import params_of
from app.strategy.scoring import ScoreResult, score_ticker
from app.universe.service import active_tickers, sector_map

# Duración nominal de cada vela (la de 4H puede ser más corta al cierre de sesión;
# usar la nominal es conservador: nunca se usa una vela antes de tiempo).
CANDLE_DURATION = {
    Timeframe.D1: timedelta(days=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.H1: timedelta(hours=1),
}
HISTORY_BARS = 600  # velas por timeframe: de sobra para que la EMA200 se estabilice


def completed_snapshot(
    session: Session, ticker: str, timeframe: Timeframe, as_of: datetime
) -> IndicatorSnapshot | None:
    """Indicadores en la última vela cerrada antes de `as_of`."""
    as_of = as_utc(as_of)
    # una vela cerrada empezó como mucho en as_of - duración
    candles = recent_candles(
        session, ticker, timeframe, as_of - CANDLE_DURATION[timeframe], HISTORY_BARS
    )
    if not candles:
        return None
    return compute_series(from_candles(candles)).last()


def score_at(session: Session, ticker: str, as_of: datetime, params: StrategyParams) -> ScoreResult:
    snaps = {tf: completed_snapshot(session, ticker, tf, as_of) for tf in Timeframe}
    return score_ticker(snaps, params)


@dataclass(frozen=True)
class ScanEntry:
    ticker: str
    sector: str | None
    result: ScoreResult


def scan_universe(
    session: Session,
    strategy: Strategy,
    as_of: datetime,
    tickers: list[str] | None = None,
) -> list[ScanEntry]:
    """Puntúa los valores y guarda/actualiza una `Signal` por valor y escaneo.
    Devuelve las entradas ordenadas de mayor a menor score."""
    as_of = as_utc(as_of).astimezone(UTC)
    params = params_of(strategy)
    sectors = sector_map(session)
    tickers = tickers if tickers is not None else active_tickers(session)

    existing = {
        s.ticker: s
        for s in session.scalars(
            select(Signal).where(Signal.strategy_id == strategy.id, Signal.scan_date == as_of)
        )
    }
    entries: list[ScanEntry] = []
    for ticker in tickers:
        result = score_at(session, ticker, as_of, params)
        entry = ScanEntry(ticker, sectors.get(ticker), result)
        entries.append(entry)

        details = result.details() | {"sector": entry.sector}
        row = existing.get(ticker)
        if row is None:
            session.add(
                Signal(
                    strategy_id=strategy.id,
                    ticker=ticker,
                    scan_date=as_of,
                    score=result.score,
                    details=details,
                    selected=False,
                    discard_reason=None if result.eligible else result.reason,
                )
            )
        else:
            row.score = result.score
            row.details = details
            row.selected = False
            row.discard_reason = None if result.eligible else result.reason
    session.commit()
    entries.sort(key=lambda e: (-e.result.score, e.ticker))
    return entries
