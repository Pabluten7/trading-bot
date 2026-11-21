"""Cálculo de todos los indicadores de la estrategia sobre una serie de velas."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.indicators import core

VOLUME_AVG_PERIOD = 20


@dataclass(frozen=True)
class Ohlcv:
    """Vela con números en coma flotante, lista para calcular indicadores."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def from_candles(candles: Sequence) -> list[Ohlcv]:
    """Convierte velas de la base de datos (`Candle`) a `Ohlcv`, ordenadas por fecha."""
    bars = [
        Ohlcv(
            _utc(c.timestamp),
            float(c.open),
            float(c.high),
            float(c.low),
            float(c.close),
            float(c.volume),
        )
        for c in candles
    ]
    bars.sort(key=lambda b: b.timestamp)
    return bars


def _utc(dt: datetime) -> datetime:
    """SQLite devuelve fechas sin zona horaria: siempre las tratamos como UTC."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


@dataclass(frozen=True)
class IndicatorSnapshot:
    """Valor de todos los indicadores en una vela concreta. `None` = sin datos suficientes."""

    timestamp: datetime
    close: float
    volume: float
    ema20: float | None
    ema50: float | None
    ema200: float | None
    rsi14: float | None
    adx14: float | None
    plus_di: float | None
    minus_di: float | None
    atr14: float | None
    rel_volume: float | None  # volumen / media de las 20 velas anteriores

    @property
    def atr_pct(self) -> float | None:
        """ATR como % del cierre."""
        if self.atr14 is None or self.close <= 0:
            return None
        return 100.0 * self.atr14 / self.close

    @property
    def is_complete(self) -> bool:
        return None not in (
            self.ema20,
            self.ema50,
            self.ema200,
            self.rsi14,
            self.adx14,
            self.plus_di,
            self.minus_di,
            self.atr14,
            self.rel_volume,
        )


@dataclass(frozen=True)
class IndicatorSeries:
    """Indicadores de toda la serie. Calcúlalos una vez y consulta `at(i)` tantas
    veces como necesites (p. ej. en un backtest)."""

    bars: list[Ohlcv]
    ema20: core.Series
    ema50: core.Series
    ema200: core.Series
    rsi14: core.Series
    adx14: core.Series
    plus_di: core.Series
    minus_di: core.Series
    atr14: core.Series
    rel_volume: core.Series

    def __len__(self) -> int:
        return len(self.bars)

    def at(self, i: int) -> IndicatorSnapshot:
        if i < 0:
            i += len(self.bars)
        b = self.bars[i]
        return IndicatorSnapshot(
            timestamp=b.timestamp,
            close=b.close,
            volume=b.volume,
            ema20=self.ema20[i],
            ema50=self.ema50[i],
            ema200=self.ema200[i],
            rsi14=self.rsi14[i],
            adx14=self.adx14[i],
            plus_di=self.plus_di[i],
            minus_di=self.minus_di[i],
            atr14=self.atr14[i],
            rel_volume=self.rel_volume[i],
        )

    def last(self) -> IndicatorSnapshot | None:
        return self.at(-1) if self.bars else None


def compute_series(bars: Sequence[Ohlcv]) -> IndicatorSeries:
    bars = list(bars)
    high = [b.high for b in bars]
    low = [b.low for b in bars]
    close = [b.close for b in bars]
    volume = [b.volume for b in bars]
    adx14, plus_di, minus_di = core.adx(high, low, close, 14)

    vol_avg = core.sma(volume, VOLUME_AVG_PERIOD)
    rel_volume: core.Series = [None] * len(bars)
    for i in range(1, len(bars)):
        prev_avg = vol_avg[i - 1]  # media de las 20 velas ANTERIORES (sin la actual)
        if prev_avg:
            rel_volume[i] = volume[i] / prev_avg

    return IndicatorSeries(
        bars=bars,
        ema20=core.ema(close, 20),
        ema50=core.ema(close, 50),
        ema200=core.ema(close, 200),
        rsi14=core.rsi(close, 14),
        adx14=adx14,
        plus_di=plus_di,
        minus_di=minus_di,
        atr14=core.atr(high, low, close, 14),
        rel_volume=rel_volume,
    )
