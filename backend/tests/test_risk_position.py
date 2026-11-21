from decimal import Decimal

import pytest

from app.risk import FillKind, PositionState, advance, plan_trade, realized_pnl
from app.strategy.params import StrategyParams

D = Decimal
P = StrategyParams()


def pos(qty=100, entry=100, atr=2, params=P) -> PositionState:
    """Entrada 100, ATR 2 -> stop 96, objetivo 108 (R = 4)."""
    plan = plan_trade("X", entry, atr, 1_000_000, 1_000_000, StrategyParams(max_position_pct=1.0))
    return PositionState.from_plan(plan.plan, quantity=qty)


def bar(s, o, h, low, c, params=P):
    return advance(s, o, h, low, c, params)


def test_estado_inicial():
    s = pos()
    assert (s.stop, s.take_profit, s.remaining, s.partial_done) == (D(96), D(108), 100, False)
    assert s.is_open and s.highest == D(100)


def test_velas_tranquilas_no_hacen_nada():
    s = pos()
    assert bar(s, 100, 104, 98, 103) == [] and bar(s, 103, 106, 99, 100) == []
    assert s.remaining == 100 and s.stop == D(96)


def test_salta_el_stop_inicial_pierde_1r_por_accion():
    s = pos()
    fills = bar(s, 99, 100, 95, 96)
    assert [(f.kind, f.price, f.quantity) for f in fills] == [(FillKind.STOP_LOSS, D(96), 100)]
    assert not s.is_open and realized_pnl(s.entry_price, fills) == D(-400)  # 100 acc x -4


def test_hueco_a_la_baja_sale_a_la_apertura_no_al_stop():
    s = pos()
    fills = bar(s, 90, 91, 88, 89)  # abre por debajo del stop (96)
    assert fills[0].price == D(90) and fills[0].kind is FillKind.STOP_LOSS


def test_al_llegar_al_objetivo_vende_la_mitad_y_sube_a_break_even():
    s = pos()
    fills = bar(s, 105, 109, 104, 108)
    assert [(f.kind, f.price, f.quantity) for f in fills] == [(FillKind.PARTIAL_TP, D(108), 50)]
    assert s.remaining == 50 and s.partial_done
    assert s.stop >= s.entry_price  # nunca por debajo de la entrada
    # trailing: máximo 109 - 2 x ATR(2) = 105
    assert s.stop == D(105) and s.highest == D(109)


def test_hueco_al_alza_por_encima_del_objetivo_vende_a_la_apertura():
    s = pos()
    assert bar(s, 112, 115, 111, 114)[0].price == D(112)


def test_stop_y_objetivo_en_la_misma_vela_gana_el_stop():
    s = pos()
    fills = bar(s, 100, 110, 95, 100)  # toca 96 y 108 a la vez
    assert fills[0].kind is FillKind.STOP_LOSS and not s.is_open


def test_el_trailing_solo_sube_y_acaba_saliendo_en_beneficio():
    s = pos()
    bar(s, 105, 109, 104, 108)  # parcial; stop 105
    bar(s, 108, 115, 107, 114)  # máximo 115 -> stop 111
    assert s.stop == D(111)
    bar(s, 114, 114.5, 110.5 + 1, 112)  # sin tocar el stop
    assert s.stop == D(111)  # no baja aunque el máximo no mejore
    fills = bar(s, 112, 113, 110, 111)  # toca 111
    assert [(f.kind, f.price, f.quantity) for f in fills] == [(FillKind.TRAILING_STOP, D(111), 50)]
    assert not s.is_open


def test_el_trailing_no_actua_en_la_misma_vela_que_lo_sube():
    """Sin mirar al futuro: el máximo de una vela no puede sacarte en esa misma vela."""
    s = pos()
    bar(s, 105, 109, 104, 108)  # parcial
    # vela con máximo enorme y mínimo bajo: el stop vigente era 105 y el mínimo 106 lo respeta
    assert bar(s, 107, 130, 106, 107) == []
    assert s.stop == D(130) - 2 * D(2)  # 126 para las siguientes velas
    assert bar(s, 125, 126, 120, 121)[0].price == D(125)  # abre bajo el stop: sale a la apertura


def test_resultado_completo_de_una_operacion_ganadora():
    s = pos()
    todas = bar(s, 105, 109, 104, 108) + bar(s, 108, 115, 107, 114) + bar(s, 112, 113, 110, 111)
    # 50 x (108-100) + 50 x (111-100) = 400 + 550
    assert realized_pnl(s.entry_price, todas) == D(950)


def test_una_sola_accion_sale_completa_en_el_objetivo():
    s = pos(qty=1)
    fills = bar(s, 105, 109, 104, 108)
    assert [(f.kind, f.quantity) for f in fills] == [(FillKind.TAKE_PROFIT, 1)] and not s.is_open


def test_tres_acciones_venden_una_en_el_parcial():
    s = pos(qty=3)
    assert bar(s, 105, 109, 104, 108)[0].quantity == 1 and s.remaining == 2  # floor(3 x 0,5)


def test_parcial_del_100_por_ciento_es_salida_completa():
    s = pos(params=P)
    fills = bar(s, 105, 109, 104, 108, StrategyParams(partial_sell_pct=1.0))
    assert fills[0].kind is FillKind.TAKE_PROFIT and not s.is_open


def test_parcial_cero_no_vende_pero_empieza_el_trailing():
    prm = StrategyParams(partial_sell_pct=0.0)
    s = pos()
    assert bar(s, 105, 109, 104, 108, prm) == []
    assert s.remaining == 100 and s.partial_done and s.stop == D(105)


def test_posicion_cerrada_ignora_nuevas_velas():
    s = pos()
    bar(s, 99, 100, 95, 96)
    assert bar(s, 50, 60, 40, 55) == []


def test_el_stop_nunca_baja_en_ninguna_secuencia():
    import random

    rnd = random.Random(3)
    for _ in range(300):
        s = pos(qty=rnd.randint(1, 500))
        last = s.stop
        price = 100.0
        for _ in range(60):
            o = price * (1 + rnd.uniform(-0.02, 0.02))
            c = o * (1 + rnd.uniform(-0.03, 0.03))
            h, low = max(o, c) * 1.01, min(o, c) * 0.99
            bar(s, o, h, low, c)
            assert s.stop >= last
            last = s.stop
            price = c
            if not s.is_open:
                break


def test_la_perdida_maxima_es_el_riesgo_previsto_salvo_huecos():
    plan = plan_trade("X", 100, 2, 100_000, 100_000, P).plan
    s = PositionState.from_plan(plan)
    fills = bar(s, 99, 100, 90, 95)
    assert -realized_pnl(plan.entry_price, fills) == pytest.approx(plan.risk_amount)
