import random
from datetime import UTC, datetime, timedelta

import pytest

from app.indicators import compute_series, core
from app.indicators.series import Ohlcv

# Valores calculados con TA-Lib sobre la serie simulada de abajo (semilla 7).
GOLDEN = {
    250: {
        "ema20": 86.0817340925,
        "ema50": 86.1987353101,
        "ema200": 91.6025086838,
        "rsi14": 61.8207571489,
        "atr14": 1.6661194446,
        "adx14": 19.8589757401,
        "plus_di": 35.3865558075,
        "minus_di": 14.9110893412,
    },
    599: {
        "ema20": 180.4958067324,
        "ema50": 172.1098799762,
        "ema200": 141.7366860916,
        "rsi14": 54.4756787915,
        "atr14": 3.3394982523,
        "adx14": 46.9755534692,
        "plus_di": 31.3687948495,
        "minus_di": 15.2345999074,
    },
}


def simulated(n=600, seed=7):
    rnd = random.Random(seed)
    closes, highs, lows = [], [], []
    prev = 100.0
    for _ in range(n):
        o = prev * (1 + rnd.uniform(-0.01, 0.01))
        c = o * (1 + rnd.gauss(0.0003, 0.012))
        highs.append(max(o, c) * (1 + rnd.uniform(0, 0.008)))
        lows.append(min(o, c) * (1 - rnd.uniform(0, 0.008)))
        closes.append(c)
        prev = c
    return highs, lows, closes


@pytest.fixture(scope="module")
def data():
    return simulated()


def _all(data):
    h, low, c = data
    adx, pdi, mdi = core.adx(h, low, c, 14)
    return {
        "ema20": core.ema(c, 20),
        "ema50": core.ema(c, 50),
        "ema200": core.ema(c, 200),
        "rsi14": core.rsi(c, 14),
        "atr14": core.atr(h, low, c, 14),
        "adx14": adx,
        "plus_di": pdi,
        "minus_di": mdi,
    }


@pytest.mark.parametrize("idx", sorted(GOLDEN))
def test_coincide_con_talib(data, idx):
    got = _all(data)
    for name, expected in GOLDEN[idx].items():
        assert got[name][idx] == pytest.approx(expected, abs=1e-8), name


@pytest.mark.parametrize(
    ("name", "first"),
    [
        ("ema20", 19),
        ("ema50", 49),
        ("ema200", 199),
        ("rsi14", 14),
        ("atr14", 14),
        ("adx14", 27),
        ("plus_di", 14),
        ("minus_di", 14),
    ],
)
def test_periodo_de_calentamiento(data, name, first):
    s = _all(data)[name]
    assert all(v is None for v in s[:first]) and s[first] is not None and len(s) == 600


def test_no_mira_al_futuro(data):
    """El valor en la posición i no cambia aunque se añadan velas posteriores."""
    h, low, c = data
    corto = core.adx(h[:300], low[:300], c[:300], 14)[0]
    largo = core.adx(h, low, c, 14)[0]
    assert corto == largo[:300]
    assert core.ema(c[:300], 50) == core.ema(c, 50)[:300]
    assert core.rsi(c[:300]) == core.rsi(c)[:300]


# ── Casos calculados a mano ──────────────────────────────────────────────────
def test_sma_a_mano():
    assert core.sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_ema_a_mano():
    # semilla = media(1,2,3)=2 ; alpha=0.5 ; siguiente = 0.5*4+0.5*2 = 3
    assert core.ema([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_rsi_extremos():
    assert core.rsi([float(i) for i in range(1, 40)])[-1] == 100.0
    assert core.rsi([float(i) for i in range(40, 1, -1)])[-1] == 0.0
    assert core.rsi([5.0] * 40)[-1] == 50.0


def test_atr_con_rango_constante():
    n = 30
    high, low, close = [11.0] * n, [9.0] * n, [10.0] * n
    assert core.atr(high, low, close, 14)[-1] == pytest.approx(2.0)


def test_true_range_incluye_gaps():
    tr = core.true_range([10, 15], [9, 14], [9.5, 14.5])
    assert tr == [None, 5.5]  # el hueco desde el cierre anterior (9.5) hasta el máximo 15


def test_adx_alto_en_tendencia_y_bajo_sin_ella():
    n = 120
    up = [float(i) for i in range(n)]
    adx_up, pdi, mdi = core.adx([x + 1 for x in up], up, up, 14)
    assert adx_up[-1] > 90 and pdi[-1] > mdi[-1]
    flat = [10.0 + (1 if i % 2 else -1) for i in range(n)]
    adx_flat, _, _ = core.adx([x + 0.5 for x in flat], [x - 0.5 for x in flat], flat, 14)
    assert adx_flat[-1] < 15


def test_series_demasiado_cortas_no_fallan():
    for fn in (core.ema, core.rsi):
        assert fn([1.0, 2.0], 14) == [None, None]
    assert core.atr([1.0], [1.0], [1.0]) == [None]
    assert core.adx([], [], []) == ([], [], [])


def test_longitudes_distintas_dan_error():
    with pytest.raises(ValueError):
        core.atr([1.0, 2.0], [1.0], [1.0, 2.0])


# ── Series e instantáneas ────────────────────────────────────────────────────
def _bars(n, seed=7):
    h, low, c = simulated(n, seed)
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    return [Ohlcv(t0 + timedelta(days=i), c[i], h[i], low[i], c[i], 1000.0 + i) for i in range(n)]


def test_snapshot_completo_con_historial_suficiente():
    s = compute_series(_bars(300)).last()
    assert s.is_complete and s.atr_pct is not None and 0 < s.atr_pct < 10


def test_snapshot_incompleto_con_poco_historial():
    s = compute_series(_bars(100)).last()
    assert s.ema200 is None and not s.is_complete
    assert s.ema50 is not None


def test_volumen_relativo_usa_las_20_velas_anteriores():
    bars = _bars(40)
    bars = [
        Ohlcv(b.timestamp, b.open, b.high, b.low, b.close, 1000.0 if i < 39 else 3000.0)
        for i, b in enumerate(bars)
    ]
    series = compute_series(bars)
    assert series.at(39).rel_volume == pytest.approx(3.0)  # 3000 / media(1000 x 20)
    assert series.at(10).rel_volume is None


def test_at_acepta_indices_negativos_y_serie_vacia():
    series = compute_series(_bars(50))
    assert series.at(-1) == series.at(49)
    assert compute_series([]).last() is None


def test_from_candles_normaliza_fechas_sin_zona_a_utc():
    from decimal import Decimal

    from app.db.models import Candle, Timeframe
    from app.indicators import from_candles

    naive = datetime(2026, 1, 5, 5, 0)  # así las devuelve SQLite
    c = Candle(
        ticker="A", timeframe=Timeframe.D1, timestamp=naive,
        open=Decimal(1), high=Decimal(2), low=Decimal(1), close=Decimal(2), volume=5,
    )  # fmt: skip
    assert from_candles([c])[0].timestamp == datetime(2026, 1, 5, 5, 0, tzinfo=UTC)
