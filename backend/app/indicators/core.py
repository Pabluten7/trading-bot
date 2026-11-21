"""Funciones puras de indicadores sobre listas de números.

Todas devuelven una lista de la misma longitud que la entrada, con `None` en el
periodo de calentamiento (no hay datos suficientes). Usan el suavizado de Wilder
donde corresponde y siguen la misma convención que TA-Lib (la referencia de la
industria), contra la que están verificadas en los tests.

Convenciones:
- Los índices crecen con el tiempo (el último valor es el más reciente).
- Un indicador en la posición i solo usa datos de las posiciones <= i
  (nunca mira al futuro).
"""

from collections.abc import Sequence

Series = list[float | None]


def sma(values: Sequence[float], period: int) -> Series:
    _check(period, len(values))
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    window = sum(values[:period])
    out[period - 1] = window / period
    for i in range(period, len(values)):
        window += values[i] - values[i - period]
        out[i] = window / period
    return out


def ema(values: Sequence[float], period: int) -> Series:
    """Media móvil exponencial. Se inicia con la media simple de las primeras
    `period` velas y luego aplica alpha = 2 / (period + 1)."""
    _check(period, len(values))
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out[i] = prev
    return out


def rsi(closes: Sequence[float], period: int = 14) -> Series:
    """RSI de Wilder. Primer valor en el índice `period`."""
    _check(period, len(closes))
    out: Series = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 50.0 if avg_gain == 0 else 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def true_range(
    high: Sequence[float], low: Sequence[float], close: Sequence[float]
) -> list[float | None]:
    """Rango verdadero. El primer valor es None porque necesita el cierre anterior."""
    _check_same(high, low, close)
    out: list[float | None] = [None] * len(close)
    for i in range(1, len(close)):
        out[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return out


def atr(
    high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int = 14
) -> Series:
    """ATR de Wilder. Primer valor en el índice `period`."""
    _check(period, len(close))
    tr = true_range(high, low, close)
    out: Series = [None] * len(close)
    if len(close) <= period:
        return out
    prev = sum(tr[1 : period + 1]) / period  # type: ignore[arg-type]
    out[period] = prev
    for i in range(period + 1, len(close)):
        prev = (prev * (period - 1) + tr[i]) / period  # type: ignore[operator]
        out[i] = prev
    return out


def adx(
    high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int = 14
) -> tuple[Series, Series, Series]:
    """ADX de Wilder junto con +DI y -DI. Devuelve (adx, plus_di, minus_di).
    +DI/-DI empiezan en el índice `period`; ADX en `2 * period - 1`."""
    _check(period, len(close))
    n = len(close)
    adx_out: Series = [None] * n
    plus_out: Series = [None] * n
    minus_out: Series = [None] * n
    if n <= period:
        return adx_out, plus_out, minus_out

    tr = true_range(high, low, close)
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0

    # Siembra igual que TA-Lib: suma de las primeras `period - 1` velas; la vela
    # `period` entra ya en el primer paso de suavizado.
    s_tr = sum(tr[1:period])  # type: ignore[arg-type]
    s_plus = sum(plus_dm[1:period])
    s_minus = sum(minus_dm[1:period])
    dx: list[float] = []

    for i in range(period, n):
        s_tr = s_tr - s_tr / period + tr[i]  # type: ignore[operator]
        s_plus = s_plus - s_plus / period + plus_dm[i]
        s_minus = s_minus - s_minus / period + minus_dm[i]
        pdi = 100.0 * s_plus / s_tr if s_tr else 0.0
        mdi = 100.0 * s_minus / s_tr if s_tr else 0.0
        plus_out[i], minus_out[i] = pdi, mdi
        total = pdi + mdi
        dx.append(100.0 * abs(pdi - mdi) / total if total else 0.0)

        if len(dx) == period:
            adx_out[i] = sum(dx) / period
        elif len(dx) > period:
            adx_out[i] = (adx_out[i - 1] * (period - 1) + dx[-1]) / period  # type: ignore[operator]
    return adx_out, plus_out, minus_out


def _check(period: int, length: int) -> None:
    if period < 1:
        raise ValueError("period debe ser >= 1")
    if length < 0:
        raise ValueError("longitud inválida")


def _check_same(*seqs: Sequence[float]) -> None:
    if len({len(s) for s in seqs}) != 1:
        raise ValueError("high, low y close deben tener la misma longitud")
