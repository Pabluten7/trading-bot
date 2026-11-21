"""Parámetros de la estrategia, con validación.

Se guardan en `Strategy.params` (JSON). Las estrategias predeterminadas y las
personalizadas (HU-14 y HU-15) son simplemente distintos valores de estos campos.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models import Timeframe


class StrategyParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # ── Selección ────────────────────────────────────────────────────────────
    max_positions: int = Field(8, ge=1, le=50)
    max_per_sector: int = Field(3, ge=1, le=50)
    min_score: float = Field(80.0, ge=0, le=100)

    # ── Scoring: peso de cada timeframe (deben sumar 1) ──────────────────────
    weight_1d: float = Field(0.5, ge=0, le=1)
    weight_4h: float = Field(0.3, ge=0, le=1)
    weight_1h: float = Field(0.2, ge=0, le=1)

    # ── Filtros ──────────────────────────────────────────────────────────────
    benchmark_ticker: str = "SPY"  # el mercado debe estar por encima de su EMA200 diaria
    max_atr_pct: float = Field(5.0, gt=0, le=100)  # ATR diario > X% del precio: no operar
    max_gap_pct: float = Field(3.0, gt=0, le=100)  # |gap| de apertura > X%: no operar
    reentry_wait_candles_1h: int = Field(1, ge=0, le=48)

    # ── Riesgo ───────────────────────────────────────────────────────────────
    risk_per_trade: float = Field(0.01, gt=0, le=0.1)  # fracción del capital arriesgada
    sl_atr_mult: float = Field(2.0, gt=0, le=10)  # stop loss = entrada - N x ATR
    tp_r_multiple: float = Field(2.0, gt=0, le=20)  # take profit = entrada + N x R
    partial_sell_pct: float = Field(0.5, ge=0, le=1)  # fracción que se vende al llegar al TP
    trail_atr_mult: float = Field(2.0, gt=0, le=10)  # trailing stop = máximo - N x ATR
    max_position_pct: float = Field(0.125, gt=0, le=1)  # tope de valor por posición / capital

    @model_validator(mode="after")
    def _pesos_suman_uno(self) -> "StrategyParams":
        total = self.weight_1d + self.weight_4h + self.weight_1h
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Los pesos de los timeframes deben sumar 1 (suman {total:.4f})")
        return self

    @property
    def weights(self) -> dict[Timeframe, float]:
        return {
            Timeframe.D1: self.weight_1d,
            Timeframe.H4: self.weight_4h,
            Timeframe.H1: self.weight_1h,
        }
