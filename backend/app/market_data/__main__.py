"""Línea de comandos: python -m app.market_data sync (--tickers AAPL,MSFT | --universe)"""

import argparse

from sqlalchemy.orm import Session

from app.db.models import Timeframe
from app.db.session import get_engine
from app.market_data.alpaca import AlpacaProvider
from app.market_data.service import sync_history
from app.universe.service import active_tickers


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.market_data")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync", help="Descarga/actualiza velas en la base de datos")
    group = sync.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", help="Lista separada por comas, p. ej. AAPL,MSFT")
    group.add_argument("--universe", action="store_true", help="Todo el universo S&P500 activo")
    sync.add_argument("--timeframes", default="1D,4H,1H", help="Por defecto: 1D,4H,1H")
    sync.add_argument("--limit", type=int, help="Solo las N primeras empresas (para pruebas)")
    args = parser.parse_args()

    timeframes = [Timeframe(t.strip().upper()) for t in args.timeframes.split(",")]
    provider = AlpacaProvider()
    with Session(get_engine()) as session:
        if args.universe:
            tickers = active_tickers(session)
            if not tickers:
                raise SystemExit(
                    "El universo está vacío: ejecuta antes `python -m app.universe sync`"
                )
        else:
            tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        if args.limit:
            tickers = tickers[: args.limit]

        print(f"Sincronizando {len(tickers)} empresas, timeframes: {[t.value for t in timeframes]}")
        for tf, st in sync_history(session, provider, tickers, timeframes).items():
            print(
                f"  {tf.value}: nuevas={st.inserted} actualizadas={st.updated} "
                f"descartadas={st.skipped_invalid} sin datos={len(st.no_data)}"
            )
            if st.no_data:
                print(f"    sin datos: {', '.join(st.no_data[:20])}")


if __name__ == "__main__":
    main()
