"""Utilidades de test: velas simuladas guardadas en la base de datos."""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.models import Timeframe
from app.market_data.provider import Bar
from app.market_data.store import upsert_candles

STEP = {
    Timeframe.D1: timedelta(days=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.H1: timedelta(hours=1),
}


def make_bars(
    tf: Timeframe,
    n: int,
    end: datetime,
    drift: float = 0.003,
    noise: float = 0.006,
    start_price: float = 100.0,
    volume: int = 1_000_000,
    seed: int = 1,
) -> list[Bar]:
    """`n` velas consecutivas; la última EMPIEZA en `end`."""
    rnd = random.Random(seed)
    price = start_price
    bars = []
    for i in range(n):
        ts = end - STEP[tf] * (n - 1 - i)
        o = price
        c = o * (1 + drift + rnd.gauss(0, noise))
        h = max(o, c) * (1 + rnd.uniform(0, noise / 2))
        low = min(o, c) * (1 - rnd.uniform(0, noise / 2))
        vol = int(volume * rnd.uniform(0.9, 1.4))
        bars.append(
            Bar(
                ts,
                Decimal(f"{o:.4f}"),
                Decimal(f"{h:.4f}"),
                Decimal(f"{low:.4f}"),
                Decimal(f"{c:.4f}"),
                vol,
            )
        )
        price = c
    return bars


def seed_ticker(session, ticker, end, drift=0.003, noise=0.006, n=None, seed=1, **kw):
    """Guarda velas 1D/4H/1H terminando en `end`."""
    sizes = n or {Timeframe.D1: 400, Timeframe.H4: 400, Timeframe.H1: 400}
    for tf, count in sizes.items():
        # en intradía la deriva por vela es menor
        d = drift if tf is Timeframe.D1 else drift / 4
        upsert_candles(session, ticker, tf, make_bars(tf, count, end, d, noise, seed=seed, **kw))
