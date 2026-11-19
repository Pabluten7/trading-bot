"""
Modelos SQLAlchemy 2.0 — Todas las tablas del Trading Bot.

Tablas:
  - candles           → datos OHLCV por ticker y timeframe
  - signals           → scores y señales calculadas por el motor
  - trades            → operaciones ejecutadas (abiertas y cerradas)
  - positions         → estado actual de posiciones abiertas
  - portfolio_snapshots → snapshot diario del portfolio
  - strategy_config   → parámetros de la estrategia (editables desde UI)
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base común con timestamps automáticos."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CANDLE — Datos OHLCV
# ─────────────────────────────────────────────────────────────────────────────
class Candle(Base):
    """
    Vela OHLCV para un ticker y timeframe dados.
    Timeframes soportados: 1D, 4H, 1H
    """

    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("ticker", "timeframe", "timestamp", name="uq_candle_ticker_tf_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)   # 1D | 4H | 1H
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    def __repr__(self) -> str:
        return f"<Candle {self.ticker} {self.timeframe} {self.timestamp} C={self.close}>"


# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL — Score y señal calculada por el motor
# ─────────────────────────────────────────────────────────────────────────────
class Signal(Base):
    """
    Resultado del motor de señales para un ticker en una fecha.
    score 0-100. selected=True si fue elegida para operar.
    """

    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("ticker", "signal_date", name="uq_signal_ticker_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    signal_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(String(100))

    # Score global y por timeframe
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_daily: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    score_4h: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    score_1h: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Indicadores calculados (snapshot en el momento del escaneo)
    ema20_daily: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    ema50_daily: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    ema200_daily: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    rsi14_daily: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    adx14_daily: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    atr14_daily: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    atr_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Resultado de los filtros
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discard_reason: Mapped[str | None] = mapped_column(String(200))

    def __repr__(self) -> str:
        return f"<Signal {self.ticker} {self.signal_date} score={self.score} selected={self.selected}>"


# ─────────────────────────────────────────────────────────────────────────────
# TRADE — Operación ejecutada
# ─────────────────────────────────────────────────────────────────────────────
class Trade(Base):
    """
    Operación completa: desde la entrada hasta el cierre.
    status: open | closed | cancelled
    """

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    alpaca_order_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"))

    # Entrada
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)

    # Gestión de riesgo
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    atr_at_entry: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    # Salida
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_reason: Mapped[str | None] = mapped_column(String(50))  # SL | TP | TRAILING | MANUAL

    # Venta parcial
    partial_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    partial_sold_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    partial_sold_shares: Mapped[int | None] = mapped_column(Integer)

    # Resultado
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))

    # Relaciones
    signal: Mapped["Signal | None"] = relationship("Signal", lazy="select")

    def __repr__(self) -> str:
        return f"<Trade {self.ticker} {self.status} entry={self.entry_price} pnl={self.pnl}>"


# ─────────────────────────────────────────────────────────────────────────────
# POSITION — Estado actual de posición abierta
# ─────────────────────────────────────────────────────────────────────────────
class Position(Base):
    """
    Vista en tiempo real de cada posición abierta.
    Sincronizado con Alpaca. Se actualiza tras cada ciclo de monitorización.
    """

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("ticker", name="uq_position_ticker"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"))

    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    unrealized_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))

    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    trailing_stop: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    partial_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trade: Mapped["Trade | None"] = relationship("Trade", lazy="select")

    def __repr__(self) -> str:
        return f"<Position {self.ticker} shares={self.shares} pnl={self.unrealized_pnl}>"


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO SNAPSHOT — Snapshot diario del portfolio
# ─────────────────────────────────────────────────────────────────────────────
class PortfolioSnapshot(Base):
    """
    Fotografía diaria del estado del portfolio al cierre del mercado.
    Sirve para construir la equity curve.
    """

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_date", name="uq_snapshot_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    total_equity: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    positions_value: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    open_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    daily_pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    daily_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    total_pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    def __repr__(self) -> str:
        return f"<PortfolioSnapshot {self.snapshot_date} equity={self.total_equity}>"


# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY CONFIG — Parámetros de la estrategia (editables desde UI)
# ─────────────────────────────────────────────────────────────────────────────
class StrategyConfig(Base):
    """
    Parámetros de la estrategia almacenados en DB.
    Permite ajustarlos desde la UI sin reiniciar el bot.
    Solo debe existir un registro activo (is_active=True).
    """

    __tablename__ = "strategy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    max_positions: Mapped[int] = mapped_column(Integer, default=8)
    max_per_sector: Mapped[int] = mapped_column(Integer, default=3)
    min_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("80.0"))
    risk_per_trade: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.01"))
    sl_atr_multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.0"))
    tp_risk_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.0"))
    partial_sell_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.50"))
    max_atr_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("5.0"))

    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<StrategyConfig '{self.name}' active={self.is_active}>"
