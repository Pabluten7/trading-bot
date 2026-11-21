"""Salida de un backtest: resumen en texto y archivos (JSON y CSV)."""

import csv
import json
from pathlib import Path

from app.backtest.engine import BacktestResult

LIMITATIONS = (
    "Limitaciones: decisiones a la apertura con datos hasta el cierre anterior; "
    "sin comisiones (el deslizamiento sí cuenta); universo actual del S&P500 "
    "(sesgo de supervivencia); resultados pasados no garantizan resultados futuros."
)


def summary_text(r: BacktestResult) -> str:
    m = r.metrics
    lines = [
        f"Backtest {r.config.start} -> {r.config.end}  ({m['days']} días de mercado)",
        f"  Capital: {m['initial_capital']:,.0f} -> {m['final_equity']:,.2f}"
        f"   Retorno: {m['total_return_pct']}%   CAGR: {m['cagr_pct']}%",
        f"  Caída máxima: {m['max_drawdown_pct']}%   Sharpe: {m['sharpe']}",
        f"  Operaciones: {m['trades']}   Aciertos: {m['win_rate_pct']}%   "
        f"Factor de beneficio: {m['profit_factor']}",
        f"  Ganancia media: {m['avg_win']}   Pérdida media: {m['avg_loss']}   "
        f"Expectativa: {m['expectancy_r']} R",
        f"  Días medios en posición: {m['avg_holding_days']}   Exposición media: "
        f"{m['avg_exposure_pct']}%",
        f"  Salidas: {m['exit_reasons']}",
    ]
    if "benchmark_return_pct" in m:
        lines.append(
            f"  {r.params.benchmark_ticker} comprar y mantener: {m['benchmark_return_pct']}% "
            f"(caída máx. {m['benchmark_max_drawdown_pct']}%)"
        )
    lines.append("  " + LIMITATIONS)
    return "\n".join(lines)


def write_report(r: BacktestResult, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(
        json.dumps({"metrics": r.metrics, "params": r.params.model_dump()}, indent=2),
        encoding="utf-8",
    )
    with open(out_dir / "equity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "equity"])
        w.writerows(zip(r.dates, [round(e, 2) for e in r.equity], strict=True))
    with open(out_dir / "trades.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["ticker", "sector", "entry_date", "exit_date", "entry_price", "quantity", "stop",
             "take_profit", "score", "pnl", "r_multiple", "exit_reason"]
        )  # fmt: skip
        for t in r.trades:
            w.writerow(
                [t.ticker, t.sector, t.entry_date, t.exit_date, t.entry_price, t.quantity,
                 t.initial_stop, t.take_profit, t.score, round(t.pnl, 2),
                 round(t.r_multiple, 3), t.exit_reason]
            )  # fmt: skip
