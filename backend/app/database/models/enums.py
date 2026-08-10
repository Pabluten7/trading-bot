"""
Database-related enumerations.

Centralizes persistent status values used across the application.
"""

from __future__ import annotations

from enum import StrEnum


class SubscriptionStatus(StrEnum):
    """Possible subscription states."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class LicenseStatus(StrEnum):
    """Possible software license states."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class DeviceStatus(StrEnum):
    """Possible device states."""

    ACTIVE = "active"
    REVOKED = "revoked"