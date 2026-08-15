"""
API server launcher.
"""

from __future__ import annotations

import uvicorn

from app.api.server import api
from app.config.settings import settings


def run_api() -> None:
    """Start the FastAPI HTTP server."""

    uvicorn.run(
        api,
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
    )


if __name__ == "__main__":
    run_api()