"""Carga de datos históricos para el backtest desde la base de datos."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtest.engine import TickerData
from app.db.models import Timeframe, UniverseMember
from app.indicators import from_candles
from app.market_data.store import load_candles

WARMUP_DAYS = 450  # velas previas al inicio para que EMA200, ADX... estén estabilizados


def load_ticker(
    session: Session,
    ticker: str,
    sector: str | None,
    start: date,
    end: date,
    use_intraday: bool,
) -> TickerData:
    lo = datetime.combine(start - timedelta(days=WARMUP_DAYS), datetime.min.time(), UTC)
    hi = datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC)
    timeframes = list(Timeframe) if use_intraday else [Timeframe.D1]
    bars = {tf: from_candles(load_candles(session, ticker, tf, lo, hi)) for tf in timeframes}
    return TickerData(ticker, sector, bars)


def load_backtest_data(
    session: Session,
    tickers: list[str],
    benchmark_ticker: str,
    start: date,
    end: date,
    use_intraday: bool = True,
) -> tuple[dict[str, TickerData], TickerData]:
    sectors = {m.ticker: m.sector for m in session.scalars(select(UniverseMember))}
    data = {}
    for t in tickers:
        td = load_ticker(session, t, sectors.get(t), start, end, use_intraday)
        if Timeframe.D1 in td.series:  # sin velas diarias no se puede operar
            data[t] = td
    benchmark = load_ticker(session, benchmark_ticker, None, start, end, use_intraday=False)
    return data, benchmark
