"""Caché local de velas en la base de datos."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Candle, Timeframe
from app.market_data.provider import Bar


def as_utc(dt: datetime) -> datetime:
    """SQLite devuelve fechas sin zona: las tratamos siempre como UTC."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


@dataclass
class StoreResult:
    inserted: int = 0
    updated: int = 0
    skipped_invalid: int = 0


def _is_valid(b: Bar) -> bool:
    return (
        b.high >= b.low
        and b.low <= min(b.open, b.close)
        and b.high >= max(b.open, b.close)
        and b.volume >= 0
        and b.low > 0
    )


def upsert_candles(
    session: Session, ticker: str, timeframe: Timeframe, bars: list[Bar]
) -> StoreResult:
    """Guarda velas sin duplicar: si ya existe (ticker, timeframe, fecha) la actualiza."""
    result = StoreResult()
    valid = []
    for b in bars:
        if _is_valid(b):
            valid.append(b)
        else:
            result.skipped_invalid += 1
    if not valid:
        return result

    lo, hi = min(b.timestamp for b in valid), max(b.timestamp for b in valid)
    existing = {
        as_utc(c.timestamp): c
        for c in session.scalars(
            select(Candle).where(
                Candle.ticker == ticker,
                Candle.timeframe == timeframe,
                Candle.timestamp >= lo,
                Candle.timestamp <= hi,
            )
        )
    }
    for b in valid:
        row = existing.get(as_utc(b.timestamp))
        if row is None:
            session.add(
                Candle(
                    ticker=ticker,
                    timeframe=timeframe,
                    timestamp=b.timestamp,
                    open=b.open,
                    high=b.high,
                    low=b.low,
                    close=b.close,
                    volume=b.volume,
                )
            )
            result.inserted += 1
        elif (row.open, row.high, row.low, row.close, row.volume) != (
            b.open,
            b.high,
            b.low,
            b.close,
            b.volume,
        ):
            row.open, row.high, row.low, row.close, row.volume = (
                b.open,
                b.high,
                b.low,
                b.close,
                b.volume,
            )
            result.updated += 1
    session.commit()
    return result


def last_timestamp(session: Session, ticker: str, timeframe: Timeframe) -> datetime | None:
    ts = session.scalar(
        select(func.max(Candle.timestamp)).where(
            Candle.ticker == ticker, Candle.timeframe == timeframe
        )
    )
    return as_utc(ts) if ts else None


def load_candles(
    session: Session,
    ticker: str,
    timeframe: Timeframe,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Candle]:
    q = select(Candle).where(Candle.ticker == ticker, Candle.timeframe == timeframe)
    if start:
        q = q.where(Candle.timestamp >= start)
    if end:
        q = q.where(Candle.timestamp <= end)
    return list(session.scalars(q.order_by(Candle.timestamp)))
