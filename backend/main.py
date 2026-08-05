"""
Punto de entrada del Trading Bot.

Este archivo NO contiene lógica de negocio.

Su única responsabilidad es arrancar la aplicación
e informar al usuario si el sistema no puede iniciarse.
"""

from __future__ import annotations

import sys

from rich.console import Console

from app.core.startup import startup_manager

console = Console()


def main() -> None:
    """
    Punto de entrada principal.
    """

    console.print()

    console.rule("[bold cyan]Trading Bot[/bold cyan]")

    try:

        status = startup_manager.initialize()

        if not status.completed:
            raise RuntimeError("Startup incompleto.")

        console.print("[green]✓ Sistema iniciado correctamente[/green]")

    except Exception as exc:

        console.print()

        console.print(
            f"[bold red]Error durante el arranque:[/bold red] {exc}"
        )

        console.print()

        sys.exit(1)


if __name__ == "__main__":
    main()