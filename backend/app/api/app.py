"""
FastAPI application factory.

Creates and configures the HTTP API independently from the
application lifecycle managed by the core package.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import settings


def create_api() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    application = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        debug=settings.app.debug,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(
        api_router,
        prefix="/api",
    )

    return application


api = create_api()