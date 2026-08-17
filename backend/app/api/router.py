"""
Main API router.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.payment import router as payment_router
from app.api.routes.subscription import (
    router as subscription_router,
)


api_router = APIRouter()

api_router.include_router(
    auth_router,
)

api_router.include_router(
    subscription_router,
)

api_router.include_router(
    payment_router,
)