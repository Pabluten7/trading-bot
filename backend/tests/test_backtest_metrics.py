from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.backtest.metrics import compute_metrics, max_drawdown, sharpe


def t(pnl, r, days=5, reason="stop_loss"):
    return SimpleNamespace(pnl=pnl, r_multiple=r, holding_days=days, exit_reason=reason)


def test_caida_maxima():
    assert max_drawdown([100, 120, 90, 110]) == pytest.approx(-0.25)
    assert max_drawdown([100, 110, 121]) == 0.0
    assert max_drawdown([]) == 0.0


def test_sharpe():
    assert sharpe([100.0] * 10) is None  # sin variación
    assert sharpe([100.0]) is None
    subiendo = [100 * (1.001 + (0.002 if i % 2 else 0)) ** i for i in range(100)]
    assert sharpe(subiendo) > 0
    assert sharpe([100 * 0.999**i * (1 + 0.003 * (i % 2)) for i in range(100)]) < 0


def test_metricas_de_operaciones():
    trades = [t(300, 2.0, 10, "trailing_stop"), t(100, 1.0, 4), t(-100, -1.0, 2), t(-50, -0.5, 6)]
    dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(100)]
    equity = [100_000 + 10 * i for i in range(100)]
    m = compute_metrics(100_000, dates, equity, trades, [0.5] * 100, [400 + i for i in range(100)])
    assert m["trades"] == 4 and m["win_rate_pct"] == 50.0
    assert m["profit_factor"] == pytest.approx(400 / 150, abs=0.01)
    assert m["avg_win"] == 200 and m["avg_loss"] == -75
    assert m["expectancy_r"] == pytest.approx(0.375)
    assert m["avg_holding_days"] == 5.5 and m["avg_exposure_pct"] == 50.0
    assert m["exit_reasons"] == {"trailing_stop": 1, "stop_loss": 3}
    assert m["total_return_pct"] == pytest.approx(0.99, abs=0.01) and m["max_drawdown_pct"] == 0
    assert m["benchmark_return_pct"] == pytest.approx(24.75, abs=0.01)


def test_sin_operaciones_no_revienta():
    m = compute_metrics(1000, [date(2025, 1, 1)], [1000.0], [], [0.0])
    assert m["trades"] == 0 and m["win_rate_pct"] is None and m["profit_factor"] is None
    assert m["expectancy_r"] is None and m["cagr_pct"] is None


def test_cagr_de_un_ano():
    dates = [date(2025, 1, 1), date(2026, 1, 1)]
    m = compute_metrics(100, dates, [100.0, 121.0], [], [0.0, 0.0])
    assert m["cagr_pct"] == pytest.approx(21.0, abs=0.1)


def test_factor_de_beneficio_sin_perdidas_es_none():
    m = compute_metrics(100, [date(2025, 1, 1)], [100.0], [t(10, 1.0)], [0.1])
    assert m["profit_factor"] is None and m["win_rate_pct"] == 100.0
