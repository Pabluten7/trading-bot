from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.db.models import Trade, TradeStatus
from app.strategy.filters import (
    MarketState,
    PortfolioState,
    first_rejection,
    load_market_state,
    load_portfolio_state,
    reentry_allowed_at,
    reject_already_open,
    reject_atr,
    reject_gap,
    reject_market,
    reject_reentry,
    reject_sector_full,
)
from app.strategy.params import StrategyParams
from app.strategy.registry import get_or_create_default_strategy
from app.universe.loader import Constituent
from app.universe.service import sync_universe
from tests.helpers import seed_ticker

END = datetime(2026, 11, 19, 15, 0, tzinfo=UTC)
AS_OF = datetime(2026, 11, 20, 14, 30, tzinfo=UTC)
P = StrategyParams()


# ── Reglas puras ─────────────────────────────────────────────────────────────
def test_mercado():
    assert reject_market(True, None) is None
    assert "bajista" in reject_market(False, "mercado bajista: SPY")


def test_posicion_ya_abierta():
    assert reject_already_open("AAPL", {"AAPL"}) == "posición ya abierta"
    assert reject_already_open("MSFT", {"AAPL"}) is None


@pytest.mark.parametrize(
    ("pct", "ok"), [(None, False), (1.0, True), (5.0, True), (5.01, False), (12.0, False)]
)
def test_atr_maximo_5_por_ciento(pct, ok):
    assert (reject_atr(pct, 5.0) is None) is ok


@pytest.mark.parametrize(
    ("prev", "open_", "ok"),
    [(100, 102.9, True), (100, 103.0, True), (100, 103.5, False), (100, 96.0, False),
     (100, 97.0, True), (100, None, True), (None, 105, True), (0, 105, True)],
)  # fmt: skip
def test_gap_en_ambas_direcciones(prev, open_, ok):
    assert (reject_gap(prev, open_, 3.0) is None) is ok


def test_el_motivo_del_gap_indica_el_signo():
    assert "+4.0%" in reject_gap(100, 104, 3.0)
    assert "-4.0%" in reject_gap(100, 96, 3.0)


def test_sector_lleno():
    assert reject_sector_full("Tech", {"Tech": 2}, 3) is None
    assert "completo (3/3)" in reject_sector_full("Tech", {"Tech": 3}, 3)
    assert reject_sector_full(None, {"Tech": 9}, 3) is None
    assert reject_sector_full("Salud", {"Tech": 9}, 3) is None


# ── Reentrada ────────────────────────────────────────────────────────────────
def test_reentrada_espera_una_vela_completa_tras_la_de_la_salida():
    salida = datetime(2026, 11, 20, 10, 20, tzinfo=UTC)  # dentro de la vela 10:00-11:00
    # la vela 11:00-12:00 es "la 1 vela" a esperar: se puede entrar desde las 12:00
    assert reentry_allowed_at(salida, 1) == datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    assert reentry_allowed_at(salida, 0) == datetime(2026, 11, 20, 11, 0, tzinfo=UTC)


def test_reentrada_bloqueada_y_liberada():
    salida = datetime(2026, 11, 20, 10, 20, tzinfo=UTC)
    assert "12:00" in reject_reentry(salida, datetime(2026, 11, 20, 11, 59, tzinfo=UTC), 1)
    assert reject_reentry(salida, datetime(2026, 11, 20, 12, 0, tzinfo=UTC), 1) is None
    assert reject_reentry(None, AS_OF, 1) is None


def test_reentrada_acepta_fechas_sin_zona():
    salida = datetime(2026, 11, 20, 10, 20)  # como las devuelve SQLite
    assert reject_reentry(salida, datetime(2026, 11, 21, tzinfo=UTC), 1) is None


# ── Mercado desde la base de datos ───────────────────────────────────────────
def test_mercado_alcista_permite_operar(session):
    seed_ticker(session, "SPY", END, drift=0.002, seed=4)
    assert load_market_state(session, P, AS_OF) == MarketState(True)


def test_mercado_bajista_bloquea(session):
    seed_ticker(session, "SPY", END, drift=-0.003, seed=2)
    m = load_market_state(session, P, AS_OF)
    assert not m.benchmark_ok and "bajista" in m.reason and "SPY" in m.reason


def test_sin_datos_del_indice_no_se_opera(session):
    m = load_market_state(session, P, AS_OF)
    assert not m.benchmark_ok and "sin datos" in m.reason


def test_indice_configurable(session):
    seed_ticker(session, "QQQ", END, drift=0.002, seed=4)
    assert load_market_state(session, StrategyParams(benchmark_ticker="QQQ"), AS_OF).benchmark_ok


# ── Estado de la cartera desde la base de datos ──────────────────────────────
def _trade(session, strategy, ticker, status, exit_at=None):
    t = Trade(
        strategy_id=strategy.id, ticker=ticker, status=status, quantity=Decimal(10),
        entry_price=Decimal(100), entry_at=END, stop_loss=Decimal(90), take_profit=Decimal(120),
        exit_at=exit_at,
    )  # fmt: skip
    session.add(t)
    session.flush()


def test_estado_de_cartera(session):
    st = get_or_create_default_strategy(session)
    sync_universe(
        session,
        [
            Constituent("AAPL", "A", "Tech"),
            Constituent("MSFT", "M", "Tech"),
            Constituent("JPM", "J", "Fin"),
        ],
    )
    _trade(session, st, "AAPL", TradeStatus.OPEN)
    _trade(session, st, "MSFT", TradeStatus.OPEN)
    _trade(session, st, "JPM", TradeStatus.CLOSED, END - timedelta(days=3))
    _trade(session, st, "JPM", TradeStatus.CLOSED, END - timedelta(days=1))
    session.commit()
    s = load_portfolio_state(session)
    assert s.open_tickers == {"AAPL", "MSFT"} and s.open_count == 2
    assert s.open_by_sector == {"Tech": 2}
    assert s.last_exit["JPM"] == END - timedelta(days=1)  # la salida más reciente
    assert "AAPL" not in s.last_exit


def test_cartera_vacia(session):
    s = load_portfolio_state(session)
    assert s.open_count == 0 and s.open_by_sector == {} and s.last_exit == {}


# ── Orden de los filtros ─────────────────────────────────────────────────────
OK = MarketState(True)


def test_pasa_todo():
    assert first_rejection("AAPL", 2.0, P, OK, PortfolioState(), AS_OF, 100, 101) is None


def test_el_mercado_manda_sobre_el_resto():
    bad = MarketState(False, "mercado bajista")
    pf = PortfolioState(open_tickers={"AAPL"})
    assert first_rejection("AAPL", 9.0, P, bad, pf, AS_OF) == "mercado bajista"


def test_orden_abierta_reentrada_atr_gap():
    pf = PortfolioState(open_tickers={"A"}, last_exit={"B": AS_OF - timedelta(minutes=10)})
    assert first_rejection("A", 9, P, OK, pf, AS_OF, 100, 120) == "posición ya abierta"
    assert "reentrada" in first_rejection("B", 9, P, OK, pf, AS_OF, 100, 120)
    assert "ATR" in first_rejection("C", 9, P, OK, pf, AS_OF, 100, 120)
    assert "gap" in first_rejection("C", 2, P, OK, pf, AS_OF, 100, 120)
