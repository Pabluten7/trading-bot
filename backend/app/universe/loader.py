"""Lectura y validación de la lista de componentes del S&P500 (CSV)."""

import csv
import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

BUNDLED_CSV = Path(__file__).parent / "data" / "sp500.csv"
REMOTE_CSV_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
)

# El S&P500 tiene ~503 valores (algunas empresas tienen dos clases de acciones).
MIN_EXPECTED = 450
MAX_EXPECTED = 550
REQUIRED_COLUMNS = {"Symbol", "Security", "GICS Sector", "GICS Sub-Industry"}


class UniverseError(ValueError):
    """La lista descargada o leída no es válida."""


@dataclass(frozen=True)
class Constituent:
    ticker: str
    name: str
    sector: str
    sub_industry: str | None = None
    added_to_index: date | None = None


def parse_constituents(text: str) -> list[Constituent]:
    """Convierte el CSV en una lista validada. Falla si algo es sospechoso:
    es mejor no actualizar que cargar un universo roto."""
    reader = csv.DictReader(io.StringIO(text))
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise UniverseError(f"Faltan columnas en el CSV: {sorted(missing)}")

    result: list[Constituent] = []
    seen: set[str] = set()
    for line, row in enumerate(reader, start=2):
        ticker = (row["Symbol"] or "").strip().upper()
        name = (row["Security"] or "").strip()
        sector = (row["GICS Sector"] or "").strip()
        if not ticker or not name or not sector:
            raise UniverseError(f"Línea {line}: ticker, nombre o sector vacío")
        if ticker in seen:
            raise UniverseError(f"Línea {line}: ticker duplicado {ticker}")
        seen.add(ticker)
        added = (row.get("Date added") or "").strip()
        try:
            added_date = date.fromisoformat(added) if added else None
        except ValueError:
            added_date = None  # fechas sueltas mal formadas no invalidan el universo
        result.append(
            Constituent(
                ticker=ticker,
                name=name,
                sector=sector,
                sub_industry=(row["GICS Sub-Industry"] or "").strip() or None,
                added_to_index=added_date,
            )
        )

    if not MIN_EXPECTED <= len(result) <= MAX_EXPECTED:
        raise UniverseError(
            f"Número de empresas inesperado: {len(result)} "
            f"(esperado entre {MIN_EXPECTED} y {MAX_EXPECTED})"
        )
    return result


def load_from_file(path: Path = BUNDLED_CSV) -> list[Constituent]:
    return parse_constituents(path.read_text(encoding="utf-8"))


def load_from_url(url: str = REMOTE_CSV_URL, timeout: float = 30.0) -> list[Constituent]:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return parse_constituents(response.text)
