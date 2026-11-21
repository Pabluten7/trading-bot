import random
from decimal import Decimal

import pytest

from app.risk import plan_trade
from app.strategy.params import StrategyParams

P = StrategyParams()
D = Decimal


def test_ejemplo_base_limitado_por_el_tope_de_posicion():
    # capital 100.000; entrada 100; ATR 2 -> R = 4; stop 96; objetivo 108
    r = plan_trade("AAPL", 100, 2, 100_000, 100_000, P)
    p = r.plan
    assert (p.stop_loss, p.take_profit, p.risk_per_share) == (D("96.00"), D("108.00"), D("4.00"))
    # por riesgo serían 250 acciones, pero el tope del 12,5 % lo deja en 125
    assert p.quantity == 125 and p.limited_by == "tope_posicion"
    assert p.position_value == D("12500.00") and p.risk_amount == D("500.00")


def test_sin_tope_manda_la_regla_del_1_por_ciento():
    p = plan_trade("AAPL", 100, 2, 100_000, 100_000, StrategyParams(max_position_pct=1.0)).plan
    assert p.quantity == 250 and p.limited_by == "riesgo"
    assert p.risk_amount == D("1000.00")  # exactamente el 1 % del capital


def test_el_efectivo_disponible_limita():
    p = plan_trade("AAPL", 100, 2, 100_000, 5_000, P).plan
    assert p.quantity == 50 and p.limited_by == "efectivo"


def test_stop_y_objetivo_se_redondean_a_centimos_en_contra():
    p = plan_trade("X", "123.456", "1.111", 1_000_000, 1_000_000, P).plan
    assert p.entry_price == D("123.46")
    assert p.stop_loss == D("121.23")  # 123.46 - 2.222 = 121.238 -> hacia abajo
    assert p.risk_per_share == p.entry_price - p.stop_loss == D("2.23")
    assert p.take_profit == D("123.46") + 2 * D("2.23") == D("127.92")


def test_parametros_de_riesgo_se_respetan():
    prm = StrategyParams(sl_atr_mult=1.5, tp_r_multiple=3.0, max_position_pct=1.0)
    p = plan_trade("X", 50, 1, 100_000, 100_000, prm).plan
    assert p.stop_loss == D("48.50") and p.take_profit == D("54.50")


@pytest.mark.parametrize(
    ("entry", "atr", "equity", "cash", "texto"),
    [
        (100, 60, 100_000, 100_000, "demasiado grande"),  # stop negativo
        (500, 5, 1_000, 1_000, "1 acción"),  # no alcanza ni para una
        (100, 2, 100_000, 0, "efectivo"),
        (0, 2, 100_000, 100_000, "no válidos"),
        (100, 0, 100_000, 100_000, "no válidos"),
        (100, 2, 0, 0, "capital"),
        (100, "0.001", 100_000, 100_000, "pequeño"),
    ],
)
def test_rechaza_casos_imposibles_con_motivo(entry, atr, equity, cash, texto):
    r = plan_trade("X", entry, atr, equity, cash, P)
    assert r.plan is None and texto in r.reason


def test_invariantes_con_muchos_casos_aleatorios():
    rnd = random.Random(11)
    for _ in range(3000):
        entry = rnd.uniform(5, 900)
        atr = entry * rnd.uniform(0.003, 0.09)
        equity = rnd.uniform(5_000, 2_000_000)
        cash = equity * rnd.uniform(0.05, 1.0)
        prm = StrategyParams(max_position_pct=rnd.choice([0.05, 0.125, 0.25, 1.0]))
        r = plan_trade("X", entry, atr, equity, cash, prm)
        if r.plan is None:
            continue
        p = r.plan
        assert isinstance(p.quantity, int) and p.quantity >= 1
        assert 0 < p.stop_loss < p.entry_price < p.take_profit
        assert p.risk_amount <= D(str(equity)) * D("0.01") + D("0.0001")  # nunca más del 1 %
        assert p.position_value <= D(str(equity)) * D(str(prm.max_position_pct))
        assert p.position_value <= D(str(cash))
        assert p.take_profit - p.entry_price >= 2 * p.risk_per_share - D("0.01")


def test_ocho_posiciones_no_superan_el_capital_con_los_valores_por_defecto():
    """La razón de ser del tope: 8 posiciones a tope no pueden pasar del 100 %."""
    p = plan_trade("X", 100, 1.5, 100_000, 100_000, P).plan  # stop del 3 %
    assert 8 * p.position_value <= D(100_000)
