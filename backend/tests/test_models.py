from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    ExitReason,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Signal,
    Strategy,
    Trade,
    TradeStatus,
)

NOW = datetime(2026, 11, 20, 14, 30, tzinfo=UTC)


def _strategy(session, name="swing-conservadora"):
    s = Strategy(name=name, params={"min_score": 80, "max_positions": 8}, is_default=True)
    session.add(s)
    session.flush()
    return s


def _trade(session, strategy, **kw):
    data = dict(
        strategy_id=strategy.id,
        ticker="AAPL",
        quantity=Decimal("10"),
        entry_price=Decimal("200.0000"),
        entry_at=NOW,
        stop_loss=Decimal("190.0000"),
        take_profit=Decimal("220.0000"),
    )
    data.update(kw)
    t = Trade(**data)
    session.add(t)
    session.flush()
    return t


def test_estrategia_guarda_params_json(session):
    _strategy(session)
    session.commit()
    s = session.scalars(select(Strategy)).one()
    assert s.params["min_score"] == 80
    assert s.is_active is True
    assert s.created_at is not None


def test_nombre_de_estrategia_unico(session):
    _strategy(session)
    with pytest.raises(IntegrityError):
        _strategy(session)


def test_senal_valida_y_rango_de_score(session):
    st = _strategy(session)
    session.add(Signal(strategy_id=st.id, ticker="MSFT", scan_date=NOW, score=Decimal("87.50")))
    session.commit()
    assert session.scalars(select(Signal)).one().score == Decimal("87.50")

    session.add(Signal(strategy_id=st.id, ticker="NVDA", scan_date=NOW, score=Decimal("101")))
    with pytest.raises(IntegrityError):
        session.flush()


def test_una_senal_por_ticker_y_dia(session):
    st = _strategy(session)
    session.add(Signal(strategy_id=st.id, ticker="MSFT", scan_date=NOW, score=Decimal("80")))
    session.flush()
    session.add(Signal(strategy_id=st.id, ticker="MSFT", scan_date=NOW, score=Decimal("90")))
    with pytest.raises(IntegrityError):
        session.flush()


def test_operacion_abierta_por_defecto_y_cierre(session):
    t = _trade(session, _strategy(session))
    assert t.status is TradeStatus.OPEN
    t.status = TradeStatus.CLOSED
    t.exit_price = Decimal("220")
    t.exit_at = NOW
    t.exit_reason = ExitReason.TAKE_PROFIT
    t.pnl = Decimal("200")
    session.commit()
    assert session.get(Trade, t.id).exit_reason is ExitReason.TAKE_PROFIT


def test_long_exige_stop_por_debajo_de_la_entrada(session):
    st = _strategy(session)
    with pytest.raises(IntegrityError):
        _trade(session, st, stop_loss=Decimal("210"))


def test_cantidad_debe_ser_positiva(session):
    st = _strategy(session)
    with pytest.raises(IntegrityError):
        _trade(session, st, quantity=Decimal("0"))


def test_ordenes_enlazadas_a_la_operacion(session):
    t = _trade(session, _strategy(session))
    session.add_all(
        [
            Order(
                trade_id=t.id,
                broker_order_id="alp-1",
                ticker="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("10"),
            ),
            Order(
                trade_id=t.id,
                broker_order_id="alp-2",
                ticker="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.STOP,
                quantity=Decimal("10"),
                stop_price=Decimal("190"),
            ),
        ]
    )
    session.commit()
    session.refresh(t)
    assert {o.side for o in t.orders} == {OrderSide.BUY, OrderSide.SELL}
    assert all(o.status is OrderStatus.NEW for o in t.orders)
    assert all(o.filled_quantity == 0 for o in t.orders)


def test_id_de_orden_del_broker_unico(session):
    for _ in range(2):
        session.add(
            Order(
                broker_order_id="dup",
                ticker="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("1"),
            )
        )
    with pytest.raises(IntegrityError):
        session.flush()


def test_claves_foraneas_se_aplican(session):
    session.add(
        Order(
            trade_id=999,
            ticker="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1"),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
