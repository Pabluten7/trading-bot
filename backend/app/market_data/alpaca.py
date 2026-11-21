"""Proveedor de velas históricas de Alpaca (API de datos v2).

Solo lectura de datos: este módulo no opera ni usa la API de trading.
"""

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from app.core.config import Settings, get_settings
from app.db.models import Timeframe
from app.market_data.provider import Bar, MarketDataError

ALPACA_TIMEFRAME = {Timeframe.D1: "1Day", Timeframe.H4: "4Hour", Timeframe.H1: "1Hour"}
# El plan gratuito no permite consultar los últimos 15 minutos del feed SIP.
SIP_DELAY = timedelta(minutes=16)
MAX_SYMBOLS_PER_REQUEST = 50
PAGE_LIMIT = 10_000  # máximo de la API (puntos totales, no por símbolo)
MAX_RETRIES = 5


class AlpacaProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        sleep=time.sleep,
    ) -> None:
        self._settings = settings or get_settings()
        key = self._settings.alpaca_api_key.get_secret_value()
        secret = self._settings.alpaca_api_secret.get_secret_value()
        if not key or not secret:
            raise MarketDataError(
                "Faltan ALPACA_API_KEY y ALPACA_API_SECRET en el .env (claves de tu cuenta Alpaca)"
            )
        self._client = client or httpx.Client(timeout=30.0)
        self._headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self._sleep = sleep

    def get_bars(
        self, tickers: list[str], timeframe: Timeframe, start: datetime, end: datetime
    ) -> dict[str, list[Bar]]:
        end = self._clamp_end(end)
        result: dict[str, list[Bar]] = {t: [] for t in tickers}
        if start >= end:
            return result
        for i in range(0, len(tickers), MAX_SYMBOLS_PER_REQUEST):
            chunk = tickers[i : i + MAX_SYMBOLS_PER_REQUEST]
            for symbol, bars in self._fetch_chunk(chunk, timeframe, start, end).items():
                result[symbol].extend(bars)
        for bars in result.values():
            bars.sort(key=lambda b: b.timestamp)
        return result

    def _clamp_end(self, end: datetime) -> datetime:
        if self._settings.alpaca_feed == "sip":
            return min(end, datetime.now(UTC) - SIP_DELAY)
        return end

    def _fetch_chunk(
        self, tickers: list[str], timeframe: Timeframe, start: datetime, end: datetime
    ) -> dict[str, list[Bar]]:
        out: dict[str, list[Bar]] = {t: [] for t in tickers}
        params: dict[str, str | int] = {
            "symbols": ",".join(tickers),
            "timeframe": ALPACA_TIMEFRAME[timeframe],
            "start": start.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": PAGE_LIMIT,
            # Precios ajustados por splits: los indicadores no ven saltos falsos.
            "adjustment": "split",
            "feed": self._settings.alpaca_feed,
            "sort": "asc",
        }
        while True:
            payload = self._get("/v2/stocks/bars", params)
            for symbol, raw_bars in (payload.get("bars") or {}).items():
                if symbol in out:
                    out[symbol].extend(_to_bar(b) for b in raw_bars)
            token = payload.get("next_page_token")
            if not token:
                return out
            params["page_token"] = token

    def _get(self, path: str, params: dict) -> dict:
        url = self._settings.alpaca_data_url.rstrip("/") + path
        for attempt in range(1, MAX_RETRIES + 1):
            response = self._client.get(url, params=params, headers=self._headers)
            if response.status_code == 429 and attempt < MAX_RETRIES:
                self._sleep(_retry_delay(response, attempt))
                continue
            if response.status_code >= 500 and attempt < MAX_RETRIES:
                self._sleep(attempt)
                continue
            break
        if response.status_code in (401, 403):
            raise MarketDataError(
                f"Alpaca rechazó la petición ({response.status_code}): revisa las claves "
                f"o el plan de datos. Respuesta: {response.text[:200]}"
            )
        if response.status_code != 200:
            raise MarketDataError(f"Alpaca devolvió {response.status_code}: {response.text[:200]}")
        return response.json()


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return float(retry_after)
    return float(min(2**attempt, 30))


def _to_bar(raw: dict) -> Bar:
    return Bar(
        timestamp=datetime.fromisoformat(raw["t"]).astimezone(UTC),
        open=Decimal(str(raw["o"])),
        high=Decimal(str(raw["h"])),
        low=Decimal(str(raw["l"])),
        close=Decimal(str(raw["c"])),
        volume=int(raw["v"]),
    )
