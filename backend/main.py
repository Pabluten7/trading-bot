"""
Application entry point.

This module is intentionally kept minimal.
Application lifecycle management belongs to the core package.
"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger
from rich.console import Console

from app.core.startup import startup_manager


console = Console()


async def run() -> None:
    """Run the Trading Bot application."""

    try:
        status = await startup_manager.initialize()

        if not status.completed:
            raise RuntimeError(
                f"Application startup failed. State: {status.state}"
            )

        console.print("[green]✓ Trading Bot started successfully.[/green]")

        # Keep the application process alive while background services
        # such as the scheduler are running.
        await asyncio.Event().wait()

    except asyncio.CancelledError:
        logger.info("Application task cancelled.")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")

    except Exception:
        logger.exception("Fatal application error.")
        raise

    finally:
        await startup_manager.shutdown()


def main() -> None:
    """Synchronous process entry point."""

    try:
        asyncio.run(run())

    except KeyboardInterrupt:
        console.print("\n[yellow]Trading Bot stopped.[/yellow]")

    except Exception as exc:
        console.print(
            f"\n[bold red]Fatal error:[/bold red] {exc}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()