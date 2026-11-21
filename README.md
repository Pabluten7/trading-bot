# Trading Bot S&P500

Bot de swing trading automatizado (solo LONG) sobre el S&P500. Broker: Alpaca (paper trading primero).

## Estructura
- `backend/` – API y motor de trading (Python, FastAPI)
- `frontend/` – Dashboard (React + Vite + TypeScript)

## Desarrollo
```bash
cp .env.example .env

# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest && ruff check . && ruff format --check .

# Frontend
cd frontend && npm install
npm run dev
npm run lint && npm test
```
Con Docker: `docker compose up --build` (levanta Postgres, aplica migraciones y arranca la API). Define `POSTGRES_PASSWORD` en `.env`.

## Base de datos
Sin Docker se usa SQLite (`DATABASE_URL=sqlite:///./trading_bot.db`). Con Docker, Postgres.
```bash
cd backend
alembic upgrade head                              # aplicar migraciones
alembic revision --autogenerate -m "descripcion"  # tras cambiar models.py
```
Hay un test que falla si cambias un modelo sin crear su migración.

## Datos de mercado (Alpaca)
Necesitas `ALPACA_API_KEY` y `ALPACA_API_SECRET` en `.env` (cuenta paper gratuita).
```bash
cd backend
python -m app.market_data sync --tickers AAPL,MSFT      # unas pocas, para probar
python -m app.market_data sync --universe --limit 20    # 20 del S&P500
python -m app.market_data sync --universe               # todo el S&P500 (1D, 4H, 1H)
```
La sincronización es incremental: la segunda vez solo descarga lo que falta. El plan gratuito de Alpaca admite 200 peticiones/min y no permite pedir los últimos 15 min del feed `sip`; ambos casos están controlados.

## Indicadores
`app.indicators` calcula EMA 20/50/200, RSI 14, ATR 14, ADX 14 (con +DI/-DI) y volumen relativo. Son funciones puras, verificadas contra TA-Lib, y nunca miran al futuro (el valor de una vela solo depende de esa vela y las anteriores).

## Estrategia: scoring
`app.strategy` puntúa cada valor de 0 a 100 combinando 1D (50 %), 4H (30 %) y 1H (20 %): tendencia de EMAs (40), ADX (20), RSI (20), volumen (10) y, solo en el diario, ATR (10). Solo usa velas ya cerradas. Los parámetros viven en `app/strategy/params.py` (validados) y se guardan en la tabla `strategies`.
```bash
# desde Python: puntuar el universo y guardar las señales
from app.strategy.scanner import scan_universe
```

## Estrategia: filtros
`app.strategy.filters` descarta valores aunque tengan buen score: mercado (SPY > EMA200 diaria; sin datos no se opera), posición ya abierta, reentrada (espera de velas de 1H tras cerrar), ATR > 5 %, gap de apertura > 3 % y sector lleno. Cada descarte guarda su motivo en español.

## Estrategia: selección
`app.strategy.selection` ordena por score y elige hasta 8 valores con score >= 80, respetando el máximo de 3 por sector y los huecos libres (8 menos las posiciones ya abiertas). Es determinista: mismos datos, misma selección. Cada valor descartado guarda su motivo en `Signal.discard_reason`.

## Riesgo
`app.risk.plan_trade` calcula acciones, stop (entrada − 2×ATR) y objetivo (+2R) arriesgando el 1 % del capital, con dos topes: máximo 12,5 % del capital por posición y el efectivo disponible (sin el tope, 8 posiciones con stops de 2×ATR sumarían más del 100 % del capital). `app.risk.advance` gestiona la posición vela a vela: venta del 50 % en el objetivo, stop a break-even y trailing stop (máximo − 2×ATR) para el resto. Si en una vela se tocan stop y objetivo, se asume que saltó el stop.

## Backtest

Simula la estrategia completa sobre datos históricos ya sincronizados (sin mirar al futuro):

```powershell
cd backend
python -m app.backtest run --start 2025-01-01 --end 2025-12-31 --universe --limit 50 --daily-only --out reports/bt1
```

- Decide cada día a la apertura usando solo velas cerradas; entra a la apertura con slippage 0,05 %.
- Gestiona stop, parcial 50 %, break-even y trailing con la vela del día; liquida al final.
- Salida: `metrics.json`, `equity.csv`, `trades.csv` y un resumen (retorno, CAGR, max drawdown, Sharpe, win rate, profit factor, esperanza en R, exposición, comparación con SPY).
- `--daily-only` usa solo velas diarias (pesos renormalizados) para periodos largos, porque por defecto 4H/1H solo guardan 180/90 días.
- Limitaciones: sesgo de supervivencia (universo actual) y sin comisiones.

## Universo S&P500
```bash
cd backend
python -m app.universe sync          # carga la lista incluida en el repo (sin internet)
python -m app.universe sync --url    # actualiza desde la lista pública actual
```
Las empresas que salen del índice se marcan inactivas (no se borran) para conservar el histórico.

## Flujo de trabajo
Una rama por historia de usuario: `hu/HU-XX-nombre`, PR a `main`. Las tasks son commits dentro de la rama. Commits en formato Conventional Commits. El backlog vive en el Project de Claude (`backlog.md`).

La rama `old` es solo referencia del intento anterior.
