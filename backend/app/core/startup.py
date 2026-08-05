"""
startup.py
==========

Inicialización del sistema.

Este módulo es responsable de arrancar todos los servicios necesarios
para que el bot pueda funcionar correctamente.

NO contiene lógica de trading.
NO ejecuta estrategias.
NO realiza cálculos.

Únicamente coordina el inicio de la aplicación.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import settings


@dataclass(slots=True)
class StartupStatus:
    """Estado del proceso de inicialización."""

    configuration_loaded: bool = False
    logging_ready: bool = False
    database_ready: bool = False
    license_ready: bool = False
    scheduler_ready: bool = False
    completed: bool = False


class StartupManager:
    """
    Responsable del arranque completo del sistema.
    """

    def __init__(self) -> None:

        self.status = StartupStatus()

    def initialize(self) -> StartupStatus:
        """
        Arranca todos los módulos necesarios.

        El orden de inicialización NO debe cambiar.
        """

        self._load_configuration()

        self._initialize_logging()

        self._initialize_database()

        self._initialize_license_system()

        self._initialize_scheduler()

        self.status.completed = True

        return self.status

    # ---------------------------------------------------------
    # Pasos de inicialización
    # ---------------------------------------------------------

    def _load_configuration(self) -> None:

        # Forzamos la carga de la configuración
        _ = settings.app.name

        self.status.configuration_loaded = True

    def _initialize_logging(self) -> None:

        # Se implementará en config/logging.py
        self.status.logging_ready = True

    def _initialize_database(self) -> None:

        # Se implementará en database/
        self.status.database_ready = True

    def _initialize_license_system(self) -> None:

        # Se implementará en licensing/
        self.status.license_ready = True

    def _initialize_scheduler(self) -> None:

        # Se implementará en core/scheduler.py
        self.status.scheduler_ready = True


startup_manager = StartupManager()