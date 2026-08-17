"""
Payment event database model.

Stores normalized payment-provider events so that webhook deliveries
can be processed idempotently.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PaymentEvent(Base):
    """Persisted payment-provider event."""

    __tablename__ = "payment_events"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "event_id",
            name="uq_payment_event_provider_event",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    raw_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )