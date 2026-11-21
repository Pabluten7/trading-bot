"""Modelos base: estrategias, señales, órdenes y operaciones.

Reglas:
- Dinero y precios: `Numeric` / `Decimal`, nunca float.
- Fechas siempre con zona horaria (UTC).
- Enums guardados como texto (portable entre SQLite y Postgres).
- Las velas (OHLCV) llegan en la HU-04; las posiciones se derivan de las operaciones abiertas.
"""

import enum
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

PRICE = Numeric(14, 4)
QTY = Numeric(18, 6)


def _now() -> datetime:
    return datetime.now(UTC)


def _enum(cls: type[enum.Enum]) -> Enum:
    return Enum(cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class OrderSide(enum.StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(enum.StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(enum.StrEnum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class TradeStatus(enum.StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class ExitReason(enum.StrEnum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    MANUAL = "manual"


class UniverseMember(TimestampMixin, Base):
    """Empresa del universo (componentes del S&P500). Si sale del índice se marca
    inactiva en vez de borrarse, para conservar el histórico."""

    __tablename__ = "universe_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(60), index=True)
    sub_industry: Mapped[str | None] = mapped_column(String(120))
    added_to_index: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Timeframe(enum.StrEnum):
    D1 = "1D"
    H4 = "4H"
    H1 = "1H"


class Candle(Base):
    """Vela OHLCV. `timestamp` es el inicio de la vela, en UTC."""

    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("ticker", "timeframe", "timestamp", name="uq_candle_ticker_tf_ts"),
        CheckConstraint("high >= low", name="ck_candle_high_ge_low"),
        CheckConstraint("volume >= 0", name="ck_candle_volume_nonneg"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10))
    timeframe: Mapped[Timeframe] = mapped_column(_enum(Timeframe))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[Decimal] = mapped_column(PRICE)
    high: Mapped[Decimal] = mapped_column(PRICE)
    low: Mapped[Decimal] = mapped_column(PRICE)
    close: Mapped[Decimal] = mapped_column(PRICE)
    volume: Mapped[int] = mapped_column(BigInteger)


class Strategy(TimestampMixin, Base):
    """Estrategia y sus parámetros. Los parámetros van en JSON para que cada
    estrategia (predeterminada o personalizada) defina los suyos."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Signal(TimestampMixin, Base):
    """Resultado del escaneo de un ticker en un día (score 0-100)."""

    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint(
            "strategy_id", "ticker", "scan_date", name="uq_signal_strategy_ticker_day"
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_signal_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    scan_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    # Valores de los indicadores y desglose del score en ese momento.
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    discard_reason: Mapped[str | None] = mapped_column(String(200))

    strategy: Mapped[Strategy] = relationship()


class Trade(TimestampMixin, Base):
    """Operación completa (LONG): de la entrada al cierre."""

    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_trade_quantity_positive"),
        CheckConstraint("stop_loss < entry_price", name="ck_trade_long_stop_below_entry"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"))
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[TradeStatus] = mapped_column(
        _enum(TradeStatus), default=TradeStatus.OPEN, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(QTY)
    entry_price: Mapped[Decimal] = mapped_column(PRICE)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stop_loss: Mapped[Decimal] = mapped_column(PRICE)
    take_profit: Mapped[Decimal] = mapped_column(PRICE)
    trailing_stop: Mapped[Decimal | None] = mapped_column(PRICE)
    partial_sold: Mapped[bool] = mapped_column(Boolean, default=False)

    exit_price: Mapped[Decimal | None] = mapped_column(PRICE)
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_reason: Mapped[ExitReason | None] = mapped_column(_enum(ExitReason))
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(16, 4))

    strategy: Mapped[Strategy] = relationship()
    signal: Mapped[Signal | None] = relationship()
    orders: Mapped[list["Order"]] = relationship(back_populates="trade")


class Order(TimestampMixin, Base):
    """Orden enviada al broker (entrada, SL, TP, venta parcial...)."""

    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), index=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    side: Mapped[OrderSide] = mapped_column(_enum(OrderSide))
    order_type: Mapped[OrderType] = mapped_column(_enum(OrderType))
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus), default=OrderStatus.NEW)

    quantity: Mapped[Decimal] = mapped_column(QTY)
    limit_price: Mapped[Decimal | None] = mapped_column(PRICE)
    stop_price: Mapped[Decimal | None] = mapped_column(PRICE)
    filled_quantity: Mapped[Decimal] = mapped_column(QTY, default=Decimal(0))
    filled_avg_price: Mapped[Decimal | None] = mapped_column(PRICE)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trade: Mapped[Trade | None] = relationship(back_populates="orders")


__all__ = [
    "Base",
    "Candle",
    "ExitReason",
    "Order",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Signal",
    "Strategy",
    "Timeframe",
    "Trade",
    "TradeStatus",
    "UniverseMember",
]
