import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.db.models import Timeframe
from app.indicators import IndicatorSnapshot
from app.strategy.params import StrategyParams
from app.strategy.scoring import (
    adx_points,
    atr_points,
    rsi_points,
    score_ticker,
    score_timeframe,
    trend_points,
    volume_points,
)

NOW = datetime(2026, 11, 20, tzinfo=UTC)


def snap(**kw) -> IndicatorSnapshot:
    base = dict(
        timestamp=NOW, close=100.0, volume=1000.0, ema20=None, ema50=None, ema200=None,
        rsi14=None, adx14=None, plus_di=None, minus_di=None, atr14=None, rel_volume=None,
    )  # fmt: skip
    base.update(kw)
    return IndicatorSnapshot(**base)


def perfect(**kw) -> IndicatorSnapshot:
    """Valor ideal en todos los componentes (100 puntos)."""
    return snap(
        close=110.0, ema20=105.0, ema50=100.0, ema200=90.0, rsi14=60.0, adx14=30.0,
        plus_di=30.0, minus_di=10.0, atr14=2.5, rel_volume=1.5, **kw,
    )  # fmt: skip


# ── Componentes ──────────────────────────────────────────────────────────────
def test_tendencia_completa_y_parcial():
    assert trend_points(perfect()) == 40
    assert trend_points(snap(close=100, ema20=95, ema50=90, ema200=None)) == 12 + 8 + 8
    assert trend_points(snap(close=80, ema20=85, ema50=90, ema200=100)) == 0
    assert trend_points(snap()) == 0


@pytest.mark.parametrize(("adx", "expected"), [(10, 0), (15, 0), (20, 10), (25, 20), (50, 20)])
def test_adx_escala_entre_15_y_25(adx, expected):
    assert adx_points(snap(adx14=adx, plus_di=20, minus_di=10)) == pytest.approx(expected)


def test_adx_no_puntua_si_la_tendencia_es_bajista():
    assert adx_points(snap(adx14=40, plus_di=10, minus_di=30)) == 0
    assert adx_points(snap(adx14=40)) == 0


@pytest.mark.parametrize(
    ("rsi", "expected"),
    [
        (60, 20),
        (55, 20),
        (65, 20),
        (52, 14),
        (68, 14),
        (47, 7),
        (74, 7),
        (30, 0),
        (85, 0),
        (None, 0),
    ],
)
def test_rsi_por_tramos(rsi, expected):
    assert rsi_points(snap(rsi14=rsi)) == expected


@pytest.mark.parametrize(
    ("rv", "expected"), [(2.0, 10), (1.2, 10), (1.0, 7), (0.8, 4), (0.5, 0), (None, 0)]
)
def test_volumen_por_tramos(rv, expected):
    assert volume_points(snap(rel_volume=rv)) == expected


@pytest.mark.parametrize(
    ("atr", "expected"), [(2.5, 10), (1.0, 10), (4.0, 10), (0.6, 5), (6.5, 5), (0.2, 0), (9.0, 0)]
)
def test_atr_por_tramos(atr, expected):
    assert atr_points(snap(close=100.0, atr14=atr)) == expected


# ── Por timeframe ────────────────────────────────────────────────────────────
def test_valor_perfecto_puntua_100_en_cada_timeframe():
    for tf in Timeframe:
        assert score_timeframe(perfect(), tf).score == pytest.approx(100)


def test_el_atr_solo_cuenta_en_el_diario():
    assert "atr" in score_timeframe(perfect(), Timeframe.D1).points
    assert "atr" not in score_timeframe(perfect(), Timeframe.H4).points
    assert "atr" not in score_timeframe(perfect(), Timeframe.H1).points


def test_timeframe_sin_datos_puntua_cero_y_queda_marcado():
    ts = score_timeframe(None, Timeframe.H1)
    assert ts.score == 0 and ts.available is False


# ── Score final ──────────────────────────────────────────────────────────────
def test_score_100_si_todo_es_perfecto():
    r = score_ticker({tf: perfect() for tf in Timeframe}, StrategyParams())
    assert r.score == 100 and r.eligible and r.reason is None


def test_respeta_los_pesos_por_timeframe():
    solo_diario = {Timeframe.D1: perfect(), Timeframe.H4: None, Timeframe.H1: None}
    assert score_ticker(solo_diario, StrategyParams()).score == 50.0
    p = StrategyParams(weight_1d=0.2, weight_4h=0.4, weight_1h=0.4)
    assert score_ticker(solo_diario, p).score == 20.0


def test_sin_historico_diario_no_es_elegible():
    sin_ema200 = perfect()
    sin_ema200 = snap(**{**sin_ema200.__dict__, "ema200": None})
    for diario in (None, sin_ema200):
        r = score_ticker(
            {Timeframe.D1: diario, Timeframe.H4: perfect(), Timeframe.H1: perfect()},
            StrategyParams(),
        )
        assert r.score == 0 and not r.eligible and "diario" in r.reason


def test_el_desglose_se_puede_guardar_como_json():
    r = score_ticker({tf: perfect() for tf in Timeframe}, StrategyParams())
    d = json.loads(json.dumps(r.details()))
    assert d["timeframes"]["1D"]["points"]["trend"] == 40 and d["daily"]["close"] == 110.0


# ── Parámetros ───────────────────────────────────────────────────────────────
def test_parametros_por_defecto_son_los_de_la_estrategia():
    p = StrategyParams()
    assert (p.max_positions, p.max_per_sector, p.min_score) == (8, 3, 80.0)
    assert (p.risk_per_trade, p.sl_atr_mult, p.tp_r_multiple, p.partial_sell_pct) == (
        0.01,
        2.0,
        2.0,
        0.5,
    )
    assert p.weights == {Timeframe.D1: 0.5, Timeframe.H4: 0.3, Timeframe.H1: 0.2}


def test_los_pesos_deben_sumar_uno():
    with pytest.raises(ValidationError, match="sumar 1"):
        StrategyParams(weight_1d=0.5, weight_4h=0.5, weight_1h=0.5)


@pytest.mark.parametrize(
    "bad", [{"min_score": 120}, {"risk_per_trade": 0}, {"max_positions": 0}, {"inventado": 1}]
)
def test_parametros_invalidos_se_rechazan(bad):
    with pytest.raises(ValidationError):
        StrategyParams(**bad)


def test_parametros_ida_y_vuelta_json():
    p = StrategyParams(min_score=70, max_per_sector=2)
    assert StrategyParams.model_validate(json.loads(json.dumps(p.model_dump()))) == p
