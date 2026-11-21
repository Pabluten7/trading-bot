from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import Signal
from app.indicators import IndicatorSnapshot
from app.strategy.filters import MarketState, PortfolioState
from app.strategy.params import StrategyParams
from app.strategy.registry import get_or_create_default_strategy
from app.strategy.scanner import ScanEntry, scan_universe
from app.strategy.scoring import ScoreResult
from app.strategy.selection import run_selection, select_candidates
from tests.helpers import seed_ticker

AS_OF = datetime(2026, 11, 20, 14, 30, tzinfo=UTC)
END = datetime(2026, 11, 19, 15, 0, tzinfo=UTC)
OK = MarketState(True)
P = StrategyParams()


def daily(close=100.0, atr=2.0) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        timestamp=AS_OF, close=close, volume=1.0, ema20=1, ema50=1, ema200=1, rsi14=60,
        adx14=30, plus_di=30, minus_di=10, atr14=atr, rel_volume=1.0,
    )  # fmt: skip


def entry(ticker, score, sector="Tech", atr=2.0, eligible=True) -> ScanEntry:
    r = ScoreResult(
        score if eligible else 0.0, eligible, None if eligible else "histórico diario insuficiente",
        {}, daily(atr=atr) if eligible else None,
    )  # fmt: skip
    return ScanEntry(ticker, sector, r)


def pick(entries, params=P, market=OK, portfolio=None, opens=None):
    return select_candidates(entries, params, market, portfolio or PortfolioState(), AS_OF, opens)


def test_elige_los_mejores_por_score():
    es = [entry(f"T{i}", 80 + i, sector=f"S{i}") for i in range(12)]
    sel = pick(es)
    assert sel.tickers == [f"T{i}" for i in range(11, 3, -1)]  # los 8 mejores, de mayor a menor
    assert all("sin hueco" in sel.discarded[f"T{i}"] for i in range(4))


def test_exige_score_minimo():
    sel = pick([entry("A", 79.9, "X"), entry("B", 80.0, "Y")])
    assert sel.tickers == ["B"] and sel.discarded["A"] == "score 79.9 < 80"


def test_minimo_configurable():
    assert pick([entry("A", 65)], StrategyParams(min_score=60)).tickers == ["A"]


def test_maximo_3_por_sector_y_entra_el_siguiente_de_otro_sector():
    es = [entry(f"T{i}", 95 - i, "Tech") for i in range(5)] + [entry("F", 81, "Fin")]
    sel = pick(es)
    assert sel.tickers == ["T0", "T1", "T2", "F"]
    assert sel.discarded["T3"] == "sector Tech completo (3/3)"
    assert "sector" in sel.discarded["T4"]


def test_las_posiciones_abiertas_cuentan_para_el_sector_y_los_huecos():
    pf = PortfolioState(open_tickers={"X1", "X2"}, open_by_sector={"Tech": 2})
    sel = pick(
        [entry("A", 90, "Tech"), entry("B", 89, "Tech"), entry("C", 88, "Fin")], portfolio=pf
    )
    assert sel.tickers == ["A", "C"] and "sector Tech completo (3/3)" in sel.discarded["B"]
    assert sel.free_slots == 6


def test_sin_huecos_no_elige_nada():
    pf = PortfolioState(open_tickers={f"X{i}" for i in range(8)})
    sel = pick([entry("A", 99, "Tech")], portfolio=pf)
    assert sel.free_slots == 0 and sel.tickers == [] and "sin hueco" in sel.discarded["A"]


def test_no_compra_lo_que_ya_tiene():
    pf = PortfolioState(open_tickers={"A"}, open_by_sector={"Tech": 1})
    sel = pick([entry("A", 99), entry("B", 90, "Fin")], portfolio=pf)
    assert sel.tickers == ["B"] and sel.discarded["A"] == "posición ya abierta"


def test_mercado_bajista_no_deja_comprar():
    sel = pick([entry("A", 99)], market=MarketState(False, "mercado bajista: SPY"))
    assert sel.tickers == [] and sel.discarded["A"] == "mercado bajista: SPY"


def test_atr_alto_y_gap_descartan():
    sel = pick([entry("A", 99, "X", atr=6.0), entry("B", 98, "Y"), entry("C", 97, "Z")],
               opens={"B": 108.0, "C": 101.0})  # fmt: skip
    assert "ATR" in sel.discarded["A"] and "gap" in sel.discarded["B"] and sel.tickers == ["C"]


def test_valores_no_elegibles_quedan_descartados_con_motivo():
    sel = pick([entry("NEW", 0, eligible=False), entry("A", 90)])
    assert sel.tickers == ["A"] and "insuficiente" in sel.discarded["NEW"]


def test_empates_se_resuelven_alfabeticamente():
    es = [entry(t, 90, sector=t) for t in ("ZZZ", "AAA", "MMM")]
    assert pick(es, StrategyParams(max_positions=2)).tickers == ["AAA", "MMM"]


def test_es_determinista_sin_importar_el_orden_de_entrada():
    es = [entry(f"T{i}", 90 - (i % 4), sector=f"S{i % 5}") for i in range(30)]
    assert pick(es).tickers == pick(list(reversed(es))).tickers


def test_cada_valor_queda_elegido_o_descartado_pero_no_ambos():
    es = [entry(f"T{i}", 70 + i, sector=f"S{i % 4}") for i in range(30)]
    sel = pick(es)
    assert set(sel.tickers).isdisjoint(sel.discarded)
    assert len(sel.tickers) + len(sel.discarded) == 30 and len(sel.tickers) <= 8


# ── Con base de datos ────────────────────────────────────────────────────────
def test_de_extremo_a_extremo_guarda_la_seleccion_en_las_senales(session):
    st = get_or_create_default_strategy(session)
    st.params = {**st.params, "min_score": 60.0}
    seed_ticker(session, "SPY", END, drift=0.002, seed=4)
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    seed_ticker(session, "BAJA", END, drift=-0.003, seed=2)
    entries = scan_universe(session, st, AS_OF, ["SUBE", "BAJA"])
    sel = run_selection(session, st, entries, AS_OF)
    assert sel.tickers == ["SUBE"]
    sigs = {s.ticker: s for s in session.scalars(select(Signal))}
    assert sigs["SUBE"].selected is True and sigs["SUBE"].discard_reason is None
    assert sigs["BAJA"].selected is False and "score" in sigs["BAJA"].discard_reason


def test_repetir_la_seleccion_no_acumula_efectos(session):
    st = get_or_create_default_strategy(session)
    st.params = {**st.params, "min_score": 60.0}
    seed_ticker(session, "SPY", END, drift=0.002, seed=4)
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)
    entries = scan_universe(session, st, AS_OF, ["SUBE"])
    a = run_selection(session, st, entries, AS_OF).tickers
    b = run_selection(session, st, entries, AS_OF).tickers
    assert a == b == ["SUBE"]
    assert session.scalars(select(Signal)).one().selected is True


def test_sin_datos_del_mercado_no_selecciona(session):
    st = get_or_create_default_strategy(session)
    st.params = {**st.params, "min_score": 10.0}
    seed_ticker(session, "SUBE", END, drift=0.002, seed=5)  # sin SPY
    entries = scan_universe(session, st, AS_OF, ["SUBE"])
    sel = run_selection(session, st, entries, AS_OF)
    assert sel.tickers == [] and "sin datos" in sel.discarded["SUBE"]
