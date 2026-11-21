"""Estrategias guardadas en la base de datos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Strategy
from app.strategy.params import StrategyParams

DEFAULT_STRATEGY_NAME = "swing-conservadora"


def get_or_create_default_strategy(session: Session) -> Strategy:
    strategy = session.scalar(select(Strategy).where(Strategy.name == DEFAULT_STRATEGY_NAME))
    if strategy is None:
        strategy = Strategy(
            name=DEFAULT_STRATEGY_NAME,
            description="Swing trading conservador LONG sobre S&P500 (multi-timeframe 1D/4H/1H)",
            params=StrategyParams().model_dump(),
            is_default=True,
        )
        session.add(strategy)
        session.commit()
    return strategy


def params_of(strategy: Strategy) -> StrategyParams:
    """Parámetros validados de una estrategia (los que falten toman el valor por defecto)."""
    return StrategyParams.model_validate(strategy.params or {})
