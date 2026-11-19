.PHONY: help dev stop build test lint migrate seed logs clean

# ─── Variables ───────────────────────────────────────────────────────────────
DC       = docker compose
BACKEND  = $(DC) exec app
PYTHON   = $(BACKEND) python

# ─── Ayuda ───────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Trading Bot — Comandos disponibles"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  make dev        Levanta todos los servicios en modo desarrollo"
	@echo "  make stop       Para y elimina los contenedores"
	@echo "  make build      Reconstruye las imágenes Docker"
	@echo "  make test       Ejecuta la suite de tests"
	@echo "  make lint       Ejecuta ruff (linter + formatter)"
	@echo "  make migrate    Genera y aplica migraciones Alembic"
	@echo "  make seed       Inserta datos de prueba en la base de datos"
	@echo "  make logs       Muestra logs en tiempo real"
	@echo "  make shell      Abre una shell en el contenedor app"
	@echo "  make clean      Elimina volúmenes y contenedores"
	@echo ""

# ─── Desarrollo ──────────────────────────────────────────────────────────────
dev:
	@cp -n .env.example .env 2>/dev/null || true
	$(DC) up -d
	@echo "✅  Servicios levantados:"
	@echo "    API  → http://localhost:8000"
	@echo "    Docs → http://localhost:8000/docs"
	@echo "    UI   → http://localhost:5173"

stop:
	$(DC) down

build:
	$(DC) build --no-cache

logs:
	$(DC) logs -f app worker beat

shell:
	$(BACKEND) bash

# ─── Calidad de código ───────────────────────────────────────────────────────
lint:
	$(BACKEND) ruff check . --fix
	$(BACKEND) ruff format .

typecheck:
	$(BACKEND) mypy app/

# ─── Tests ───────────────────────────────────────────────────────────────────
test:
	$(BACKEND) pytest -v --cov=app --cov-report=term-missing

test-fast:
	$(BACKEND) pytest -v -x -q

# ─── Base de datos ───────────────────────────────────────────────────────────
migrate:
	$(BACKEND) alembic revision --autogenerate -m "$(msg)"
	$(BACKEND) alembic upgrade head
	@echo "✅  Migración aplicada"

migrate-up:
	$(BACKEND) alembic upgrade head

migrate-down:
	$(BACKEND) alembic downgrade -1

migrate-history:
	$(BACKEND) alembic history --verbose

seed:
	$(PYTHON) -m app.db.seed
	@echo "✅  Datos de prueba insertados"

# ─── Limpieza ────────────────────────────────────────────────────────────────
clean:
	$(DC) down -v --remove-orphans
	@echo "✅  Contenedores y volúmenes eliminados"
