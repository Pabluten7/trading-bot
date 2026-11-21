"""Línea de comandos:

python -m app.backtest run --start 2024-01-01 --end 2026-10-31 --universe --limit 50
python -m app.backtest run --start 2025-01-01 --end 2026-10-31 --tickers AAPL,MSFT --daily-only
"""

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.backtest.data import load_backtest_data
from app.backtest.engine import BacktestConfig, run_backtest
from app.backtest.report import summary_text, write_report
from app.db.models import Timeframe
from app.db.session import get_engine
from app.strategy.registry import get_or_create_default_strategy, params_of
from app.universe.service import active_tickers


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.backtest")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="Ejecuta un backtest con los datos guardados")
    run.add_argument("--start", type=date.fromisoformat, required=True)
    run.add_argument("--end", type=date.fromisoformat, required=True)
    group = run.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", help="Lista separada por comas")
    group.add_argument("--universe", action="store_true", help="Todo el universo S&P500 activo")
    run.add_argument("--limit", type=int, help="Solo las N primeras empresas")
    run.add_argument("--capital", type=Decimal, default=Decimal(100_000))
    run.add_argument("--slippage", type=float, default=0.0005, help="Fracción por operación")
    run.add_argument(
        "--daily-only",
        action="store_true",
        help="Puntuar solo con velas diarias (si no hay histórico 4H/1H suficiente)",
    )
    run.add_argument("--out", type=Path, help="Carpeta donde guardar metrics.json, trades.csv...")
    args = parser.parse_args()

    with Session(get_engine()) as session:
        strategy = get_or_create_default_strategy(session)
        params = params_of(strategy)
        tickers = (
            active_tickers(session)
            if args.universe
            else [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        )
        if args.limit:
            tickers = tickers[: args.limit]
        if not tickers:
            raise SystemExit("No hay valores: sincroniza antes el universo y los datos")
        print(f"Cargando datos de {len(tickers)} valores...")
        data, benchmark = load_backtest_data(
            session, tickers, params.benchmark_ticker, args.start, args.end, not args.daily_only
        )
    if not data:
        raise SystemExit("Ninguno de los valores tiene velas diarias guardadas")
    if Timeframe.D1 not in benchmark.series:
        raise SystemExit(
            f"Faltan velas diarias de {params.benchmark_ticker}: "
            f"python -m app.market_data sync --tickers {params.benchmark_ticker}"
        )
    config = BacktestConfig(
        args.start, args.end, args.capital, args.slippage, use_intraday=not args.daily_only
    )
    result = run_backtest(data, benchmark, params, config)
    print(summary_text(result))
    if args.out:
        write_report(result, args.out)
        print(f"Informe guardado en {args.out}")


if __name__ == "__main__":
    main()
