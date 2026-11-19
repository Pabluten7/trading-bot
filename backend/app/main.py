"""
Trading Bot — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Acciones al iniciar y detener la aplicación."""
    setup_logging()
    await init_db()
    yield
    # Cleanup al apagar (cerrar conexiones, etc.)


app = FastAPI(
    title="Trading Bot API",
    description="S&P500 Swing Trading Bot — REST API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# Se irán añadiendo por sprint
# from app.api import portfolio, signals, trades, bot_control
# app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
# app.include_router(signals.router,   prefix="/api/v1/signals",   tags=["Signals"])
# app.include_router(trades.router,    prefix="/api/v1/trades",    tags=["Trades"])
# app.include_router(bot_control.router, prefix="/api/v1/bot",     tags=["Bot Control"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0", "mode": settings.TRADING_MODE}
