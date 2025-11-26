"""Trading execution and position management (refactored)"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .exchanges import ExchangeBase, Order, OrderStatus, PaperTrading
from .models import (
    AutoTradingConfig,
    PortfolioValueSnapshot,
    Position,
    PositionHistorySnapshot,
    TechnicalIndicators,
    TradeAction,
    TradeHistoryRecord,
    TradeType,
)
from .position_ledger import PositionLedger
from .position_manager import PositionManager
from .position_persistence import PositionPersistence
from .trade_recorder import TradeRecorder

logger = logging.getLogger(__name__)


class TradingExecutor:
    """
    Orchestrates trade execution using specialized modules.

    This is the main facade that coordinates:
    - Position management (via PositionManager)
    - Trade recording (via TradeRecorder)
    - Cash management (via PositionManager)
    """

    def __init__(
        self,
        config: AutoTradingConfig,
        exchange: Optional[ExchangeBase] = None,
        position_ledger: Optional[PositionLedger] = None,
        position_persistence: Optional[PositionPersistence] = None,
    ):
        """
        Initialize trading executor.

        Args:
            config: Auto trading configuration
            exchange: Exchange adapter (optional)
            position_ledger: Position ledger for updating real ledger (optional)
            position_persistence: Position persistence for reading agent view (optional)
        """
        self.config = config
        self.initial_capital = config.initial_capital

        # Exchange adapter (defaults to in-memory paper trading)
        self.exchange: ExchangeBase = exchange or PaperTrading(
            initial_balance=config.initial_capital
        )
        self.exchange_type = self.exchange.exchange_type

        # Use specialized modules
        self._position_manager = PositionManager(config.initial_capital)
        self._trade_recorder = TradeRecorder()
        
        # Position ledger and persistence (for ledger-based trading)
        self.position_ledger = position_ledger
        self.position_persistence = position_persistence

    async def execute_trade(
        self,
        symbol: str,
        action: TradeAction,
        trade_type: TradeType,
        indicators: TechnicalIndicators,
        trading_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a trade (open or close position).

        Args:
            symbol: Trading symbol
            action: Trade action (buy/sell)
            trade_type: Trade type (long/short)
            indicators: Current technical indicators
            trading_date: Optional trading date string (for backtesting, format: "YYYY-MM-DD HH:MM:SS")
                         If not provided, uses current system time

        Returns:
            Trade execution details or None if execution failed
        """
        try:
            current_price = indicators.close_price
            # Use trading_date if provided (for backtesting), otherwise use current time
            if trading_date:
                try:
                    if " " in trading_date:
                        timestamp = datetime.strptime(trading_date, "%Y-%m-%d %H:%M:%S")
                    else:
                        timestamp = datetime.strptime(trading_date, "%Y-%m-%d")
                    # Ensure timezone awareness (assume UTC for backtesting)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(
                        f"Failed to parse trading_date '{trading_date}', using current time"
                    )
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

            if action == TradeAction.BUY:
                return await self._execute_buy(
                    symbol, trade_type, current_price, timestamp
                )
            if action == TradeAction.SELL:
                return await self._execute_sell(
                    symbol, trade_type, current_price, timestamp
                )

            return None

        except Exception as e:
            logger.error(f"Failed to execute trade for {symbol}: {e}")
            return None

    async def _execute_buy(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Open a new position"""
        # If ledger is available, use ledger-based execution
        if self.position_ledger and self.position_persistence:
            return await self._execute_buy_with_ledger(
                symbol, trade_type, current_price, timestamp
            )
        
        # Legacy execution (direct memory management)
        # Check if we already have a position
        if self._position_manager.get_position(symbol) is not None:
            logger.info(f"Position already exists for {symbol}, skipping")
            return None

        # Check max positions limit
        if self._position_manager.get_positions_count() >= self.config.max_positions:
            logger.info(f"Max positions reached ({self.config.max_positions})")
            return None

        # Calculate position size
        available_cash = self._position_manager.get_available_cash()
        risk_amount = available_cash * self.config.risk_per_trade
        quantity = risk_amount / current_price if current_price > 0 else 0.0
        
        # For stock market, quantity must be an integer (whole shares only)
        # For crypto market, fractional quantities are allowed
        if self.config.market_type == "stock":
            quantity = math.floor(quantity)  # Round down to whole shares
            if quantity <= 0:
                logger.warning(
                    f"Calculated stock quantity is zero or negative ({quantity}); "
                    f"insufficient funds for at least 1 share at ${current_price:.2f}"
                )
                return None
        
        if quantity <= 0:
            logger.warning("Calculated quantity is non-positive; skipping trade")
            return None
        
        # Recalculate notional based on adjusted quantity (important for stock market)
        notional = quantity * current_price

        # Check if we have enough cash
        if notional > available_cash:
            logger.warning(
                f"Insufficient cash: need ${notional:.2f}, have ${available_cash:.2f}"
            )
            return None

        side = "buy" if trade_type == TradeType.LONG else "sell"
        order = await self._submit_order(
            symbol=symbol,
            side=side,
            quantity=abs(quantity),
            trade_type=trade_type,
        )

        if order is None or order.status in {
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
        }:
            logger.warning("Exchange rejected open order for %s", symbol)
            return None

        fill_price = order.price or current_price
        notional = abs(quantity) * fill_price

        # Create and open position
        position = Position(
            symbol=symbol,
            entry_price=fill_price,
            quantity=abs(quantity) if trade_type == TradeType.LONG else -abs(quantity),
            entry_time=timestamp,
            trade_type=trade_type,
            notional=notional,
        )

        if not self._position_manager.open_position(symbol, position):
            return None

        # Record trade
        portfolio_value = self.get_portfolio_value()
        trade_record = TradeHistoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            action="opened",
            trade_type=trade_type.value,
            price=fill_price,
            quantity=abs(position.quantity),
            notional=notional,
            pnl=None,
            portfolio_value_after=portfolio_value,
            cash_after=self._position_manager.get_available_cash(),
        )
        self._trade_recorder.record_trade(trade_record)

        return {
            "action": "opened",
            "trade_type": trade_type.value,
            "symbol": symbol,
            "entry_price": fill_price,
            "quantity": position.quantity,
            "notional": notional,
            "timestamp": timestamp,
            "order_id": order.order_id,
            "exchange": self.exchange_type.value,
        }
    
    async def _execute_buy_with_ledger(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Execute buy using ledger (file-based position management)"""
        # Load agent view of positions from file (can be tampered by hook)
        agent_position_record = self.position_persistence.load_latest_position()
        if not agent_position_record:
            logger.warning("Failed to load agent position view from file")
            return None
        
        agent_positions = agent_position_record.get("positions", {})
        agent_position_id = agent_position_record.get("id", 0)
        
        # Check if we already have a position (from agent's view)
        if agent_positions.get(symbol, 0) != 0:
            logger.info(f"Position already exists for {symbol} (agent view), skipping")
            return None
        
        # Count non-zero positions (excluding CASH)
        non_zero_positions = sum(1 for k, v in agent_positions.items() 
                                if k != "CASH" and v != 0)
        if non_zero_positions >= self.config.max_positions:
            logger.info(f"Max positions reached ({self.config.max_positions})")
            return None
        
        # Calculate position size based on agent's view of cash
        available_cash = agent_positions.get("CASH", 0.0)
        risk_amount = available_cash * self.config.risk_per_trade
        quantity = risk_amount / current_price if current_price > 0 else 0.0
        
        # For stock market, quantity must be an integer (whole shares only)
        if self.config.market_type == "stock":
            quantity = math.floor(quantity)
            if quantity <= 0:
                logger.warning(
                    f"Calculated stock quantity is zero or negative ({quantity}); "
                    f"insufficient funds for at least 1 share at ${current_price:.2f}"
                )
                return None
        
        if quantity <= 0:
            logger.warning("Calculated quantity is non-positive; skipping trade")
            return None
        
        notional = quantity * current_price
        
        # Check if we have enough cash (from agent's view)
        if notional > available_cash:
            logger.warning(
                f"Insufficient cash: need ${notional:.2f}, have ${available_cash:.2f} (agent view)"
            )
            return None
        
        # Submit order to exchange
        side = "buy" if trade_type == TradeType.LONG else "sell"
        order = await self._submit_order(
            symbol=symbol,
            side=side,
            quantity=abs(quantity),
            trade_type=trade_type,
        )
        
        if order is None or order.status in {
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
        }:
            logger.warning("Exchange rejected open order for %s", symbol)
            return None
        
        fill_price = order.price or current_price
        notional = abs(quantity) * fill_price
        
        # Build order payload for ledger
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        order_payload = {
            "id": agent_position_id + 1,
            "timestamp": timestamp_str,
            "action": "buy",
            "symbol": symbol,
            "amount": int(quantity),
            "price": fill_price,
            "market": self.config.market_type,
        }
        
        staged_record = {
            "order": order_payload,
            "position_before": agent_positions,
        }
        
        # Process through ledger (updates real ledger, writes audit)
        try:
            result_record = self.position_ledger.process(staged_record)
            
            # Sync ledger result to memory for portfolio calculations
            self._sync_ledger_to_memory(result_record)
            
            # Record trade for history
            portfolio_value = self.get_portfolio_value()
            trade_record = TradeHistoryRecord(
                timestamp=timestamp,
                symbol=symbol,
                action="opened",
                trade_type=trade_type.value,
                price=fill_price,
                quantity=abs(quantity),
                notional=notional,
                pnl=None,
                portfolio_value_after=portfolio_value,
                cash_after=self._position_manager.get_available_cash(),
            )
            self._trade_recorder.record_trade(trade_record)
            
            return {
                "action": "opened",
                "trade_type": trade_type.value,
                "symbol": symbol,
                "entry_price": fill_price,
                "quantity": quantity if trade_type == TradeType.LONG else -quantity,
                "notional": notional,
                "timestamp": timestamp,
                "order_id": order.order_id,
                "exchange": self.exchange_type.value,
            }
        except Exception as e:
            logger.error(f"Ledger processing failed for buy {symbol}: {e}")
            return None

    async def _execute_sell(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Close an existing position"""
        # If ledger is available, use ledger-based execution
        if self.position_ledger and self.position_persistence:
            return await self._execute_sell_with_ledger(
                symbol, trade_type, current_price, timestamp
            )
        
        # Legacy execution (direct memory management)
        # Get position
        position = self._position_manager.get_position(symbol)
        if position is None:
            return None

        # Check if trade type matches
        if position.trade_type != trade_type:
            return None

        side = "sell" if trade_type == TradeType.LONG else "buy"
        order = await self._submit_order(
            symbol=symbol,
            side=side,
            quantity=abs(position.quantity),
            trade_type=trade_type,
        )

        if order is None:
            logger.warning("Failed to close position on %s via exchange", symbol)
            return None

        exit_price = order.price or current_price
        pnl = self._position_manager.calculate_position_pnl(position, exit_price)
        exit_notional = abs(position.quantity) * exit_price

        # Close position locally
        self._position_manager.close_position(symbol)
        self._position_manager.release_cash(position.notional, pnl)

        # Record trade
        holding_time = timestamp - position.entry_time
        portfolio_value = self.get_portfolio_value()
        trade_record = TradeHistoryRecord(
            timestamp=timestamp,
            symbol=symbol,
            action="closed",
            trade_type=trade_type.value,
            price=exit_price,
            quantity=abs(position.quantity),
            notional=exit_notional,
            pnl=pnl,
            portfolio_value_after=portfolio_value,
            cash_after=self._position_manager.get_available_cash(),
        )
        self._trade_recorder.record_trade(trade_record)

        return {
            "action": "closed",
            "trade_type": trade_type.value,
            "symbol": symbol,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": position.quantity,
            "entry_notional": position.notional,
            "exit_notional": exit_notional,
            "pnl": pnl,
            "holding_time": holding_time,
            "timestamp": timestamp,
            "order_id": order.order_id,
            "exchange": self.exchange_type.value,
        }
    
    async def _execute_sell_with_ledger(
        self,
        symbol: str,
        trade_type: TradeType,
        current_price: float,
        timestamp: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Execute sell using ledger (file-based position management)"""
        # Load agent view of positions from file (can be tampered by hook)
        agent_position_record = self.position_persistence.load_latest_position()
        if not agent_position_record:
            logger.warning("Failed to load agent position view from file")
            return None
        
        agent_positions = agent_position_record.get("positions", {})
        agent_position_id = agent_position_record.get("id", 0)
        
        # Check if we have a position (from agent's view)
        held_quantity = agent_positions.get(symbol, 0)
        if held_quantity == 0:
            logger.info(f"No position found for {symbol} (agent view), skipping")
            return None
        
        # Determine sell quantity (sell all)
        sell_quantity = int(abs(held_quantity))
        if sell_quantity <= 0:
            return None
        
        # Submit order to exchange
        side = "sell" if trade_type == TradeType.LONG else "buy"
        order = await self._submit_order(
            symbol=symbol,
            side=side,
            quantity=sell_quantity,
            trade_type=trade_type,
        )
        
        if order is None:
            logger.warning("Failed to close position on %s via exchange", symbol)
            return None
        
        exit_price = order.price or current_price
        exit_notional = sell_quantity * exit_price
        
        # Build order payload for ledger
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        order_payload = {
            "id": agent_position_id + 1,
            "timestamp": timestamp_str,
            "action": "sell",
            "symbol": symbol,
            "amount": sell_quantity,
            "price": exit_price,
            "market": self.config.market_type,
        }
        
        staged_record = {
            "order": order_payload,
            "position_before": agent_positions,
        }
        
        # Process through ledger (updates real ledger, writes audit)
        try:
            result_record = self.position_ledger.process(staged_record)
            
            # Sync ledger result to memory for portfolio calculations
            self._sync_ledger_to_memory(result_record)
            
            # Calculate P&L (approximate, we don't have entry price from file)
            # For now, use current price as entry price approximation
            pnl = 0.0  # We don't track entry price in position.jsonl format
            entry_price = current_price  # Approximation
            
            # Record trade for history
            portfolio_value = self.get_portfolio_value()
            trade_record = TradeHistoryRecord(
                timestamp=timestamp,
                symbol=symbol,
                action="closed",
                trade_type=trade_type.value,
                price=exit_price,
                quantity=sell_quantity,
                notional=exit_notional,
                pnl=pnl,
                portfolio_value_after=portfolio_value,
                cash_after=self._position_manager.get_available_cash(),
            )
            self._trade_recorder.record_trade(trade_record)
            
            return {
                "action": "closed",
                "trade_type": trade_type.value,
                "symbol": symbol,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": -sell_quantity if trade_type == TradeType.LONG else sell_quantity,
                "entry_notional": sell_quantity * entry_price,
                "exit_notional": exit_notional,
                "pnl": pnl,
                "holding_time": None,  # Not tracked in file format
                "timestamp": timestamp,
                "order_id": order.order_id,
                "exchange": self.exchange_type.value,
            }
        except Exception as e:
            logger.error(f"Ledger processing failed for sell {symbol}: {e}")
            return None
    
    def _sync_ledger_to_memory(self, ledger_record: Dict[str, Any]):
        """
        Sync ledger record to in-memory PositionManager for portfolio calculations.
        This is needed for get_portfolio_value() and other calculations.
        """
        positions_dict = ledger_record.get("positions", {})
        cash = positions_dict.get("CASH", 0.0)
        
        # Reset position manager with new cash
        self._position_manager.reset(self.initial_capital)
        self._position_manager._cash_management.total_cash = cash
        self._position_manager._cash_management.available_cash = cash
        self._position_manager._cash_management.cash_in_trades = 0.0
        
        # Reconstruct positions from ledger (approximate, since we don't have entry prices)
        # For portfolio value calculation, we'll use current prices
        # This is just to keep memory state roughly in sync
        self._position_manager._positions.clear()
        
        # Note: We can't fully reconstruct Position objects without entry prices,
        # but this is okay since we mainly use ledger for source of truth

    async def _submit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        trade_type: TradeType,
        order_type: str = "market",
    ) -> Optional[Order]:
        try:
            if not self.exchange.is_connected:
                await self.exchange.connect()
            return await self.exchange.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=None,
                order_type=order_type,
                trade_type=trade_type,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Order submission failed (%s %s %s): %s",
                side,
                quantity,
                symbol,
                exc,
            )
            return None

    # ============ Portfolio Queries ============

    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        total_value, _, _ = self._position_manager.calculate_portfolio_value()
        return total_value

    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary"""
        return self._position_manager.get_portfolio_summary()

    def get_current_capital(self) -> float:
        """Get available cash"""
        return self._position_manager.get_available_cash()

    @property
    def current_capital(self) -> float:
        """Property for backward compatibility"""
        return self._position_manager.get_available_cash()

    @property
    def positions(self) -> Dict[str, Position]:
        """Property for backward compatibility"""
        return self._position_manager.get_all_positions()

    # ============ History Management ============

    def snapshot_positions(self, timestamp: datetime):
        """Take a snapshot of all positions"""
        self._position_manager.snapshot_positions(timestamp)

    def snapshot_portfolio(self, timestamp: datetime):
        """Take a snapshot of portfolio value"""
        self._position_manager.snapshot_portfolio(timestamp)

    def get_trade_history(self) -> List[TradeHistoryRecord]:
        """Get all trade history"""
        return self._trade_recorder.get_all_trades()

    def get_position_history(self) -> List[PositionHistorySnapshot]:
        """Get all position snapshots"""
        return self._position_manager.get_position_history()

    def get_portfolio_history(self) -> List[PortfolioValueSnapshot]:
        """Get all portfolio snapshots"""
        return self._position_manager.get_portfolio_history()

    # ============ Statistics ============

    def get_trade_statistics(self) -> Dict:
        """Get trading statistics"""
        return self._trade_recorder.get_trade_statistics()

    def get_symbol_statistics(self, symbol: str) -> Dict:
        """Get statistics for a symbol"""
        return self._trade_recorder.get_symbol_statistics(symbol)

    def get_daily_statistics(self) -> Dict[str, Dict]:
        """Get daily P&L breakdown"""
        return self._trade_recorder.get_daily_statistics()

    # ============ Management ============

    def reset(self, initial_capital: float):
        """Reset executor state"""
        self._position_manager.reset(initial_capital)
        self._trade_recorder.reset()
