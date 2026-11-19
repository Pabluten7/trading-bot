# 🤖 Trading Bot — S&P500 Swing Trading

Bot de trading automatizado para el S&P500. Estrategia swing trading conservadora multi-timeframe (Diario / 4H / 1H), solo posiciones LONG, gestión de riesgo del 1% por operación.

## Requisitos previos

| Herramienta | Versión mínima | Instalación |
|---|---|---|
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | 2.20+ | incluido con Docker Desktop |
| Git | 2.40+ | https://git-scm.com |
| Cuenta Alpaca Paper | — | https://alpaca.markets |

> Python y Node.js **no son necesarios** en tu máquina local; todo corre dentro de Docker.

---

## Setup en 4 pasos

### 1 — Clonar el repositorio

```bash
git clone https://github.com/Pabluten7/trading-bot.git
cd trading-bot
git checkout main
```

### 2 — Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y rellena al menos:

```env
ALPACA_API_KEY=tu_api_key
ALPACA_API_SECRET=tu_api_secret
TRADING_MODE=paper          # paper siempre para empezar
```

> Las claves de Alpaca Paper las encuentras en https://app.alpaca.markets → Paper Trading → API Keys

### 3 — Levantar los servicios

```bash
make dev
```

Esto arranca automáticamente:

| Servicio | URL |
|---|---|
| API FastAPI | http://localhost:8000 |
| Docs interactivos (Swagger) | http://localhost:8000/docs |
| Frontend React | http://localhost:5173 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 4 — Aplicar migraciones y datos de prueba

```bash
make migrate-up
make seed
```

---

## Comandos útiles

```bash
make dev          # levantar todo
make stop         # parar todo
make test         # ejecutar tests
make lint         # linter + formatter
make logs         # ver logs en tiempo real
make shell        # entrar al contenedor app
make clean        # borrar contenedores y volúmenes
```

---

## Arquitectura

```
trading-bot/
├── backend/
│   ├── app/
│   │   ├── api/           # Endpoints FastAPI (routers)
│   │   ├── core/          # Config, Celery, scheduler
│   │   ├── db/            # Modelos SQLAlchemy, Alembic
│   │   ├── services/
│   │   │   ├── market_data.py    # Alpaca Market Data API
│   │   │   ├── signals.py        # Indicadores + scoring
│   │   │   ├── risk.py           # Sizing, SL/TP
│   │   │   ├── order_manager.py  # Ejecución órdenes
│   │   │   └── portfolio.py      # Estado cartera
│   │   ├── tasks/         # Jobs Celery
│   │   └── schemas/       # Schemas Pydantic
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/         # Dashboard, Trades, Signals
│       ├── components/
│       ├── hooks/
│       └── api/           # Axios client
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 + Alembic |
| Base de datos | PostgreSQL 16 |
| Cache / Cola | Redis 7 + Celery |
| Scheduler | APScheduler |
| Broker | Alpaca (paper primero) |
| Indicadores | pandas-ta |
| Frontend | React 18 + TypeScript + Vite |
| UI | shadcn/ui + Tailwind CSS |

## Estrategia de trading

- **Mercado**: S&P500 (500 empresas), solo LONG
- **Timeframes**: Diario / 4H / 1H (multi-timeframe)
- **Escaneo**: diario al abrir mercado (09:30 ET)
- **Scoring**: 0–100, operar solo con score ≥ 80
- **Posiciones**: máx 8 simultáneas, máx 3 por sector
- **Riesgo**: 1% capital por operación
- **Stop Loss**: 2 × ATR
- **Take Profit**: 2R (ratio riesgo/beneficio 1:2)
- **Venta parcial**: 50% al alcanzar TP, trailing stop en el resto

## Fases del proyecto

| Fase | Descripción | Estado |
|---|---|---|
| Sprint 0 | Infraestructura & Setup | ✅ En curso |
| Sprint 1 | Pipeline de datos S&P500 | ⏳ Pendiente |
| Sprint 2 | Motor de señales | ⏳ Pendiente |
| Sprint 3 | Órdenes + riesgo | ⏳ Pendiente |
| Sprint 4 | Automatización + paper trading | ⏳ Pendiente |
| Sprint 5 | Dashboard | ⏳ Pendiente |
| Sprint 6 | Reporting + alertas | ⏳ Pendiente |

---

## Licencia

Uso personal. No distribuir sin permiso del autor.
