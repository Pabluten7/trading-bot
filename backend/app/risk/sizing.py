"""Cuántas acciones comprar y dónde poner stop y objetivo.

Reglas:
- R (riesgo por acción) = multiplicador x ATR14 (por defecto 2 x ATR).
- Stop loss   = entrada - R
- Take profit = entrada + 2 x R   (por defecto)
- Acciones    = capital x 1 % / R, redondeado hacia abajo (acciones enteras).

Además se aplican dos topes, porque con stops de 2 x ATR la regla del 1 % por sí
sola daría posiciones enormes (un stop del 4 % implica el 25 % del capital en una
sola acción, y con 8 posiciones se superaría el 100 % del capital):
- Valor de la posición <= `max_position_pct` del capital (por defecto 12,5 % = 1/8).
- Valor de la posición <= efectivo disponible.

Se redondea siempre en contra de nosotros (el stop hacia abajo, las acciones hacia
abajo) para no arriesgar más de lo previsto.
"""

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.strategy.params import StrategyParams

CENT = Decimal("0.01")
# Un stop a menos del 0,5 % del precio salta por puro ruido: se rechaza el plan.
MIN_STOP_DISTANCE_PCT = Decimal("0.005")


@dataclass(frozen=True)
class TradePlan:
    ticker: str
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    quantity: int
    risk_per_share: Decimal  # R
    risk_amount: Decimal  # riesgo real = cantidad x R
    position_value: Decimal
    atr: Decimal
    limited_by: str  # qué regla fijó la cantidad: "riesgo", "tope_posicion" o "efectivo"


@dataclass(frozen=True)
class SizingResult:
    plan: TradePlan | None
    reason: str | None = None


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def plan_trade(
    ticker: str,
    entry_price,
    atr,
    equity,
    cash,
    params: StrategyParams,
) -> SizingResult:
    entry = _dec(entry_price).quantize(CENT, ROUND_HALF_UP)
    atr = _dec(atr)
    equity, cash = _dec(equity), _dec(cash)

    if entry <= 0 or atr <= 0:
        return SizingResult(None, "precio o ATR no válidos")
    if equity <= 0:
        return SizingResult(None, "capital no válido")

    stop = (entry - _dec(params.sl_atr_mult) * atr).quantize(CENT, ROUND_DOWN)
    if stop <= 0:
        return SizingResult(None, "ATR demasiado grande: el stop quedaría en cero o negativo")
    r = entry - stop
    if r < entry * MIN_STOP_DISTANCE_PCT:
        return SizingResult(None, "ATR demasiado pequeño: el stop quedaría pegado a la entrada")
    take_profit = (entry + _dec(params.tp_r_multiple) * r).quantize(CENT, ROUND_HALF_UP)

    limits = {
        "riesgo": int(equity * _dec(params.risk_per_trade) / r),
        "tope_posicion": int(equity * _dec(params.max_position_pct) / entry),
        "efectivo": int(cash / entry) if cash > 0 else 0,
    }
    limited_by = min(limits, key=lambda k: limits[k])
    qty = limits[limited_by]
    if qty < 1:
        return SizingResult(None, f"no alcanza para 1 acción (límite: {limited_by})")

    return SizingResult(
        TradePlan(
            ticker=ticker,
            entry_price=entry,
            stop_loss=stop,
            take_profit=take_profit,
            quantity=qty,
            risk_per_share=r,
            risk_amount=r * qty,
            position_value=entry * qty,
            atr=atr,
            limited_by=limited_by,
        )
    )
