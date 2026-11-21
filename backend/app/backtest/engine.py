"""Motor de backtest diario.

Usa EXACTAMENTE las mismas piezas que el bot real: `score_ticker`,
`select_candidates`, `plan_trade` y `advance`. Solo cambian los datos (históricos).

Cómo avanza cada día de mercado D:
1. A la apertura (`as_of` = inicio de la vela diaria + 9:30) se puntúan los valores con
   las velas ya cerradas en ese momento (nada del día D ni posterior).
2. Se seleccionan valores (filtros, tope por sector, huecos libres) y se compran a la
   apertura de D, con deslizamiento (slippage) en contra.
3. Se gestionan TODAS las posiciones (también las recién abiertas) con la vela de D:
   stop, objetivo parcial y trailing, con las reglas pesimistas de `advance`.
4. Se valora la cartera al cierre.

Limitaciones conocidas (se muestran en el informe):
- Las decisiones se toman a la apertura con datos hasta el cierre anterior; el bot real
  necesitará el precio de apertura en vivo (HU-12).
- Sin comisiones (Alpaca no cobra en acciones). El deslizamiento se aplica en entradas
  y salidas (por defecto 0,05 %).
- Se usa el universo actual del S&P500: hay sesgo de supervivencia (no incluye empresas
  que ya salieron del índice).
"""

from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.backtest.metrics import compute_metrics
from app.db.models import Timeframe
from app.indicators import IndicatorSeries, IndicatorSnapshot, Ohlcv, compute_series
from app.risk import Fill, FillKind, PositionState, advance, plan_trade, realized_pnl
from app.strategy.filters import MarketState, PortfolioState
from app.strategy.params import StrategyParams
from app.strategy.scanner import CANDLE_DURATION, ScanEntry
from app.strategy.scoring import score_ticker
from app.strategy.selection import select_candidates


@dataclass(frozen=True)
class BacktestConfig:
    start: date
    end: date
    initial_capital: Decimal = Decimal(100_000)
    slippage_pct: float = 0.0005
    use_intraday: bool = True  # False: puntúa solo con el diario (si no hay histórico 4H/1H)
    open_offset: timedelta = timedelta(hours=9, minutes=30)


class TickerData:
    """Series de indicadores de un valor, listas para consultar en cualquier fecha."""

    def __init__(self, ticker: str, sector: str | None, bars: dict[Timeframe, list[Ohlcv]]):
        self.ticker = ticker
        self.sector = sector
        self.series: dict[Timeframe, IndicatorSeries] = {
            tf: compute_series(b) for tf, b in bars.items() if b
        }
        self._ends = {
            tf: [b.timestamp + CANDLE_DURATION[tf] for b in s.bars] for tf, s in self.series.items()
        }
        daily = self.series.get(Timeframe.D1)
        self.day_index = {b.timestamp: i for i, b in enumerate(daily.bars)} if daily else {}

    def snapshot_at(self, tf: Timeframe, as_of: datetime) -> IndicatorSnapshot | None:
        """Indicadores en la última vela CERRADA en `as_of`."""
        s = self.series.get(tf)
        if s is None:
            return None
        i = bisect_right(self._ends[tf], as_of) - 1
        return s.at(i) if i >= 0 else None


@dataclass
class BacktestTrade:
    ticker: str
    sector: str | None
    entry_date: date
    entry_price: Decimal
    quantity: int
    initial_stop: Decimal
    take_profit: Decimal
    risk_amount: Decimal
    score: float
    exit_date: date | None = None
    fills: list[Fill] = field(default_factory=list)

    @property
    def pnl(self) -> Decimal:
        return realized_pnl(self.entry_price, self.fills)

    @property
    def r_multiple(self) -> float:
        return float(self.pnl / self.risk_amount) if self.risk_amount else 0.0

    @property
    def holding_days(self) -> int:
        return ((self.exit_date or self.entry_date) - self.entry_date).days

    @property
    def exit_reason(self) -> str:
        return self.fills[-1].kind.value if self.fills else "abierta"


@dataclass
class BacktestResult:
    config: BacktestConfig
    params: StrategyParams
    trades: list[BacktestTrade]
    dates: list[date]
    equity: list[float]
    metrics: dict


def run_backtest(
    data: dict[str, TickerData],
    benchmark: TickerData,
    params: StrategyParams,
    config: BacktestConfig,
) -> BacktestResult:
    bench_daily = benchmark.series.get(Timeframe.D1)
    if bench_daily is None:
        raise ValueError(f"No hay velas diarias del índice de referencia {benchmark.ticker}")
    days = [b for b in bench_daily.bars if config.start <= b.timestamp.date() <= config.end]
    if not days:
        raise ValueError("No hay días de mercado en el rango pedido")

    slip = Decimal(str(config.slippage_pct))
    cash = config.initial_capital
    open_pos: dict[str, tuple[PositionState, BacktestTrade]] = {}
    last_close: dict[str, Decimal] = {}
    last_exit: dict[str, datetime] = {}
    trades: list[BacktestTrade] = []
    dates, equity, exposure = [], [], []

    def mark_to_market() -> Decimal:
        return cash + sum(
            (st.remaining * last_close.get(t, st.entry_price) for t, (st, _) in open_pos.items()),
            Decimal(0),
        )

    for k, day in enumerate(days):
        as_of = day.timestamp + config.open_offset
        today: dict[str, Ohlcv] = {}
        for t, td in data.items():
            i = td.day_index.get(day.timestamp)
            if i is not None:
                today[t] = td.series[Timeframe.D1].bars[i]

        # 1-2) Selección y compras a la apertura
        equity_now = mark_to_market()
        bsnap = benchmark.snapshot_at(Timeframe.D1, as_of)
        market = _market_state(bsnap, params)
        portfolio = PortfolioState(
            open_tickers=set(open_pos),
            open_by_sector=_sector_counts(open_pos),
            last_exit=dict(last_exit),
        )
        entries = []
        for t, td in data.items():
            if t not in today:
                continue
            snaps = {
                tf: (
                    td.snapshot_at(tf, as_of)
                    if (tf is Timeframe.D1 or config.use_intraday)
                    else None
                )
                for tf in Timeframe
            }
            entries.append(
                ScanEntry(
                    t,
                    td.sector,
                    score_ticker(snaps, params, renormalize_missing=not config.use_intraday),
                )
            )
        opens = {t: bar.open for t, bar in today.items()}
        selection = select_candidates(entries, params, market, portfolio, as_of, opens)
        for pick in selection.selected:
            entry = Decimal(str(today[pick.ticker].open)) * (1 + slip)
            res = plan_trade(pick.ticker, entry, pick.atr, equity_now, cash, params)
            if res.plan is None:
                continue
            plan = res.plan
            cash -= plan.position_value
            state = PositionState.from_plan(plan)
            trade = BacktestTrade(
                pick.ticker, pick.sector, day.timestamp.date(), plan.entry_price, plan.quantity,
                plan.stop_loss, plan.take_profit, plan.risk_amount, pick.score,
            )  # fmt: skip
            open_pos[pick.ticker] = (state, trade)

        # 3) Gestión de todas las posiciones con la vela de hoy
        for t in list(open_pos):
            bar = today.get(t)
            if bar is None:
                continue
            state, trade = open_pos[t]
            fills = advance(state, bar.open, bar.high, bar.low, bar.close, params)
            for f in fills:
                f = Fill(f.kind, f.price * (1 - slip), f.quantity)
                trade.fills.append(f)
                cash += f.price * f.quantity
            if not state.is_open:
                trade.exit_date = day.timestamp.date()
                trades.append(trade)
                last_exit[t] = day.timestamp + timedelta(hours=16)
                del open_pos[t]

        for t, bar in today.items():
            last_close[t] = Decimal(str(bar.close))

        # 4) Último día: se cierra todo al cierre para medir el resultado completo
        if k == len(days) - 1:
            for t in list(open_pos):
                state, trade = open_pos.pop(t)
                price = last_close.get(t, state.entry_price) * (1 - slip)
                trade.fills.append(Fill(FillKind.MANUAL, price, state.remaining))
                cash += price * state.remaining
                state.remaining = 0
                trade.exit_date = day.timestamp.date()
                trades.append(trade)

        eq = mark_to_market()
        invested = eq - cash
        dates.append(day.timestamp.date())
        equity.append(float(eq))
        exposure.append(float(invested / eq) if eq > 0 else 0.0)

    bench_close = [b.close for b in days]
    metrics = compute_metrics(
        float(config.initial_capital), dates, equity, trades, exposure, bench_close
    )
    return BacktestResult(config, params, trades, dates, equity, metrics)


def _market_state(snap: IndicatorSnapshot | None, params: StrategyParams) -> MarketState:
    name = params.benchmark_ticker
    if snap is None or snap.ema200 is None:
        return MarketState(False, f"sin datos suficientes de {name}: no se opera")
    if snap.close <= snap.ema200:
        return MarketState(False, f"mercado bajista: {name} por debajo de su EMA200")
    return MarketState(True)


def _sector_counts(open_pos: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, trade in open_pos.values():
        key = trade.sector or "?"
        counts[key] = counts.get(key, 0) + 1
    return counts
