"""
Subscription API schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatusResponse(BaseModel):
    """Current subscription state."""

    exists: bool

    status: str | None

    started_at: datetime | None

    current_period_start: datetime | None

    current_period_end: datetime | None

    cancel_at_period_end: bool

    access_allowed: bool

    access_reason: str


class SubscriptionCancelResponse(BaseModel):
    """Subscription cancellation response."""

    success: bool

    status: str

    message: str