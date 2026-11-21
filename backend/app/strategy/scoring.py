"""Scoring 0-100 de un valor a partir de sus indicadores en 3 timeframes.

Cada timeframe se puntúa de 0 a 100 con estos componentes (solo LONG):

| Componente | Puntos | Qué premia                                                     |
|------------|--------|----------------------------------------------------------------|
| Tendencia  | 40     | EMA20>EMA50 (12), EMA50>EMA200 (12), precio>EMA20 (8), >EMA50 (8) |
| ADX        | 20     | Fuerza de tendencia (15→25), solo si +DI > -DI                  |
| RSI        | 20     | Momento sano: 55-65 (20), 50-70 (14), 45-75 (7)                 |
| Volumen    | 10     | Volumen relativo: >=1.2 (10), >=1.0 (7), >=0.8 (4)             |
| ATR        | 10     | Volatilidad útil 1-4 % (10), 0.5-7 % (5). Solo en el diario     |

El score final es la media ponderada de los tres timeframes (por defecto
50 % diario, 30 % 4H, 20 % 1H). El ATR solo puntúa en el diario porque sus
umbrales en % no son comparables con los de velas horarias; en 4H y 1H la
puntuación se reescala sobre los puntos que sí aplican.
"""

from dataclasses import dataclass, field

from app.db.models import Timeframe
from app.indicators import IndicatorSnapshot
from app.strategy.params import StrategyParams

MAX_POINTS = {"trend": 40.0, "adx": 20.0, "rsi": 20.0, "volume": 10.0, "atr": 10.0}
COMPONENTS_BY_TIMEFRAME = {
    Timeframe.D1: ("trend", "adx", "rsi", "volume", "atr"),
    Timeframe.H4: ("trend", "adx", "rsi", "volume"),
    Timeframe.H1: ("trend", "adx", "rsi", "volume"),
}


def trend_points(s: IndicatorSnapshot) -> float:
    pts = 0.0
    if s.ema20 is not None and s.ema50 is not None and s.ema20 > s.ema50:
        pts += 12
    if s.ema50 is not None and s.ema200 is not None and s.ema50 > s.ema200:
        pts += 12
    if s.ema20 is not None and s.close > s.ema20:
        pts += 8
    if s.ema50 is not None and s.close > s.ema50:
        pts += 8
    return pts


def adx_points(s: IndicatorSnapshot) -> float:
    if s.adx14 is None or s.plus_di is None or s.minus_di is None:
        return 0.0
    if s.plus_di <= s.minus_di:  # tendencia bajista: no puntúa para largos
        return 0.0
    return MAX_POINTS["adx"] * min(max((s.adx14 - 15.0) / 10.0, 0.0), 1.0)


def rsi_points(s: IndicatorSnapshot) -> float:
    r = s.rsi14
    if r is None:
        return 0.0
    if 55 <= r <= 65:
        return 20.0
    if 50 <= r <= 70:
        return 14.0
    if 45 <= r <= 75:
        return 7.0
    return 0.0


def volume_points(s: IndicatorSnapshot) -> float:
    v = s.rel_volume
    if v is None:
        return 0.0
    if v >= 1.2:
        return 10.0
    if v >= 1.0:
        return 7.0
    if v >= 0.8:
        return 4.0
    return 0.0


def atr_points(s: IndicatorSnapshot) -> float:
    pct = s.atr_pct
    if pct is None:
        return 0.0
    if 1.0 <= pct <= 4.0:
        return 10.0
    if 0.5 <= pct <= 7.0:
        return 5.0
    return 0.0


_FUNCS = {
    "trend": trend_points,
    "adx": adx_points,
    "rsi": rsi_points,
    "volume": volume_points,
    "atr": atr_points,
}


@dataclass(frozen=True)
class TimeframeScore:
    timeframe: Timeframe
    score: float  # 0-100
    points: dict[str, float]
    available: bool  # había datos para este timeframe


def score_timeframe(snapshot: IndicatorSnapshot | None, timeframe: Timeframe) -> TimeframeScore:
    comps = COMPONENTS_BY_TIMEFRAME[timeframe]
    if snapshot is None:
        return TimeframeScore(timeframe, 0.0, {c: 0.0 for c in comps}, available=False)
    points = {c: round(_FUNCS[c](snapshot), 4) for c in comps}
    maximum = sum(MAX_POINTS[c] for c in comps)
    return TimeframeScore(timeframe, 100.0 * sum(points.values()) / maximum, points, True)


@dataclass(frozen=True)
class ScoreResult:
    score: float  # 0-100, 2 decimales
    eligible: bool  # False si falta el histórico diario mínimo
    reason: str | None
    by_timeframe: dict[Timeframe, TimeframeScore] = field(default_factory=dict)
    daily: IndicatorSnapshot | None = None

    def details(self) -> dict:
        """Desglose en formato JSON para guardar en `Signal.details`."""
        d = self.daily
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "timeframes": {
                tf.value: {
                    "score": round(ts.score, 2),
                    "available": ts.available,
                    "points": ts.points,
                }
                for tf, ts in self.by_timeframe.items()
            },
            "daily": None
            if d is None
            else {
                "close": d.close,
                "ema20": d.ema20,
                "ema50": d.ema50,
                "ema200": d.ema200,
                "rsi14": d.rsi14,
                "adx14": d.adx14,
                "atr14": d.atr14,
                "atr_pct": d.atr_pct,
                "rel_volume": d.rel_volume,
            },
        }


def score_ticker(
    snapshots: dict[Timeframe, IndicatorSnapshot | None],
    params: StrategyParams,
    renormalize_missing: bool = False,
) -> ScoreResult:
    """Combina los 3 timeframes. Sin velas diarias suficientes (EMA200 y ATR)
    el valor no es puntuable: score 0 y `eligible=False`.

    Con `renormalize_missing=True` los timeframes sin datos no cuentan como 0: sus
    pesos se reparten entre los que sí tienen datos (útil en backtests sin histórico
    intradía). En el bot real se deja en False: faltar un timeframe es un problema."""
    by_tf = {tf: score_timeframe(snapshots.get(tf), tf) for tf in Timeframe}
    daily = snapshots.get(Timeframe.D1)
    if daily is None or daily.ema200 is None or daily.atr14 is None:
        return ScoreResult(0.0, False, "histórico diario insuficiente", by_tf, daily)
    if renormalize_missing:
        used = [tf for tf in Timeframe if by_tf[tf].available]
        weight = sum(params.weights[tf] for tf in used)
        total = sum(params.weights[tf] * by_tf[tf].score for tf in used) / weight if weight else 0.0
    else:
        total = sum(params.weights[tf] * by_tf[tf].score for tf in Timeframe)
    return ScoreResult(round(min(max(total, 0.0), 100.0), 2), True, None, by_tf, daily)
