"""
Alpaca broker provider.

Adapts Alpaca's trading API to the internal BrokerProvider interface.
"""

from __future__ import annotations

from decimal import Decimal

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import (
    OrderSide as AlpacaOrderSide,
    OrderStatus as AlpacaOrderStatus,
    OrderType as AlpacaOrderType,
)
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    StopLimitOrderRequest,
    StopOrderRequest,
)
from alpaca.trading.timeframe import TimeInForce

from app.broker.models import (
    Account,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from app.broker.provider import BrokerProvider
from app.config.settings import settings


class AlpacaBrokerProvider(BrokerProvider):
    """Alpaca implementation of the broker abstraction."""

    def __init__(self) -> None:
        self._client: TradingClient | None = None

    @property
    def client(self) -> TradingClient:
        """Return the lazily initialized Alpaca trading client."""

        if self._client is None:
            api_key = settings.broker.api_key
            secret_key = settings.broker.secret_key

            if not api_key or not secret_key:
                raise RuntimeError(
                    "Alpaca API credentials are not configured."
                )

            self._client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=settings.broker.paper_trading,
            )

        return self._client

    def get_account(self) -> Account:
        """Return normalized account information."""

        account = self.client.get_account()

        return Account(
            account_id=str(account.id),
            buying_power=Decimal(str(account.buying_power)),
            cash=Decimal(str(account.cash)),
            portfolio_value=Decimal(
                str(account.portfolio_value)
            ),
            equity=Decimal(str(account.equity)),
        )

    def get_positions(self) -> list[Position]:
        """Return all open positions."""

        positions = self.client.get_all_positions()

        return [
            self._normalize_position(position)
            for position in positions
        ]

    def get_position(
        self,
        symbol: str,
    ) -> Position | None:
        """Return a single open position."""

        if not symbol:
            raise ValueError(
                "symbol cannot be empty."
            )

        try:
            position = self.client.get_open_position(
                symbol
            )
        except Exception:
            return None

        return self._normalize_position(position)

    def submit_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
    ) -> Order:
        """Submit an order to Alpaca."""

        if quantity <= 0:
            raise ValueError(
                "quantity must be greater than zero."
            )

        if not symbol:
            raise ValueError(
                "symbol cannot be empty."
            )

        alpaca_side = (
            AlpacaOrderSide.BUY
            if side == OrderSide.BUY
            else AlpacaOrderSide.SELL
        )

        request = self._build_order_request(
            symbol=symbol,
            side=alpaca_side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
        )

        order = self.client.submit_order(
            order_data=request,
        )

        return self._normalize_order(order)

    def cancel_order(
        self,
        order_id: str,
    ) -> None:
        """Cancel an existing order."""

        if not order_id:
            raise ValueError(
                "order_id cannot be empty."
            )

        self.client.cancel_order_by_id(
            order_id
        )

    def get_order(
        self,
        order_id: str,
    ) -> Order | None:
        """Return an order by ID."""

        if not order_id:
            raise ValueError(
                "order_id cannot be empty."
            )

        try:
            order = self.client.get_order_by_id(
                order_id
            )
        except Exception:
            return None

        return self._normalize_order(order)

    @staticmethod
    def _build_order_request(
        *,
        symbol: str,
        side: AlpacaOrderSide,
        order_type: OrderType,
        quantity: Decimal,
        limit_price: Decimal | None,
        stop_price: Decimal | None,
    ):
        """Build the appropriate Alpaca order request."""

        common = {
            "symbol": symbol,
            "qty": float(quantity),
            "side": side,
            "time_in_force": TimeInForce.DAY,
        }

        if order_type == OrderType.MARKET:
            return MarketOrderRequest(**common)

        if order_type == OrderType.LIMIT:
            if limit_price is None:
                raise ValueError(
                    "limit_price is required for limit orders."
                )

            return LimitOrderRequest(
                **common,
                limit_price=float(limit_price),
            )

        if order_type == OrderType.STOP:
            if stop_price is None:
                raise ValueError(
                    "stop_price is required for stop orders."
                )

            return StopOrderRequest(
                **common,
                stop_price=float(stop_price),
            )

        if order_type == OrderType.STOP_LIMIT:
            if stop_price is None:
                raise ValueError(
                    "stop_price is required for stop-limit orders."
                )

            if limit_price is None:
                raise ValueError(
                    "limit_price is required for stop-limit orders."
                )

            return StopLimitOrderRequest(
                **common,
                stop_price=float(stop_price),
                limit_price=float(limit_price),
            )

        raise ValueError(
            f"Unsupported order type: {order_type}"
        )

    @staticmethod
    def _normalize_position(position) -> Position:
        """Normalize an Alpaca position."""

        return Position(
            symbol=position.symbol,
            quantity=Decimal(str(position.qty)),
            average_entry_price=Decimal(
                str(position.avg_entry_price)
            ),
            market_price=Decimal(
                str(position.current_price)
            ),
            market_value=Decimal(
                str(position.market_value)
            ),
            unrealized_pnl=Decimal(
                str(position.unrealized_pl)
            ),
        )

    @staticmethod
    def _normalize_order(order) -> Order:
        """Normalize an Alpaca order."""

        return Order(
            order_id=str(order.id),
            symbol=order.symbol,
            side=(
                OrderSide.BUY
                if order.side == AlpacaOrderSide.BUY
                else OrderSide.SELL
            ),
            order_type=AlpacaBrokerProvider._normalize_order_type(
                order.order_type
            ),
            quantity=Decimal(str(order.qty)),
            status=AlpacaBrokerProvider._normalize_order_status(
                order.status
            ),
            limit_price=(
                Decimal(str(order.limit_price))
                if order.limit_price is not None
                else None
            ),
            stop_price=(
                Decimal(str(order.stop_price))
                if order.stop_price is not None
                else None
            ),
            filled_quantity=Decimal(
                str(order.filled_qty or 0)
            ),
            average_fill_price=(
                Decimal(str(order.filled_avg_price))
                if order.filled_avg_price is not None
                else None
            ),
        )

    @staticmethod
    def _normalize_order_type(
        order_type,
    ) -> OrderType:
        """Normalize an Alpaca order type."""

        mapping = {
            AlpacaOrderType.MARKET: OrderType.MARKET,
            AlpacaOrderType.LIMIT: OrderType.LIMIT,
            AlpacaOrderType.STOP: OrderType.STOP,
            AlpacaOrderType.STOP_LIMIT: OrderType.STOP_LIMIT,
        }

        try:
            return mapping[order_type]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported Alpaca order type: {order_type}"
            ) from exc

    @staticmethod
    def _normalize_order_status(
        order_status,
    ) -> OrderStatus:
        """Normalize an Alpaca order status."""

        mapping = {
            AlpacaOrderStatus.NEW: OrderStatus.NEW,
            AlpacaOrderStatus.ACCEPTED: OrderStatus.ACCEPTED,
            AlpacaOrderStatus.PENDING_NEW: OrderStatus.PENDING,
            AlpacaOrderStatus.FILLED: OrderStatus.FILLED,
            AlpacaOrderStatus.PARTIALLY_FILLED:
                OrderStatus.PARTIALLY_FILLED,
            AlpacaOrderStatus.CANCELED: OrderStatus.CANCELLED,
            AlpacaOrderStatus.REJECTED: OrderStatus.REJECTED,
            AlpacaOrderStatus.EXPIRED: OrderStatus.EXPIRED,
        }

        try:
            return mapping[order_status]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported Alpaca order status: {order_status}"
            ) from exc


alpaca_broker_provider = AlpacaBrokerProvider()