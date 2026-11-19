"""
Seed de datos de prueba para desarrollo local.
Ejecutar con: make seed  (o  python -m app.db.seed)
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Candle, Signal, StrategyConfig
from app.db.session import AsyncSessionLocal


TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "JPM", "V", "UNH"]
SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Communication Services", "META": "Communication Services",
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "JPM": "Financials", "V": "Financials", "UNH": "Healthcare",
}

BASE_PRICES = {
    "AAPL": 220.0, "MSFT": 440.0, "NVDA": 130.0, "GOOGL": 185.0, "META": 580.0,
    "AMZN": 210.0, "TSLA": 260.0, "JPM": 230.0, "V": 290.0, "UNH": 580.0,
}


def random_candle(ticker: str, timestamp: datetime, timeframe: str) -> Candle:
    base = BASE_PRICES[ticker]
    drift = random.uniform(-0.02, 0.02)
    open_ = base * (1 + drift)
    close = open_ * (1 + random.uniform(-0.015, 0.015))
    high = max(open_, close) * (1 + random.uniform(0, 0.01))
    low = min(open_, close) * (1 - random.uniform(0, 0.01))
    volume = random.randint(5_000_000, 80_000_000)

    return Candle(
        ticker=ticker,
        timeframe=timeframe,
        timestamp=timestamp,
        open=Decimal(str(round(open_, 4))),
        high=Decimal(str(round(high, 4))),
        low=Decimal(str(round(low, 4))),
        close=Decimal(str(round(close, 4))),
        volume=volume,
    )


async def seed(db: AsyncSession) -> None:
    print("🌱 Iniciando seed...")

    # ── 10 velas diarias por ticker ───────────────────────────────────────────
    now = datetime.now(tz=timezone.utc)
    candles: list[Candle] = []
    for ticker in TICKERS:
        for i in range(10):
            ts = now - timedelta(days=i + 1)
            ts = ts.replace(hour=21, minute=0, second=0, microsecond=0)
            candles.append(random_candle(ticker, ts, "1D"))

    db.add_all(candles)
    print(f"  ✅ {len(candles)} candles insertados")

    # ── Señales del día de hoy ─────────────────────────────────────────────────
    today = now.replace(hour=9, minute=30, second=0, microsecond=0)
    signals: list[Signal] = []
    for ticker in TICKERS:
        score = Decimal(str(round(random.uniform(55.0, 98.0), 2)))
        selected = score >= Decimal("80.0")
        signals.append(Signal(
            ticker=ticker,
            signal_date=today,
            sector=SECTORS.get(ticker),
            score=score,
            score_daily=score * Decimal("0.9"),
            rsi14_daily=Decimal(str(round(random.uniform(45, 70), 2))),
            adx14_daily=Decimal(str(round(random.uniform(20, 45), 2))),
            atr_pct=Decimal(str(round(random.uniform(1.0, 4.5), 2))),
            selected=selected,
            discard_reason=None if selected else "score < 80",
        ))

    db.add_all(signals)
    print(f"  ✅ {len(signals)} signals insertadas")

    # ── Configuración de estrategia por defecto ────────────────────────────────
    config = StrategyConfig(
        name="Swing Trading S&P500 — Default",
        is_active=True,
        max_positions=8,
        max_per_sector=3,
        min_score=Decimal("80.0"),
        risk_per_trade=Decimal("0.01"),
        sl_atr_multiplier=Decimal("2.0"),
        tp_risk_ratio=Decimal("2.0"),
        partial_sell_pct=Decimal("0.50"),
        max_atr_pct=Decimal("5.0"),
        notes="Configuración inicial. Ajustar tras el paper trading.",
    )
    db.add(config)
    print("  ✅ StrategyConfig por defecto creada")

    await db.commit()
    print("✅ Seed completado correctamente.")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
