from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import Candle, Timeframe
from app.market_data.provider import Bar
from app.market_data.store import last_timestamp, load_candles, upsert_candles

T0 = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)


def bar(day=0, o="100", h="102", low="99", c="101", v=1000):
    return Bar(T0 + timedelta(days=day), Decimal(o), Decimal(h), Decimal(low), Decimal(c), v)


def _count(session):
    return session.scalar(select(func.count()).select_from(Candle))


def test_inserta_velas(session):
    r = upsert_candles(session, "AAPL", Timeframe.D1, [bar(0), bar(1)])
    assert (r.inserted, r.updated) == (2, 0) and _count(session) == 2


def test_es_idempotente(session):
    upsert_candles(session, "AAPL", Timeframe.D1, [bar(0), bar(1)])
    r = upsert_candles(session, "AAPL", Timeframe.D1, [bar(0), bar(1)])
    assert (r.inserted, r.updated) == (0, 0) and _count(session) == 2


def test_actualiza_una_vela_que_cambio(session):
    upsert_candles(session, "AAPL", Timeframe.D1, [bar(0, c="101")])
    r = upsert_candles(session, "AAPL", Timeframe.D1, [bar(0, c="101.5", v=2000)])
    assert (r.inserted, r.updated) == (0, 1)
    c = load_candles(session, "AAPL", Timeframe.D1)[0]
    assert c.close == Decimal("101.5") and c.volume == 2000


def test_timeframes_y_tickers_separados(session):
    upsert_candles(session, "AAPL", Timeframe.D1, [bar(0)])
    upsert_candles(session, "AAPL", Timeframe.H1, [bar(0)])
    upsert_candles(session, "MSFT", Timeframe.D1, [bar(0)])
    assert _count(session) == 3


@pytest.mark.parametrize(
    "kwargs",
    [
        {"h": "98"},  # máximo por debajo del mínimo
        {"c": "150"},  # cierre por encima del máximo
        {"o": "90"},  # apertura por debajo del mínimo
        {"low": "0", "o": "0"},  # precio cero
        {"v": -1},
    ],
)
def test_descarta_velas_incoherentes(session, kwargs):
    r = upsert_candles(session, "AAPL", Timeframe.D1, [bar(0, **kwargs), bar(1)])
    assert (r.inserted, r.skipped_invalid) == (1, 1)


def test_ultima_fecha_y_carga_ordenada_con_rango(session):
    assert last_timestamp(session, "AAPL", Timeframe.D1) is None
    upsert_candles(session, "AAPL", Timeframe.D1, [bar(2), bar(0), bar(1)])
    assert last_timestamp(session, "AAPL", Timeframe.D1) == T0 + timedelta(days=2)
    todas = load_candles(session, "AAPL", Timeframe.D1)
    assert [c.timestamp.day for c in todas] == [5, 6, 7]
    parte = load_candles(session, "AAPL", Timeframe.D1, start=T0 + timedelta(days=1))
    assert len(parte) == 2


def test_la_base_rechaza_duplicados_directos(session):
    for _ in range(2):
        session.add(
            Candle(
                ticker="AAPL",
                timeframe=Timeframe.D1,
                timestamp=T0,
                open=1,
                high=2,
                low=1,
                close=2,
                volume=1,
            )
        )
    with pytest.raises(IntegrityError):
        session.flush()
