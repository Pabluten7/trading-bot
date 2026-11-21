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
