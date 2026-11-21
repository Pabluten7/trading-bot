from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db.models import Timeframe
from app.market_data.provider import Bar
from app.market_data.service import DEFAULT_LOOKBACK_DAYS, sync_history
from app.market_data.store import last_timestamp, load_candles

NOW = datetime(2026, 11, 20, 21, 0, tzinfo=UTC)


class FakeProvider:
    """Genera una vela diaria por día natural entre start y end."""

    def __init__(self, missing: set[str] | None = None):
        self.calls: list[tuple[list[str], Timeframe, datetime, datetime]] = []
        self.missing = missing or set()

    def get_bars(self, tickers, timeframe, start, end):
        self.calls.append((list(tickers), timeframe, start, end))
        out = {}
        for t in tickers:
            bars, d = [], start.replace(hour=5, minute=0, second=0, microsecond=0)
            while d <= end and t not in self.missing:
                bars.append(Bar(d, Decimal(10), Decimal(12), Decimal(9), Decimal(11), 100))
                d += timedelta(days=1)
            out[t] = bars
        return out


def test_primera_sincronizacion_pide_el_historico_por_defecto(session):
    p = FakeProvider()
    sync_history(session, p, ["AAPL"], [Timeframe.D1], now=NOW)
    _, _, start, end = p.calls[0]
    assert start == NOW - timedelta(days=DEFAULT_LOOKBACK_DAYS[Timeframe.D1]) and end == NOW
    assert load_candles(session, "AAPL", Timeframe.D1)


def test_segunda_sincronizacion_pide_solo_lo_que_falta(session):
    p = FakeProvider()
    sync_history(session, p, ["AAPL"], [Timeframe.D1], now=NOW)
    ultima = last_timestamp(session, "AAPL", Timeframe.D1)
    stats = sync_history(session, p, ["AAPL"], [Timeframe.D1], now=NOW + timedelta(days=3))
    _, _, start, _ = p.calls[1]
    assert start == ultima
    # la vela de `ultima` se refresca (sin cambios) y se añaden 3 nuevas
    assert stats[Timeframe.D1].inserted == 3 and stats[Timeframe.D1].updated == 0


def test_agrupa_tickers_con_el_mismo_inicio_en_una_peticion(session):
    p = FakeProvider()
    sync_history(session, p, ["AAPL", "MSFT", "JPM"], [Timeframe.D1], now=NOW)
    assert len(p.calls) == 1 and p.calls[0][0] == ["AAPL", "MSFT", "JPM"]


def test_tickers_con_distinto_historial_se_piden_por_separado(session):
    p = FakeProvider()
    sync_history(session, p, ["AAPL"], [Timeframe.D1], now=NOW)
    p.calls.clear()
    sync_history(session, p, ["AAPL", "NUEVA"], [Timeframe.D1], now=NOW + timedelta(days=1))
    assert len(p.calls) == 2


def test_registra_tickers_sin_datos(session):
    stats = sync_history(
        session, FakeProvider(missing={"ZZZ"}), ["AAPL", "ZZZ"], [Timeframe.D1], now=NOW
    )
    assert stats[Timeframe.D1].no_data == ["ZZZ"]


def test_sincroniza_los_tres_timeframes_por_defecto(session):
    p = FakeProvider()
    stats = sync_history(session, p, ["AAPL"], now=NOW, lookback_days={t: 3 for t in Timeframe})
    assert set(stats) == set(Timeframe) and [c[1] for c in p.calls] == list(Timeframe)
