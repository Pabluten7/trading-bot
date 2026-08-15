"""
HTTP server entry point.

This module exposes the FastAPI application to ASGI servers such as
Uvicorn.
"""

from __future__ import annotations

from app.api.app import api


__all__ = ["api"]