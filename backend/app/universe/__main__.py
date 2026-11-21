"""Línea de comandos: python -m app.universe sync [--url | --file RUTA]"""

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.universe.loader import BUNDLED_CSV, load_from_file, load_from_url
from app.universe.service import count_by_sector, sync_universe


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.universe")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync", help="Carga/actualiza el universo en la base de datos")
    src = sync.add_mutually_exclusive_group()
    src.add_argument("--url", action="store_true", help="Descargar la lista actual de internet")
    src.add_argument(
        "--file", type=Path, default=BUNDLED_CSV, help="CSV local (por defecto el incluido)"
    )
    args = parser.parse_args()

    constituents = load_from_url() if args.url else load_from_file(args.file)
    with Session(get_engine()) as session:
        result = sync_universe(session, constituents)
        print(f"Universo sincronizado: {result.summary()}")
        for ticker in result.removed:
            print(f"  salida del índice: {ticker}")
        for ticker in result.added:
            print(f"  nueva en el índice: {ticker}")
        print("Empresas activas por sector:")
        for sector, n in count_by_sector(session).items():
            print(f"  {sector}: {n}")


if __name__ == "__main__":
    main()
