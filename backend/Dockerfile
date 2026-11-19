FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (gestor de paquetes rápido)
RUN pip install uv

# Copiar e instalar dependencias Python
COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"

COPY . .

EXPOSE 8000
