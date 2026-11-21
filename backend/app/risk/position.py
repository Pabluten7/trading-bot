"""Gestión de una posición abierta, vela a vela.

Reglas (solo LONG):
1. Stop loss inicial = entrada - 2 x ATR.
2. Al llegar al take profit (+2R) se vende el 50 % y el resto sigue abierto.
3. Tras la venta parcial el stop sube a break-even (precio de entrada) y pasa a ser
   un trailing stop: máximo alcanzado - 2 x ATR (con el ATR de la entrada). El stop
   solo sube, nunca baja.

Reglas de simulación (pensadas para no ser optimistas):
- Los niveles de stop que se usan en una vela son los fijados al cierre de la ANTERIOR;
  el máximo de la vela actual solo sube el stop para las velas siguientes.
- Si en una misma vela se tocan el stop y el objetivo, se asume que saltó el stop.
- Si la vela abre más allá del stop (hueco a la baja) se sale a la apertura, no al
  precio del stop. Si abre por encima del objetivo, se vende a la apertura.
"""

import enum
from dataclasses import dataclass
from decimal import Decimal

from app.risk.sizing import TradePlan
from app.strategy.params import StrategyParams


class FillKind(enum.StrEnum):
    STOP_LOSS = "stop_loss"  # salida total por el stop inicial
    PARTIAL_TP = "partial_tp"  # venta parcial en el objetivo
    TAKE_PROFIT = "take_profit"  # salida total en el objetivo (no se pudo dividir)
    TRAILING_STOP = "trailing_stop"  # salida del resto tras la venta parcial
    MANUAL = "manual"  # cierre decidido por nosotros (p. ej. fin de un backtest)


@dataclass(frozen=True)
class Fill:
    kind: FillKind
    price: Decimal
    quantity: int


@dataclass
class PositionState:
    ticker: str
    entry_price: Decimal
    quantity: int
    remaining: int
    stop: Decimal
    take_profit: Decimal
    atr: Decimal  # ATR en la entrada (fijo durante la operación)
    partial_done: bool = False
    highest: Decimal | None = None

    def __post_init__(self) -> None:
        if self.highest is None:
            self.highest = self.entry_price

    @classmethod
    def from_plan(cls, plan: TradePlan, quantity: int | None = None) -> "PositionState":
        q = plan.quantity if quantity is None else quantity
        return cls(
            ticker=plan.ticker,
            entry_price=plan.entry_price,
            quantity=q,
            remaining=q,
            stop=plan.stop_loss,
            take_profit=plan.take_profit,
            atr=plan.atr,
        )

    @property
    def is_open(self) -> bool:
        return self.remaining > 0


def advance(state: PositionState, open_, high, low, close, params: StrategyParams) -> list[Fill]:
    """Procesa una vela y devuelve las ventas que ocurren en ella (puede ser ninguna)."""
    if not state.is_open:
        return []
    open_, high, low = Decimal(str(open_)), Decimal(str(high)), Decimal(str(low))
    fills: list[Fill] = []

    # 1) Stop (con el nivel vigente al empezar la vela)
    if low <= state.stop:
        price = min(open_, state.stop)
        kind = FillKind.TRAILING_STOP if state.partial_done else FillKind.STOP_LOSS
        fills.append(Fill(kind, price, state.remaining))
        state.remaining = 0
        return fills

    # 2) Objetivo: venta parcial (solo la primera vez)
    if not state.partial_done and high >= state.take_profit:
        price = max(open_, state.take_profit)
        pct = Decimal(str(params.partial_sell_pct))
        sell_qty = int(state.quantity * pct)
        if pct > 0 and (sell_qty < 1 or sell_qty >= state.remaining):
            # no se puede dividir (p. ej. 1 acción) o se vende todo: salida completa
            fills.append(Fill(FillKind.TAKE_PROFIT, price, state.remaining))
            state.remaining = 0
            return fills
        if sell_qty >= 1:
            fills.append(Fill(FillKind.PARTIAL_TP, price, sell_qty))
            state.remaining -= sell_qty
        state.partial_done = True  # con pct = 0 no se vende nada, pero empieza el trailing
        state.stop = max(state.stop, state.entry_price)  # break-even

    # 3) Trailing (con el máximo de esta vela, para las siguientes)
    if state.partial_done:
        state.highest = max(state.highest, high)
        trail = state.highest - Decimal(str(params.trail_atr_mult)) * state.atr
        state.stop = max(state.stop, trail, state.entry_price)
    return fills


def realized_pnl(entry_price: Decimal, fills: list[Fill]) -> Decimal:
    """Beneficio o pérdida (sin comisiones) de un conjunto de ventas."""
    return sum(((f.price - entry_price) * f.quantity for f in fills), Decimal(0))
