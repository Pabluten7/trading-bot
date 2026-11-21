"""Selección final de valores a comprar.

Proceso (por orden de score descendente, y alfabético en caso de empate para que
el resultado sea siempre el mismo):

1. Elegible (histórico diario suficiente).
2. Score >= mínimo (80 por defecto).
3. Filtros (mercado, posición abierta, reentrada, ATR, gap).
4. Tope por sector (cuenta las posiciones ya abiertas + las ya elegidas).
5. Huecos libres: máximo de posiciones simultáneas menos las ya abiertas.

Todo valor que no entra queda con su motivo de descarte.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Signal, Strategy
from app.market_data.store import as_utc
from app.strategy.filters import (
    MarketState,
    PortfolioState,
    first_rejection,
    load_market_state,
    load_portfolio_state,
    reject_sector_full,
)
from app.strategy.params import StrategyParams
from app.strategy.registry import params_of
from app.strategy.scanner import ScanEntry


@dataclass(frozen=True)
class Pick:
    ticker: str
    sector: str | None
    score: float
    price: float  # último cierre diario (referencia; la compra real usa el precio de mercado)
    atr: float  # ATR14 diario


@dataclass
class Selection:
    selected: list[Pick] = field(default_factory=list)
    discarded: dict[str, str] = field(default_factory=dict)  # ticker -> motivo
    free_slots: int = 0

    @property
    def tickers(self) -> list[str]:
        return [p.ticker for p in self.selected]


def select_candidates(
    entries: list[ScanEntry],
    params: StrategyParams,
    market: MarketState,
    portfolio: PortfolioState,
    as_of: datetime,
    opens: dict[str, float] | None = None,
) -> Selection:
    """`opens`: precio de apertura de hoy por valor, si se conoce (para el filtro de gap)."""
    opens = opens or {}
    free = max(params.max_positions - portfolio.open_count, 0)
    result = Selection(free_slots=free)
    sector_counts = dict(portfolio.open_by_sector)

    for entry in sorted(entries, key=lambda e: (-e.result.score, e.ticker)):
        t, r = entry.ticker, entry.result
        reason = None
        if not r.eligible:
            reason = r.reason
        elif r.score < params.min_score:
            reason = f"score {r.score:.1f} < {params.min_score:.0f}"
        else:
            daily = r.daily
            reason = first_rejection(
                t, daily.atr_pct, params, market, portfolio, as_of,
                prev_close=daily.close, today_open=opens.get(t),
            )  # fmt: skip
            if reason is None:
                reason = reject_sector_full(entry.sector, sector_counts, params.max_per_sector)
            if reason is None and len(result.selected) >= free:
                reason = f"sin hueco: máximo {params.max_positions} posiciones"

        if reason is not None:
            result.discarded[t] = reason
            continue
        result.selected.append(
            Pick(t, entry.sector, r.score, r.daily.close, r.daily.atr14)  # type: ignore[arg-type]
        )
        if entry.sector is not None:
            sector_counts[entry.sector] = sector_counts.get(entry.sector, 0) + 1
    return result


def run_selection(
    session: Session,
    strategy: Strategy,
    entries: list[ScanEntry],
    as_of: datetime,
    opens: dict[str, float] | None = None,
) -> Selection:
    """Selecciona y deja el resultado en las señales de ese escaneo
    (`selected` y `discard_reason`). Se puede repetir sin efectos acumulados."""
    as_of = as_utc(as_of)
    params = params_of(strategy)
    selection = select_candidates(
        entries,
        params,
        load_market_state(session, params, as_of),
        load_portfolio_state(session),
        as_of,
        opens,
    )
    chosen = set(selection.tickers)
    for sig in session.scalars(
        select(Signal).where(Signal.strategy_id == strategy.id, Signal.scan_date == as_of)
    ):
        sig.selected = sig.ticker in chosen
        sig.discard_reason = selection.discarded.get(sig.ticker)
    session.commit()
    return selection
