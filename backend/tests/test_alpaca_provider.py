from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from app.core.config import Settings
from app.db.models import Timeframe
from app.market_data.alpaca import AlpacaProvider
from app.market_data.provider import MarketDataError

START = datetime(2026, 1, 5, tzinfo=UTC)
END = datetime(2026, 1, 9, tzinfo=UTC)


def _bar(day: int, close="101.5"):
    return {
        "t": f"2026-01-{day:02d}T05:00:00Z",
        "o": 100,
        "h": 102.25,
        "l": 99.1234,
        "c": float(close),
        "v": 1_234_567,
        "n": 10,
        "vw": 100.5,
    }


def _provider(handler, feed="iex", key="k", secret="s", sleeps=None):
    settings = Settings(
        _env_file=None, alpaca_api_key=key, alpaca_api_secret=secret, alpaca_feed=feed
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AlpacaProvider(
        settings, client, sleep=(sleeps.append if sleeps is not None else lambda s: None)
    )


def test_exige_claves():
    with pytest.raises(MarketDataError, match="ALPACA_API_KEY"):
        AlpacaProvider(Settings(_env_file=None, alpaca_api_key="", alpaca_api_secret=""))


def test_envia_cabeceras_y_parametros_correctos():
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        return httpx.Response(200, json={"bars": {"AAPL": [_bar(5)]}})

    result = _provider(handler).get_bars(["AAPL"], Timeframe.H4, START, END)
    req = seen[0]
    assert req.headers["APCA-API-KEY-ID"] == "k" and req.headers["APCA-API-SECRET-KEY"] == "s"
    q = dict(req.url.params)
    assert q["timeframe"] == "4Hour" and q["adjustment"] == "split" and q["feed"] == "iex"
    assert q["symbols"] == "AAPL" and q["start"] == "2026-01-05T00:00:00Z"
    bar = result["AAPL"][0]
    assert bar.close == Decimal("101.5") and bar.low == Decimal("99.1234")
    assert bar.volume == 1_234_567 and bar.timestamp.tzinfo is not None


@pytest.mark.parametrize(
    ("tf", "expected"),
    [(Timeframe.D1, "1Day"), (Timeframe.H4, "4Hour"), (Timeframe.H1, "1Hour")],
)
def test_traduce_timeframes(tf, expected):
    seen = []

    def handler(req):
        seen.append(req.url.params["timeframe"])
        return httpx.Response(200, json={"bars": {}})

    _provider(handler).get_bars(["AAPL"], tf, START, END)
    assert seen == [expected]


def test_sigue_la_paginacion_y_une_resultados():
    pages = iter(
        [
            {"bars": {"AAPL": [_bar(5), _bar(6)]}, "next_page_token": "abc"},
            {"bars": {"AAPL": [_bar(7)], "MSFT": [_bar(5)]}, "next_page_token": None},
        ]
    )
    tokens = []

    def handler(req):
        tokens.append(req.url.params.get("page_token"))
        return httpx.Response(200, json=next(pages))

    result = _provider(handler).get_bars(["AAPL", "MSFT"], Timeframe.D1, START, END)
    assert tokens == [None, "abc"]
    assert len(result["AAPL"]) == 3 and len(result["MSFT"]) == 1


def test_ticker_sin_datos_devuelve_lista_vacia():
    result = _provider(lambda r: httpx.Response(200, json={"bars": {}})).get_bars(
        ["ZZZZ"], Timeframe.D1, START, END
    )
    assert result == {"ZZZZ": []}


def test_divide_en_lotes_de_50_simbolos():
    calls = []

    def handler(req):
        calls.append(req.url.params["symbols"].split(","))
        return httpx.Response(200, json={"bars": {}})

    tickers = [f"T{i}" for i in range(120)]
    result = _provider(handler).get_bars(tickers, Timeframe.D1, START, END)
    assert [len(c) for c in calls] == [50, 50, 20]
    assert set(result) == set(tickers)


def test_feed_sip_recorta_el_final_para_respetar_el_plan_gratis():
    seen = []

    def handler(req):
        seen.append(req.url.params["end"])
        return httpx.Response(200, json={"bars": {}})

    now = datetime.now(UTC)
    _provider(handler, feed="sip").get_bars(["AAPL"], Timeframe.H1, now - timedelta(days=2), now)
    end = datetime.fromisoformat(seen[0])
    assert timedelta(minutes=15) < now - end < timedelta(minutes=18)


def test_feed_iex_no_recorta():
    seen = []

    def handler(req):
        seen.append(req.url.params["end"])
        return httpx.Response(200, json={"bars": {}})

    _provider(handler, feed="iex").get_bars(["AAPL"], Timeframe.D1, START, END)
    assert seen == ["2026-01-09T00:00:00Z"]


def test_si_todo_el_rango_es_reciente_no_llama_a_la_api():
    def handler(req):
        raise AssertionError("no debería llamar")

    now = datetime.now(UTC)
    result = _provider(handler, feed="sip").get_bars(
        ["AAPL"], Timeframe.H1, now - timedelta(minutes=5), now
    )
    assert result == {"AAPL": []}


def test_reintenta_ante_429_respetando_retry_after():
    answers = iter(
        [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"bars": {}})]
    )
    sleeps: list[float] = []
    _provider(lambda r: next(answers), sleeps=sleeps).get_bars(["AAPL"], Timeframe.D1, START, END)
    assert sleeps == [7.0]


def test_429_persistente_termina_con_error():
    sleeps: list[float] = []
    p = _provider(lambda r: httpx.Response(429), sleeps=sleeps)
    with pytest.raises(MarketDataError, match="429"):
        p.get_bars(["AAPL"], Timeframe.D1, START, END)
    assert len(sleeps) == 4


def test_error_de_servidor_se_reintenta():
    answers = iter([httpx.Response(503), httpx.Response(200, json={"bars": {"AAPL": [_bar(5)]}})])
    result = _provider(lambda r: next(answers)).get_bars(["AAPL"], Timeframe.D1, START, END)
    assert len(result["AAPL"]) == 1


@pytest.mark.parametrize("status", [401, 403])
def test_claves_o_plan_invalidos_dan_mensaje_claro(status):
    p = _provider(lambda r: httpx.Response(status, json={"message": "forbidden"}))
    with pytest.raises(MarketDataError, match="claves"):
        p.get_bars(["AAPL"], Timeframe.D1, START, END)


def test_los_secretos_no_aparecen_en_los_errores():
    p = _provider(
        lambda r: httpx.Response(401, text="nope"), key="clave-visible", secret="muy-secreto"
    )
    with pytest.raises(MarketDataError) as exc:
        p.get_bars(["AAPL"], Timeframe.D1, START, END)
    assert "muy-secreto" not in str(exc.value) and "clave-visible" not in str(exc.value)
