"""
Application-wide constants.

Only stable system-level constants belong here.

Strategy parameters, risk parameters and trading thresholds must NOT be
stored in this module. Those values belong to their respective configuration
or strategy definitions.
"""

from __future__ import annotations

from typing import Final


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

APPLICATION_NAME: Final[str] = "Trading Bot"

DEFAULT_TIMEZONE: Final[str] = "America/New_York"


# ---------------------------------------------------------------------------
# Market
# ---------------------------------------------------------------------------

DEFAULT_MARKET: Final[str] = "US"

DEFAULT_EXCHANGE: Final[str] = "NYSE"


# ---------------------------------------------------------------------------
# Supported providers
# ---------------------------------------------------------------------------

ALPACA_PROVIDER: Final[str] = "alpaca"


# ---------------------------------------------------------------------------
# Authentication / licensing
# ---------------------------------------------------------------------------

LICENSE_TOKEN_TYPE: Final[str] = "Bearer"

LICENSE_STATUS_ACTIVE: Final[str] = "active"

LICENSE_STATUS_EXPIRED: Final[str] = "expired"

LICENSE_STATUS_SUSPENDED: Final[str] = "suspended"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

API_PREFIX: Final[str] = "/api"

API_V1_PREFIX: Final[str] = f"{API_PREFIX}/v1"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

HTTP_REQUEST_TIMEOUT_SECONDS: Final[float] = 10.0

HTTP_CONNECTION_TIMEOUT_SECONDS: Final[float] = 5.0


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

HEALTH_STATUS_OK: Final[str] = "ok"

HEALTH_STATUS_DEGRADED: Final[str] = "degraded"

HEALTH_STATUS_UNAVAILABLE: Final[str] = "unavailable"


# ---------------------------------------------------------------------------
# Trading system states
# ---------------------------------------------------------------------------

SYSTEM_STATE_STARTING: Final[str] = "starting"

SYSTEM_STATE_RUNNING: Final[str] = "running"

SYSTEM_STATE_STOPPING: Final[str] = "stopping"

SYSTEM_STATE_STOPPED: Final[str] = "stopped"

SYSTEM_STATE_ERROR: Final[str] = "error"