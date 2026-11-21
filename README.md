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

## Flujo de trabajo
Una rama por historia de usuario: `hu/HU-XX-nombre`, PR a `main`. Las tasks son commits dentro de la rama. Commits en formato Conventional Commits. El backlog vive en el Project de Claude (`backlog.md`).

La rama `old` es solo referencia del intento anterior.
