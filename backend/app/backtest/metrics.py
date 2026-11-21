"""Métricas de rendimiento de un backtest."""

import math
from datetime import date

TRADING_DAYS = 252


def max_drawdown(equity: list[float]) -> float:
    """Mayor caída desde un máximo, como número negativo (p. ej. -0.12 = -12 %)."""
    peak, worst = float("-inf"), 0.0
    for e in equity:
        peak = max(peak, e)
        if peak > 0:
            worst = min(worst, e / peak - 1.0)
    return worst


def sharpe(equity: list[float]) -> float | None:
    """Sharpe anualizado con rentabilidad libre de riesgo 0 y retornos diarios."""
    rets = [b / a - 1.0 for a, b in zip(equity, equity[1:], strict=False) if a > 0]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    if var <= 0:
        return None
    return mean / math.sqrt(var) * math.sqrt(TRADING_DAYS)


def compute_metrics(
    initial: float,
    dates: list[date],
    equity: list[float],
    trades: list,
    exposure: list[float],
    benchmark_close: list[float] | None = None,
) -> dict:
    """`trades`: objetos con `pnl`, `r_multiple`, `holding_days`, `exit_reason`."""
    final = equity[-1] if equity else initial
    total_return = final / initial - 1.0
    days = (dates[-1] - dates[0]).days if len(dates) > 1 else 0
    cagr = (final / initial) ** (365.25 / days) - 1.0 if days >= 30 and final > 0 else None

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_win = float(sum(t.pnl for t in wins))
    gross_loss = -float(sum(t.pnl for t in losses))
    reasons: dict[str, int] = {}
    for t in trades:
        reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1

    m = {
        "initial_capital": initial,
        "final_equity": round(final, 2),
        "total_return_pct": round(100 * total_return, 2),
        "cagr_pct": None if cagr is None else round(100 * cagr, 2),
        "max_drawdown_pct": round(100 * max_drawdown(equity), 2),
        "sharpe": None if (s := sharpe(equity)) is None else round(s, 2),
        "trades": len(trades),
        "win_rate_pct": round(100 * len(wins) / len(trades), 1) if trades else None,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "avg_win": round(gross_win / len(wins), 2) if wins else None,
        "avg_loss": round(-gross_loss / len(losses), 2) if losses else None,
        "expectancy_r": round(sum(t.r_multiple for t in trades) / len(trades), 3)
        if trades
        else None,
        "avg_holding_days": round(sum(t.holding_days for t in trades) / len(trades), 1)
        if trades
        else None,
        "avg_exposure_pct": round(100 * sum(exposure) / len(exposure), 1) if exposure else None,
        "exit_reasons": reasons,
        "days": len(equity),
    }
    if benchmark_close and len(benchmark_close) > 1 and benchmark_close[0] > 0:
        bench = benchmark_close[-1] / benchmark_close[0] - 1.0
        m["benchmark_return_pct"] = round(100 * bench, 2)
        m["benchmark_max_drawdown_pct"] = round(100 * max_drawdown(benchmark_close), 2)
    return m
