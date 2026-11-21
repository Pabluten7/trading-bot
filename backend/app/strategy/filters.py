"""Filtros de la estrategia: condiciones que descartan un valor aunque tenga buen score.

Cada regla es una función pura que devuelve `None` si el valor pasa, o el
MOTIVO del descarte (texto en español, que se guarda en `Signal.discard_reason`).

Reglas:
1. Mercado: el índice de referencia (SPY) debe cerrar por encima de su EMA200 diaria.
   Sin datos del índice NO se opera (fail-safe).
2. Posición ya abierta en ese valor.
3. Reentrada: tras cerrar una operación hay que esperar N velas de 1 hora completas.
4. Volatilidad: ATR diario > X % del precio -> no operar.
5. Gap de apertura: |apertura - cierre anterior| > X % -> no operar
   (solo se evalúa si se conoce el precio de apertura de hoy).
6. Sector lleno: máximo N posiciones del mismo sector (se aplica al seleccionar).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Timeframe, Trade, TradeStatus
from app.market_data.store import as_utc
from app.strategy.params import StrategyParams
from app.strategy.scanner import completed_snapshot
from app.universe.service import sector_of


# ── Reglas puras ─────────────────────────────────────────────────────────────
def reject_market(benchmark_ok: bool, reason: str | None) -> str | None:
    return None if benchmark_ok else (reason or "mercado no favorable")


def reject_already_open(ticker: str, open_tickers: set[str]) -> str | None:
    return "posición ya abierta" if ticker in open_tickers else None


def reentry_allowed_at(last_exit: datetime, wait_candles: int) -> datetime:
    """Momento desde el que se puede reentrar: la vela de 1H en la que ocurrió la
    salida no cuenta; hay que dejar pasar `wait_candles` velas completas más."""
    exit_utc = as_utc(last_exit)
    start_of_candle = exit_utc.replace(minute=0, second=0, microsecond=0)
    return start_of_candle + timedelta(hours=1 + wait_candles)


def reject_reentry(last_exit: datetime | None, now: datetime, wait_candles: int) -> str | None:
    if last_exit is None:
        return None
    allowed = reentry_allowed_at(last_exit, wait_candles)
    if as_utc(now) < allowed:
        return f"reentrada bloqueada hasta {allowed:%Y-%m-%d %H:%M} UTC"
    return None


def reject_atr(atr_pct: float | None, max_atr_pct: float) -> str | None:
    if atr_pct is None:
        return "sin ATR calculable"
    if atr_pct > max_atr_pct:
        return f"ATR {atr_pct:.1f}% > {max_atr_pct:.1f}%"
    return None


def reject_gap(
    prev_close: float | None, today_open: float | None, max_gap_pct: float
) -> str | None:
    if not prev_close or today_open is None:
        return None  # sin precio de apertura no se puede evaluar
    gap = 100.0 * (today_open - prev_close) / prev_close
    if abs(gap) > max_gap_pct:
        return f"gap {gap:+.1f}% > ±{max_gap_pct:.1f}%"
    return None


def reject_sector_full(
    sector: str | None, counts: dict[str, int], max_per_sector: int
) -> str | None:
    if sector is None:
        return None
    n = counts.get(sector, 0)
    if n >= max_per_sector:
        return f"sector {sector} completo ({n}/{max_per_sector})"
    return None


# ── Estado externo ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class MarketState:
    benchmark_ok: bool
    reason: str | None = None


@dataclass
class PortfolioState:
    open_tickers: set[str] = field(default_factory=set)
    open_by_sector: dict[str, int] = field(default_factory=dict)
    last_exit: dict[str, datetime] = field(default_factory=dict)

    @property
    def open_count(self) -> int:
        return len(self.open_tickers)


def load_market_state(session: Session, params: StrategyParams, as_of: datetime) -> MarketState:
    """SPY (o el índice configurado) por encima de su EMA200 diaria, con la última vela cerrada."""
    snap = completed_snapshot(session, params.benchmark_ticker, Timeframe.D1, as_of)
    name = params.benchmark_ticker
    if snap is None or snap.ema200 is None:
        return MarketState(False, f"sin datos suficientes de {name}: no se opera")
    if snap.close <= snap.ema200:
        return MarketState(
            False, f"mercado bajista: {name} {snap.close:.2f} <= EMA200 {snap.ema200:.2f}"
        )
    return MarketState(True)


def load_portfolio_state(session: Session) -> PortfolioState:
    state = PortfolioState()
    for trade in session.scalars(select(Trade).where(Trade.status == TradeStatus.OPEN)):
        state.open_tickers.add(trade.ticker)
        sector = sector_of(session, trade.ticker) or "?"
        state.open_by_sector[sector] = state.open_by_sector.get(sector, 0) + 1
    for trade in session.scalars(
        select(Trade).where(Trade.status == TradeStatus.CLOSED, Trade.exit_at.is_not(None))
    ):
        exit_at = as_utc(trade.exit_at)
        if exit_at > state.last_exit.get(trade.ticker, datetime.min.replace(tzinfo=UTC)):
            state.last_exit[trade.ticker] = exit_at
    return state


def first_rejection(
    ticker: str,
    atr_pct: float | None,
    params: StrategyParams,
    market: MarketState,
    portfolio: PortfolioState,
    as_of: datetime,
    prev_close: float | None = None,
    today_open: float | None = None,
) -> str | None:
    """Aplica los filtros por orden y devuelve el primer motivo de descarte (o None)."""
    return (
        reject_market(market.benchmark_ok, market.reason)
        or reject_already_open(ticker, portfolio.open_tickers)
        or reject_reentry(portfolio.last_exit.get(ticker), as_of, params.reentry_wait_candles_1h)
        or reject_atr(atr_pct, params.max_atr_pct)
        or reject_gap(prev_close, today_open, params.max_gap_pct)
    )
