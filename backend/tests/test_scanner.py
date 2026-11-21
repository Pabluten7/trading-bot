from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db.models import Signal, Strategy, Timeframe
from app.strategy.params import StrategyParams
from app.strategy.registry import DEFAULT_STRATEGY_NAME, get_or_create_default_strategy, params_of
from app.strategy.scanner import completed_snapshot, scan_universe
from app.universe.loader import Constituent
from app.universe.service import sync_universe
from tests.helpers import seed_ticker

END = datetime(2026, 11, 19, 15, 0, tzinfo=UTC)  # inicio de la última vela sembrada
AS_OF = datetime(2026, 11, 20, 14, 30, tzinfo=UTC)  # apertura del mercado del día siguiente


@pytest.fixture
def strategy(session):
    return get_or_create_default_strategy(session)


def _count(session):
    return session.scalar(select(func.count()).select_from(Signal))


def test_estrategia_por_defecto_se_crea_una_sola_vez(session):
    a = get_or_create_default_strategy(session)
    b = get_or_create_default_strategy(session)
    assert a.id == b.id and a.name == DEFAULT_STRATEGY_NAME and a.is_default
    assert params_of(a) == StrategyParams()


def test_parametros_incompletos_toman_el_valor_por_defecto(session):
    s = Strategy(name="x", params={"min_score": 70})
    p = params_of(s)
    assert p.min_score == 70 and p.max_positions == 8


def test_tendencia_alcista_puntua_mas_que_bajista(session, strategy):
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    seed_ticker(session, "BAJA", END, drift=-0.003, seed=2)
    entries = scan_universe(session, strategy, AS_OF, ["SUBE", "BAJA"])
    assert [e.ticker for e in entries] == ["SUBE", "BAJA"]
    assert entries[0].result.score - entries[1].result.score > 30
    assert 0 <= entries[1].result.score < entries[0].result.score <= 100


def test_guarda_una_senal_por_valor_con_el_desglose(session, strategy):
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    scan_universe(session, strategy, AS_OF, ["SUBE"])
    sig = session.scalars(select(Signal)).one()
    assert sig.ticker == "SUBE" and sig.selected is False and sig.discard_reason is None
    assert float(sig.score) > 50 and sig.details["timeframes"]["1D"]["available"] is True
    assert sig.details["daily"]["close"] > 0


def test_repetir_el_mismo_escaneo_no_duplica(session, strategy):
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    scan_universe(session, strategy, AS_OF, ["SUBE"])
    scan_universe(session, strategy, AS_OF, ["SUBE"])
    assert _count(session) == 1
    scan_universe(session, strategy, AS_OF + timedelta(days=1), ["SUBE"])
    assert _count(session) == 2


def test_valor_sin_datos_queda_registrado_como_no_elegible(session, strategy):
    entries = scan_universe(session, strategy, AS_OF, ["FANTASMA"])
    assert entries[0].result.score == 0 and not entries[0].result.eligible
    sig = session.scalars(select(Signal)).one()
    assert "insuficiente" in sig.discard_reason


def test_historico_corto_no_es_elegible(session, strategy):
    corto = {tf: 100 for tf in Timeframe}  # 100 velas: no alcanza la EMA200
    seed_ticker(session, "NUEVA", END, n=corto, seed=3)
    assert not scan_universe(session, strategy, AS_OF, ["NUEVA"])[0].result.eligible


def test_sin_lista_usa_el_universo_activo_con_su_sector(session, strategy):
    sync_universe(
        session,
        [Constituent("SUBE", "Sube Inc", "Technology"), Constituent("OTRA", "Otra", "Financials")],
    )
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    entries = scan_universe(session, strategy, AS_OF)
    assert {e.ticker for e in entries} == {"SUBE", "OTRA"}
    assert next(e for e in entries if e.ticker == "SUBE").sector == "Technology"
    assert (
        session.scalars(select(Signal).where(Signal.ticker == "SUBE")).one().details["sector"]
        == "Technology"
    )


# ── Solo velas cerradas ──────────────────────────────────────────────────────
def test_no_usa_la_vela_que_aun_no_ha_cerrado(session):
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)  # última vela 1H empieza a las 15:00
    # a las 15:30 la vela de las 15:00 sigue abierta: se usa la de las 14:00
    a = completed_snapshot(session, "SUBE", Timeframe.H1, END + timedelta(minutes=30))
    assert a.timestamp == END - timedelta(hours=1)
    # a las 16:00 en punto ya cerró
    b = completed_snapshot(session, "SUBE", Timeframe.H1, END + timedelta(hours=1))
    assert b.timestamp == END


def test_la_vela_diaria_de_hoy_no_se_usa_antes_de_cerrar(session):
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    snap = completed_snapshot(session, "SUBE", Timeframe.D1, END + timedelta(hours=1))
    assert snap.timestamp == END - timedelta(days=1)


def test_resultado_no_cambia_si_llegan_velas_posteriores(session, strategy):
    """Añadir datos futuros no debe alterar un escaneo pasado."""
    from app.market_data.store import upsert_candles
    from tests.helpers import make_bars

    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    antes = scan_universe(session, strategy, AS_OF, ["SUBE"])[0].result.score
    for tf in Timeframe:
        futuro = make_bars(tf, 30, END + timedelta(days=10), drift=-0.05, seed=9)
        upsert_candles(session, "SUBE", tf, [b for b in futuro if b.timestamp > AS_OF])
    despues = scan_universe(session, strategy, AS_OF, ["SUBE"])[0].result.score
    assert antes == despues
