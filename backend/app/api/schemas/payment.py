"""
Payment API schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


class CheckoutResponse(BaseModel):
    """Payment checkout response."""

    checkout_id: str

    checkout_url: str

    status: str