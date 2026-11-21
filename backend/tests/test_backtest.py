import csv
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.backtest import BacktestConfig, run_backtest
from app.backtest.data import load_backtest_data
from app.backtest.engine import TickerData
from app.backtest.report import summary_text, write_report
from app.db.models import Timeframe
from app.indicators import Ohlcv
from app.strategy.params import StrategyParams
from tests.helpers import make_bars, seed_ticker

END = datetime(2026, 6, 30, 5, 0, tzinfo=UTC)
N = 700
SECTORS = ["Tech", "Fin", "Salud"]
PARAMS = StrategyParams(min_score=60.0)


def to_ohlcv(bars):
    return [Ohlcv(b.timestamp, *(float(x) for x in (b.open, b.high, b.low, b.close)), b.volume)
            for b in bars]  # fmt: skip


def world(n_tickers=12, spy_drift=0.0015, drifts=None, n=N):
    """Un mercado simulado: SPY y varias acciones solo con velas diarias."""
    data = {}
    for i in range(n_tickers):
        drift = (drifts or [0.0025, 0.0018, 0.0005, -0.001])[i % 4]
        bars = to_ohlcv(make_bars(Timeframe.D1, n, END, drift, 0.012, seed=100 + i))
        data[f"T{i:02d}"] = TickerData(f"T{i:02d}", SECTORS[i % 3], {Timeframe.D1: bars})
    spy = TickerData(
        "SPY",
        None,
        {Timeframe.D1: to_ohlcv(make_bars(Timeframe.D1, n, END, spy_drift, 0.006, seed=4))},
    )
    return data, spy


def cfg(**kw):
    base = dict(start=date(2026, 1, 1), end=date(2026, 6, 30), use_intraday=False)
    return BacktestConfig(**{**base, **kw})


@pytest.fixture(scope="module")
def result():
    data, spy = world()
    return run_backtest(data, spy, PARAMS, cfg())


def test_produce_curva_de_capital_y_operaciones(result):
    assert len(result.dates) == len(result.equity) == 181
    assert result.equity[0] == pytest.approx(100_000, rel=0.05)
    assert len(result.trades) > 5
    assert result.metrics["trades"] == len(result.trades)


def test_la_contabilidad_cuadra_al_centimo(result):
    """Capital final = capital inicial + suma del beneficio de todas las operaciones."""
    total = sum((t.pnl for t in result.trades), Decimal(0))
    assert result.equity[-1] == pytest.approx(float(100_000 + total), abs=0.01)


def test_todas_las_operaciones_estan_cerradas_y_ordenadas(result):
    for t in result.trades:
        assert t.exit_date is not None and t.exit_date >= t.entry_date and t.fills
        assert sum(f.quantity for f in t.fills) == t.quantity  # se vende exactamente lo comprado


def test_nunca_hay_mas_posiciones_que_el_maximo():
    data, spy = world(n_tickers=16, drifts=[0.003] * 4)
    prm = StrategyParams(min_score=40.0, max_positions=3, max_per_sector=2)
    r = run_backtest(data, spy, prm, cfg())
    day = r.dates[0]
    while day <= r.dates[-1]:
        activas = [t for t in r.trades if t.entry_date <= day <= t.exit_date]
        assert len(activas) <= 3
        for s in SECTORS:
            assert sum(1 for t in activas if t.sector == s) <= 2
        day += timedelta(days=1)
    assert r.trades  # el test es válido: sí hubo operaciones


def test_el_riesgo_por_operacion_respeta_las_reglas(result):
    pico = max(result.equity)
    for t in result.trades:
        assert t.risk_amount <= Decimal(str(pico)) * Decimal("0.01") + Decimal("0.01")
        assert t.entry_price * t.quantity <= Decimal(str(pico)) * Decimal("0.125") + Decimal(1)
        assert t.initial_stop < t.entry_price < t.take_profit


def test_es_determinista():
    data, spy = world()
    a = run_backtest(data, spy, PARAMS, cfg())
    b = run_backtest(data, spy, PARAMS, cfg())
    assert a.equity == b.equity and [t.pnl for t in a.trades] == [t.pnl for t in b.trades]


def _desplome_desde(td: TickerData, corte: datetime) -> TickerData:
    """Mismo mercado hasta `corte`; después, un hundimiento brutal."""
    barras = [
        b
        if b.timestamp <= corte
        else Ohlcv(b.timestamp, b.open * 0.3, b.high * 0.3, b.low * 0.25, b.close * 0.3, b.volume)
        for b in td.series[Timeframe.D1].bars
    ]
    return TickerData(td.ticker, td.sector, {Timeframe.D1: barras})


def test_el_futuro_no_altera_lo_ya_simulado():
    """Para muchas fechas de corte: dos mercados idénticos hasta el corte y distintos
    después deben dar exactamente el mismo capital y las mismas compras hasta el corte.
    (Se prueban varias fechas porque en un día concreto puede no haber compras.)"""
    data, spy = world()
    base = run_backtest(data, spy, PARAMS, cfg())
    sensibles = 0
    for dias in range(2, 170, 4):
        dia_corte = base.dates[0] + timedelta(days=dias)
        corte = datetime.combine(dia_corte, datetime.min.time(), UTC).replace(hour=5)
        otro = run_backtest(
            {t: _desplome_desde(td, corte) for t, td in data.items()},
            _desplome_desde(spy, corte),
            PARAMS,
            cfg(),
        )
        k = base.dates.index(dia_corte) + 1
        assert base.equity[:k] == otro.equity[:k], f"el futuro cambió el pasado (corte {dia_corte})"
        sensibles += base.equity[k:] != otro.equity[k:]

        def entradas(r, hasta=dia_corte):
            return sorted(
                (t.entry_date, t.ticker, t.quantity, t.entry_price)
                for t in r.trades
                if t.entry_date <= hasta
            )

        assert entradas(base) == entradas(otro)
    assert sensibles > 30  # en la mayoría de cortes el futuro sí es distinto: el test es sensible


def test_las_decisiones_solo_ven_velas_cerradas():
    """A la apertura del día D solo existe información hasta el cierre de D-1."""
    data, _ = world()
    td = data["T00"]
    bars = td.series[Timeframe.D1].bars
    dia = bars[400]
    assert (
        td.snapshot_at(Timeframe.D1, dia.timestamp + timedelta(hours=9, minutes=30)).timestamp
        == bars[399].timestamp
    )
    # justo al cerrar la vela de D ya se puede usar
    assert (
        td.snapshot_at(Timeframe.D1, dia.timestamp + timedelta(days=1)).timestamp == dia.timestamp
    )
    assert td.snapshot_at(Timeframe.D1, bars[0].timestamp) is None  # antes de la primera vela


def test_mercado_bajista_no_opera():
    data, spy = world(spy_drift=-0.003)
    r = run_backtest(data, spy, PARAMS, cfg())
    assert r.trades == [] and r.equity[-1] == pytest.approx(100_000)


def test_el_deslizamiento_reduce_el_resultado():
    data, spy = world()
    sin = run_backtest(data, spy, PARAMS, cfg(slippage_pct=0.0))
    con = run_backtest(data, spy, PARAMS, cfg(slippage_pct=0.01))
    assert con.equity[-1] < sin.equity[-1]


def test_el_deslizamiento_se_aplica_en_entradas_y_salidas():
    data, spy = world()
    slip = Decimal("0.01")
    r = run_backtest(data, spy, PARAMS, cfg(slippage_pct=0.01))
    assert r.trades
    for t in r.trades:  # entrada: apertura del día + 1 %
        td = data[t.ticker]
        ts = datetime.combine(t.entry_date, datetime.min.time(), UTC).replace(hour=5)
        apertura = Decimal(str(td.series[Timeframe.D1].bars[td.day_index[ts]].open))
        assert t.entry_price == (apertura * (1 + slip)).quantize(Decimal("0.01"))
    stops = [t for t in r.trades if t.fills[0].kind.value == "stop_loss"]
    assert stops
    for t in stops:  # salida por stop: el stop menos 1 % (o peor si hubo hueco)
        assert t.fills[0].price <= t.initial_stop * (1 - slip)
    assert any(t.fills[0].price == t.initial_stop * (1 - slip) for t in stops)


def test_capital_inicial_configurable():
    data, spy = world()
    r = run_backtest(data, spy, PARAMS, cfg(initial_capital=Decimal(10_000)))
    assert r.metrics["initial_capital"] == 10_000
    assert all(t.quantity >= 1 for t in r.trades)


def test_errores_claros():
    data, spy = world()
    with pytest.raises(ValueError, match="rango"):
        run_backtest(data, spy, PARAMS, cfg(start=date(2030, 1, 1), end=date(2030, 2, 1)))
    with pytest.raises(ValueError, match="diarias"):
        run_backtest(data, TickerData("SPY", None, {}), PARAMS, cfg())


def test_el_informe_incluye_metricas_y_limitaciones(result, tmp_path):
    texto = summary_text(result)
    assert "Operaciones" in texto and "sesgo de supervivencia" in texto and "SPY" in texto
    write_report(result, tmp_path)
    m = json.loads((tmp_path / "metrics.json").read_text())
    assert m["metrics"]["trades"] == len(result.trades) and m["params"]["min_score"] == 60.0
    filas = list(csv.DictReader(open(tmp_path / "trades.csv", encoding="utf-8")))
    assert len(filas) == len(result.trades)
    assert len(list(csv.reader(open(tmp_path / "equity.csv", encoding="utf-8")))) == 182


def test_carga_desde_la_base_de_datos_y_ejecuta(session):
    for i, name in enumerate(["AAA", "BBB", "SPY"]):
        seed_ticker(session, name, END, drift=0.002, seed=20 + i,
                    n={Timeframe.D1: 700, Timeframe.H4: 300, Timeframe.H1: 300})  # fmt: skip
    data, spy = load_backtest_data(
        session, ["AAA", "BBB", "NOEXISTE"], "SPY", date(2026, 1, 1), date(2026, 6, 30), False
    )
    assert set(data) == {"AAA", "BBB"}  # el que no tiene datos se ignora
    r = run_backtest(data, spy, PARAMS, cfg())
    assert len(r.dates) > 100
    data_full, spy2 = load_backtest_data(
        session, ["AAA"], "SPY", date(2026, 1, 1), date(2026, 6, 30), True
    )
    assert set(data_full["AAA"].series) == set(Timeframe)  # con intradía carga los 3
