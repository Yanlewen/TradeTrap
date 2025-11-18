"""Paper trading (simulated) exchange adapter"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_exchange import ExchangeBase, ExchangeType, Order, OrderStatus
from ..data_sources.local_price_provider import LocalPriceProvider

logger = logging.getLogger(__name__)


class PaperTrading(ExchangeBase):
    """
    Simulated trading on paper (no real money, no real orders).

    Used for backtesting and strategy development without risking real capital.
    """

    def __init__(self, initial_balance: float = 100000.0, market_type: str = "crypto"):
        """
        Initialize paper trading exchange.

        Args:
            initial_balance: Starting capital for simulated trading
            market_type: Market type ("crypto" or "stock")
        """
        super().__init__(ExchangeType.PAPER)
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}  # {symbol: position_data}
        self.is_connected = True
        self.current_date: Optional[str] = None  # For historical backtesting
        self.market_type = market_type  # "crypto" or "stock"
        self._price_provider = LocalPriceProvider()

    # ============ Connection Management ============

    async def connect(self) -> bool:
        """Paper trading is always connected"""
        self.is_connected = True
        logger.info("Paper trading connected (simulated)")
        return True

    async def disconnect(self) -> bool:
        """Disconnect paper trading"""
        self.is_connected = False
        logger.info("Paper trading disconnected")
        return True

    async def validate_connection(self) -> bool:
        """Paper trading is always valid"""
        return self.is_connected

    # ============ Account Information ============

    async def get_balance(self) -> Dict[str, float]:
        """
        Get simulated account balances.

        Returns:
            Dictionary with USDT and other assets
        """
        balances = {"USDT": self.balance}
        # Add positions as assets
        for symbol, pos_data in self.positions.items():
            asset = symbol.replace("USDT", "")
            balances[asset] = pos_data["quantity"]
        return balances

    async def get_asset_balance(self, asset: str) -> float:
        """
        Get balance for a specific asset.

        Args:
            asset: Asset symbol

        Returns:
            Available balance
        """
        if asset == "USDT":
            return self.balance

        # Check if we have a position
        for symbol, pos_data in self.positions.items():
            if symbol.startswith(asset):
                return pos_data["quantity"]

        return 0.0

    # ============ Market Data ============

    def set_current_date(self, date: str):
        """
        Set current date for historical backtesting.

        Args:
            date: Date string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        """
        self.current_date = date
        logger.debug(f"Set current date for backtesting: {date}")

    async def get_current_price(self, symbol: str) -> float:
        """
        Get current simulated price from local historical data.
        Supports historical backtesting when current_date is set.

        Args:
            symbol: Trading symbol in exchange format

        Returns:
            Current price
        """
        try:
            ticker_symbol = self._denormalize_symbol(symbol)
            target_dt: Optional[datetime] = None
            if self.current_date:
                if " " in self.current_date:
                    target_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    target_dt = datetime.strptime(self.current_date, "%Y-%m-%d")
            price = self._price_provider.get_price(ticker_symbol, target_dt)
            if price is None:
                logger.warning("No local price data for %s", ticker_symbol)
                return 0.0
            return float(price)
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return 0.0

    async def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker data based on local history.
        Supports historical backtesting when current_date is set.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data dictionary
        """
        try:
            ticker_symbol = self._denormalize_symbol(symbol)
            end_dt: Optional[datetime] = None
            if self.current_date:
                if " " in self.current_date:
                    end_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    end_dt = datetime.strptime(self.current_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(hours=24) if end_dt else None

            df = self._price_provider.get_history(ticker_symbol, start_dt, end_dt, interval="60min")
            if df.empty:
                return {}

            window = df.tail(24)
            if window.empty:
                window = df

            return {
                "symbol": symbol,
                "current_price": float(window["Close"].iloc[-1]),
                "24h_high": float(window["High"].max()),
                "24h_low": float(window["Low"].min()),
                "24h_volume": float(window["Volume"].sum()),
                "24h_change": float(
                    (window["Close"].iloc[-1] - window["Close"].iloc[0]) / window["Close"].iloc[0] * 100
                ) if window["Close"].iloc[0] else 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get 24h ticker for {symbol}: {e}")
            return {}

    # ============ Order Management ============

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_type: str = "limit",
        **kwargs,
    ) -> Order:
        """
        Place a simulated order.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Order quantity
            price: Order price (None for market)
            order_type: "limit" or "market"
            **kwargs: Additional parameters

        Returns:
            Order object
        """
        order_id = str(uuid.uuid4())[:8]

        # Get current price if market order
        if price is None or order_type == "market":
            price = await self.get_current_price(symbol)

        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side.lower(),
            quantity=quantity,
            price=price,
            order_type=order_type,
            trade_type=kwargs.get("trade_type"),
        )

        # Immediately fill market orders
        if order_type == "market":
            await self._fill_order(order)

        self.orders[order_id] = order
        logger.info(
            f"Order placed: {order_id} - {side} {quantity} {symbol} @ ${price:.2f}"
        )
        return order

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an order (for paper trading, just mark as cancelled).

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            True if successful
        """
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"Order cancelled: {order_id}")
            return True
        return False

    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """
        Get order status.

        Args:
            symbol: Trading symbol
            order_id: Order ID

        Returns:
            Order status
        """
        if order_id in self.orders:
            return self.orders[order_id].status
        return OrderStatus.EXPIRED

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders
        """
        open_orders = [
            o
            for o in self.orders.values()
            if o.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]
        ]
        if symbol:
            open_orders = [o for o in open_orders if o.symbol == symbol]
        return open_orders

    async def get_order_history(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Order]:
        """
        Get order history.

        Args:
            symbol: Optional symbol filter
            limit: Max orders to return

        Returns:
            Order history
        """
        history = self.order_history
        if symbol:
            history = [o for o in history if o.symbol == symbol]
        return history[-limit:]

    # ============ Position Management ============

    async def get_open_positions(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get open positions.

        Args:
            symbol: Optional symbol filter

        Returns:
            Dictionary of positions
        """
        if symbol:
            if symbol in self.positions:
                return {symbol: self.positions[symbol]}
            return {}
        return self.positions.copy()

    async def get_position_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific position.

        Args:
            symbol: Trading symbol

        Returns:
            Position details or None
        """
        return self.positions.get(symbol)

    # ============ Trade Execution ============

    async def execute_buy(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs,
    ) -> Optional[Order]:
        """
        Execute a buy order.

        Args:
            symbol: Trading symbol
            quantity: Amount to buy
            price: Price (None for market)
            **kwargs: Additional parameters

        Returns:
            Order or None
        """
        # Get price
        if price is None:
            price = await self.get_current_price(symbol)

        notional = quantity * price

        # Check balance
        if notional > self.balance:
            logger.warning(
                f"Insufficient balance for buy: need ${notional:.2f}, have ${self.balance:.2f}"
            )
            return None

        # Place and fill order
        order = await self.place_order(symbol, "buy", quantity, price, "market")
        return order

    async def execute_sell(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs,
    ) -> Optional[Order]:
        """
        Execute a sell order.

        Args:
            symbol: Trading symbol
            quantity: Amount to sell
            price: Price (None for market)
            **kwargs: Additional parameters

        Returns:
            Order or None
        """
        # Check if we have the position
        if symbol not in self.positions:
            logger.warning(f"No position to sell for {symbol}")
            return None

        if self.positions[symbol]["quantity"] < quantity:
            logger.warning(
                f"Insufficient position: have {self.positions[symbol]['quantity']}, "
                f"trying to sell {quantity}"
            )
            return None

        # Get price
        if price is None:
            price = await self.get_current_price(symbol)

        # Place and fill order
        order = await self.place_order(symbol, "sell", quantity, price, "market")
        return order

    # ============ Utilities ============

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to paper trading format based on market type.

        Args:
            symbol: Original symbol (e.g., "BTC-USD" for crypto, "AAPL" for stock)

        Returns:
            Normalized symbol (e.g., "BTCUSDT" for crypto, "AAPL" for stock)
        """
        if self.market_type == "crypto":
            return symbol.replace("-USD", "USDT").replace("-USDT", "USDT")
        if self.market_type == "stock":
            return symbol.upper()
        return symbol

    def _denormalize_symbol(self, symbol: str) -> str:
        """
        Convert from exchange format back to yfinance format.

        Args:
            symbol: Exchange format (e.g., "BTCUSDT" for crypto, "AAPL" for stock)

        Returns:
            yfinance format (e.g., "BTC-USD" for crypto, "AAPL" for stock)
        """
        if self.market_type == "crypto":
            return symbol.replace("USDT", "-USD")
        elif self.market_type == "stock":
            return symbol  # Stock symbols don't need conversion
        return symbol

    async def get_fee_tier(self) -> Dict[str, float]:
        """
        Paper trading has no fees.

        Returns:
            Fee dictionary
        """
        return {"maker": 0.0, "taker": 0.0}

    async def get_trading_limits(self, symbol: str) -> Dict[str, float]:
        """
        Get trading limits (paper trading has no limits).

        Args:
            symbol: Trading symbol

        Returns:
            Limits dictionary
        """
        return {
            "min_quantity": 0.0001,
            "max_quantity": 1000000,
            "quantity_precision": 8,
            "min_notional": 1.0,
        }

    # ============ Private Methods ============

    async def _fill_order(self, order: Order) -> bool:
        """
        Fill an order (update balance, positions).

        Args:
            order: Order to fill

        Returns:
            True if filled successfully
        """
        try:
            if order.side == "buy":
                notional = order.quantity * order.price
                self.balance -= notional

                # Update position
                if order.symbol in self.positions:
                    self.positions[order.symbol]["quantity"] += order.quantity
                    # Update entry price (average)
                    old_notional = self.positions[order.symbol]["entry_price"] * (
                        self.positions[order.symbol]["quantity"] - order.quantity
                    )
                    total_notional = old_notional + notional
                    total_quantity = self.positions[order.symbol]["quantity"]
                    self.positions[order.symbol]["entry_price"] = (
                        total_notional / total_quantity
                    )
                else:
                    self.positions[order.symbol] = {
                        "quantity": order.quantity,
                        "entry_price": order.price,
                        "entry_time": order.created_at,
                    }

                order.filled_quantity = order.quantity
                order.filled_price = order.price
                order.status = OrderStatus.FILLED

            elif order.side == "sell":
                notional = order.quantity * order.price
                self.balance += notional

                # Update position
                if order.symbol in self.positions:
                    self.positions[order.symbol]["quantity"] -= order.quantity
                    if self.positions[order.symbol]["quantity"] <= 0:
                        del self.positions[order.symbol]

                order.filled_quantity = order.quantity
                order.filled_price = order.price
                order.status = OrderStatus.FILLED

            self.order_history.append(order)
            logger.info(f"Order filled: {order.order_id} - {order.status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to fill order: {e}")
            return False

    async def reset(self, initial_balance: float):
        """
        Reset paper trading to initial state.

        Args:
            initial_balance: New starting balance
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions.clear()
        self.orders.clear()
        self.order_history.clear()
        logger.info(f"Paper trading reset with balance: ${initial_balance:,.2f}")
