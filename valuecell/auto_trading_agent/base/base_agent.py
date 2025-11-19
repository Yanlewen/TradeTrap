"""Base agent class for auto trading - common logic for both crypto and stock"""

import asyncio
import json
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logger first
logger = logging.getLogger(__name__)

from langchain_openai import ChatOpenAI


class Model:
    """
    Minimal wrapper so现有代码保持使用 `Model(...)` 语义，
    底层固定走 langchain 的 ChatOpenAI。
    """

    def __init__(self, id: str, **kwargs):
        self.id = id
        model_name = id.split("/", 1)[-1] if "/" in id else id
        self._client = ChatOpenAI(
            model=model_name,
            temperature=kwargs.get("temperature", 0),
            **{k: v for k, v in kwargs.items() if k != "temperature"},
        )

    def __call__(self, *args, **kwargs):
        return self._client


_MODEL_AVAILABLE = True

# Add project root to path for importing tools
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ..constants import ENV_SIGNAL_MODEL_ID
from ..exchanges import (
    ExchangeBase,
    ExchangeType,
    PaperTrading,
)
from ..market_data import MarketDataProvider
from ..models import SUPPORTED_EXCHANGES, SUPPORTED_NETWORKS
from ..portfolio_decision_manager import (
    AssetAnalysis,
    PortfolioDecisionManager,
)
from ..technical_analysis import AISignalGenerator, TechnicalAnalyzer
from ..trading_executor import TradingExecutor
from ..position_persistence import PositionPersistence
from .base_config import BaseTradingConfig

logger = logging.getLogger(__name__)


class AutoTradingAgentBase(ABC):
    """
    Base class for auto trading agents (supports both crypto and stock).
    
    This class contains common logic shared by both crypto and stock trading agents.
    Subclasses should implement market-specific methods.
    """

    def __init__(
        self,
        config: BaseTradingConfig,
        signature: Optional[str] = None,
        log_path: Optional[str] = None,
    ):
        """
        Initialize base auto trading agent.

        Args:
            config: Base trading configuration
            signature: Agent signature/identifier (for backtesting)
            log_path: Log path for data persistence (for backtesting)
        """
        self.config = config
        self.active = True
        self.check_count = 0
        self.signature = signature or f"auto_trading_{config.market_type}"
        self.log_path = log_path or "./data/agent_data"
        self.market_type = config.market_type
        self.current_date = None  # For backtesting: current date being processed

        # Initialize exchange adapter
        self.exchange: Optional[ExchangeBase] = None

        # Initialize executor (will be set in run())
        self.executor: Optional[TradingExecutor] = None

        # Initialize position persistence (for backtesting)
        self.position_persistence = PositionPersistence(self.log_path, self.signature)
        
        # Setup log directory for JSON outputs
        self.log_dir = Path(self.log_path) / self.signature / "log"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Session data collector (for JSON output)
        self.session_data: Optional[Dict[str, Any]] = None

        # Initialize AI signal generator if enabled
        self.ai_signal_generator = self._initialize_ai_signal_generator(config)

        # Set market data provider (paper/backtesting only) with config values
        try:
            TechnicalAnalyzer.set_provider(
                MarketDataProvider(
                    min_bars_daily=config.min_bars_daily,
                    min_bars_hourly=config.min_bars_hourly
                )
            )
        except Exception as e:
            logger.warning(f"Failed to set market data provider: {e}")

        logger.info(f"Auto Trading Agent ({self.market_type}) initialized successfully")

    @abstractmethod
    def _get_symbols(self) -> List[str]:
        """
        Get list of trading symbols (implemented by subclasses).

        Returns:
            List of trading symbols
        """
        raise NotImplementedError

    @abstractmethod
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for exchange (implemented by subclasses).

        Args:
            symbol: Original symbol

        Returns:
            Normalized symbol
        """
        raise NotImplementedError

    def _initialize_ai_signal_generator(
        self, config: BaseTradingConfig
    ) -> Optional[AISignalGenerator]:
        """
        Initialize AI signal generator if configured.

        Args:
            config: BaseTradingConfig with use_ai_signals, agent_model settings

        Returns:
            AISignalGenerator instance or None if AI signals are disabled
        """
        if not config.use_ai_signals:
            return None

        if not _MODEL_AVAILABLE:
            logger.warning("LLM provider unavailable; disabling AI signals for this run.")
            return None

        try:
            # Check for environment variable override
            model_id_override = os.getenv(ENV_SIGNAL_MODEL_ID)
            model_id = model_id_override or config.agent_model

            if not model_id:
                logger.warning("No model ID provided for AI signal generator")
                return None

            # Create model directly using langchain-openai ChatOpenAI
            llm_client = Model(id=model_id)
            
            # If using langchain fallback, get the actual client
            if hasattr(llm_client, '_client'):
                llm_client = llm_client._client

            logger.info(f"Initialized AI signal generator: model_id={model_id}")
            return AISignalGenerator(llm_client)

        except Exception as e:
            logger.error(f"Failed to initialize AI signal generator: {e}")
            logger.info(
                "Hint: Make sure provider API keys are configured in environment variables. "
                "AI signals will be disabled for this trading instance."
            )
            return None

    async def _build_exchange(self, config: BaseTradingConfig) -> ExchangeBase:
        """Build exchange adapter based on configuration."""
        exchange_name = (config.exchange or ExchangeType.PAPER.value).lower()

        if exchange_name == ExchangeType.PAPER.value:
            adapter = PaperTrading(
                initial_balance=config.initial_capital, market_type=self.market_type
            )
            await adapter.connect()
            return adapter

        if exchange_name == ExchangeType.OKX.value:
            raise ValueError(
                "OKX exchange support has been removed in this build. "
                "Please set 'exchange' to 'paper' for historical backtesting."
            )

        raise ValueError(f"Unsupported exchange '{exchange_name}'")

    async def _process_trading_cycle(self) -> None:
        """
        Process a single trading cycle.

        This is the core trading logic:
        1. Analyze all assets (technical indicators + AI signals)
        2. Make portfolio-level decisions
        3. Execute approved trades
        4. Record snapshots
        """
        # Initialize session data collector for JSON output
        # Extract date and hour from current_date
        if self.current_date and " " in self.current_date:
            date_part, time_part = self.current_date.split(" ", 1)
            hour_part = time_part.split(":")[0] if ":" in time_part else None
        else:
            date_part = self.current_date
            hour_part = None
        
        self.session_data = {
            "date": date_part,
            "hour": hour_part,
            "datetime": self.current_date,
            "timestamp": datetime.now().isoformat(),
            "phase1_analysis": [],
            "phase2_portfolio_decision": None,
            "phase3_trades_executed": [],
            "summary": {}
        }
        
        try:
            self.check_count += 1
            check_time = datetime.now()

            # Reduced terminal output - only log to file
            logger.debug(
                f"\n{'=' * 50}\n"
                f"🔄 Check #{self.check_count} - {check_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Model: {self.config.agent_model}\n"
                f"Market: {self.market_type.upper()}\n"
                f"{'=' * 50}\n"
            )

            # Phase 1: Collect analysis for all symbols (reduced terminal output)
            logger.debug("📊 Phase 1: Analyzing all assets...\n")

            # Initialize portfolio manager with LLM client for AI-powered decisions
            llm_client = None
            if self.ai_signal_generator and self.ai_signal_generator.llm_client:
                llm_client = self.ai_signal_generator.llm_client

            portfolio_manager = PortfolioDecisionManager(self.config, llm_client)

            # Use abstract method to get symbols
            symbols = self._get_symbols()
            logger.debug(f"📋 Analyzing {len(symbols)} symbols...")
            symbols_with_data = 0
            skipped_symbols = []
            
            # Determine data interval:
            # 1. If explicitly configured, use that
            # 2. Otherwise, auto-select: hourly for backtesting (trading every hour), hourly for live trading
            if self.config.data_interval:
                interval = self.config.data_interval
                use_daily_data = interval == "1d"
            else:
                # Auto-select based on mode
                # For backtesting with hourly trading, always use 60min data
                use_daily_data = False  # Always use hourly data for hourly trading
                interval = "60min"
            
            logger.debug(f"Using data interval: {interval} ({'backtesting' if use_daily_data else 'live trading'} mode)")
            
            # Determine data period based on interval type
            period = self.config.data_period_daily if use_daily_data else self.config.data_period_hourly
            
            for symbol in symbols:
                # Calculate indicators
                indicators = TechnicalAnalyzer.calculate_indicators(symbol, period=period, interval=interval)

                if indicators is None:
                    skipped_symbols.append(symbol)
                    continue
                
                symbols_with_data += 1

                # Generate technical signal
                technical_action, technical_trade_type = (
                    TechnicalAnalyzer.generate_signal(indicators)
                )

                # Generate AI signal if enabled
                ai_action, ai_trade_type, ai_reasoning, ai_confidence = (
                    None,
                    None,
                    None,
                    None,
                )

                if self.ai_signal_generator:
                    ai_signal = await self.ai_signal_generator.get_signal(indicators)
                    if ai_signal:
                        (
                            ai_action,
                            ai_trade_type,
                            ai_reasoning,
                            ai_confidence,
                        ) = ai_signal
                        # Use debug level to reduce noise - summary will be shown at portfolio level
                        logger.debug(
                            f"AI signal for {symbol}: {ai_action.value} {ai_trade_type.value} "
                            f"(confidence: {ai_confidence}%)"
                        )

                # Create asset analysis
                asset_analysis = AssetAnalysis(
                    symbol=symbol,
                    indicators=indicators,
                    technical_action=technical_action,
                    technical_trade_type=technical_trade_type,
                    ai_action=ai_action,
                    ai_trade_type=ai_trade_type,
                    ai_reasoning=ai_reasoning,
                    ai_confidence=ai_confidence,
                )

                # Add to portfolio manager
                portfolio_manager.add_asset_analysis(asset_analysis)

                # Collect data for JSON output
                asset_data = {
                    "symbol": symbol,
                    "price": indicators.close_price,
                    "indicators": {
                        "macd": indicators.macd,
                        "macd_signal": indicators.macd_signal,
                        "macd_histogram": indicators.macd_histogram,
                        "rsi": indicators.rsi,
                        "ema_12": indicators.ema_12,
                        "ema_26": indicators.ema_26,
                        "bb_upper": indicators.bb_upper,
                        "bb_middle": indicators.bb_middle,
                        "bb_lower": indicators.bb_lower,
                    },
                    "technical_signal": {
                        "action": technical_action.value if technical_action else None,
                        "trade_type": technical_trade_type.value if technical_trade_type else None,
                    },
                    "ai_signal": {
                        "action": ai_action.value if ai_action else None,
                        "trade_type": ai_trade_type.value if ai_trade_type else None,
                        "confidence": ai_confidence,
                        "reasoning": ai_reasoning,
                    },
                    "recommended_action": asset_analysis.recommended_action.value,
                    "recommended_trade_type": asset_analysis.recommended_trade_type.value,
                }
                self.session_data["phase1_analysis"].append(asset_data)

                # Log individual asset analysis (use debug to reduce noise)
                logger.debug(
                    f"📊 {symbol}: "
                    f"Price=${indicators.close_price:,.2f}, "
                    f"Signal={asset_analysis.recommended_action.value} "
                    f"{asset_analysis.recommended_trade_type.value}"
                )
                if ai_reasoning:
                    logger.debug(f"   AI Reasoning: {ai_reasoning}")
            
            # Log summary of skipped symbols (reduced terminal output)
            if skipped_symbols:
                if len(skipped_symbols) > 10:
                    logger.debug(f"⚠️  Skipped {len(skipped_symbols)} symbols due to insufficient data (showing first 10: {', '.join(skipped_symbols[:10])}...)")
                else:
                    logger.debug(f"⚠️  Skipped {len(skipped_symbols)} symbols due to insufficient data: {', '.join(skipped_symbols)}")
            
            logger.debug(f"✅ Successfully analyzed {symbols_with_data} out of {len(symbols)} symbols")
            
            if symbols_with_data == 0:
                logger.warning("⚠️  No symbols with sufficient data - skipping portfolio decision")
                # Update session data before returning
                self.session_data["summary"] = {
                    "total_symbols_analyzed": len(symbols),
                    "symbols_with_data": 0,
                    "skipped_symbols_count": len(skipped_symbols),
                    "error": "No symbols with sufficient data",
                }
                return

            # Phase 2: Make portfolio-level decision (reduced terminal output)
            logger.debug(
                "\n" + "=" * 50 + "\n"
                "🎯 Phase 2: Portfolio Decision Making...\n" + "=" * 50 + "\n"
            )

            # Get portfolio summary (only log to file, not terminal)
            portfolio_summary = portfolio_manager.get_portfolio_summary()
            logger.debug(portfolio_summary + "\n")

            # Make coordinated decision (async call for AI analysis)
            portfolio_decision = await portfolio_manager.make_portfolio_decision(
                current_positions=self.executor.positions,
                available_cash=self.executor.get_current_capital(),
                total_portfolio_value=self.executor.get_portfolio_value(),
            )

            # Log decision reasoning (only to file, not terminal)
            logger.debug(
                f"💰 Portfolio Decision Reasoning:\n{portfolio_decision.reasoning}\n"
            )
            # Only show trade count and trades in terminal with datetime
            datetime_str = self.current_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if portfolio_decision.trades_to_execute:
                trades_summary = ", ".join([f"{s} {a.value} {t.value}" for s, a, t in portfolio_decision.trades_to_execute])
                print(f"[{datetime_str}] 📊 Portfolio Decision: {len(portfolio_decision.trades_to_execute)} trade(s) - {trades_summary}")
            else:
                print(f"[{datetime_str}] 📊 Portfolio Decision: No trades - holding current positions")
            
            # Collect portfolio decision data for JSON output
            self.session_data["phase2_portfolio_decision"] = {
                "reasoning": portfolio_decision.reasoning,
                "risk_level": portfolio_decision.risk_level,
                "trades_to_execute": [
                    {
                        "symbol": symbol,
                        "action": action.value,
                        "trade_type": trade_type.value,
                    }
                    for symbol, action, trade_type in portfolio_decision.trades_to_execute
                ],
                "trades_count": len(portfolio_decision.trades_to_execute),
            }

            # Phase 3: Execute approved trades (reduced terminal output)
            if portfolio_decision.trades_to_execute:
                logger.debug(
                    "\n" + "=" * 50 + "\n"
                    f"⚡ Phase 3: Executing {len(portfolio_decision.trades_to_execute)} trade(s)...\n"
                    + "=" * 50 + "\n"
                )

                for (
                    symbol,
                    action,
                    trade_type,
                ) in portfolio_decision.trades_to_execute:
                    # Get indicators for this symbol
                    asset_analysis = portfolio_manager.asset_analyses.get(symbol)
                    if not asset_analysis:
                        continue

                    # Execute trade
                    trade_details = await self.executor.execute_trade(
                        symbol, action, trade_type, asset_analysis.indicators
                    )

                    if trade_details:
                        # Show trade execution in terminal (brief) with datetime
                        datetime_str = self.current_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{datetime_str}] ✅ Trade executed: {action.value} {trade_type.value} {symbol} @ ${trade_details.get('entry_price', 0):,.2f}")
                        # Detailed info only to file
                        logger.debug(
                            f"✅ Trade executed: {action.value} {trade_type.value} {symbol}\n"
                            f"   Price: ${trade_details.get('entry_price', 0):,.2f}, "
                            f"Quantity: {trade_details.get('quantity', 0):.4f}, "
                            f"Notional: ${trade_details.get('notional', 0):,.2f}"
                        )
                        
                        # Collect trade execution data for JSON output
                        if self.session_data:
                            self.session_data["phase3_trades_executed"].append({
                                "symbol": symbol,
                                "action": action.value,
                                "trade_type": trade_type.value,
                                "entry_price": trade_details.get('entry_price'),
                                "quantity": trade_details.get('quantity'),
                                "notional": trade_details.get('notional'),
                                "status": "success",
                            })
                    else:
                        logger.warning(
                            f"❌ Trade failed: {action.value} {trade_type.value} on {symbol}"
                        )
                        
                        # Collect failed trade data for JSON output
                        if self.session_data:
                            self.session_data["phase3_trades_executed"].append({
                                "symbol": symbol,
                                "action": action.value,
                                "trade_type": trade_type.value,
                                "status": "failed",
                            })

            # Collect summary data for JSON output
            portfolio_value = self.executor.get_portfolio_value()
            total_pnl = portfolio_value - self.config.initial_capital
            pnl_pct = (total_pnl / self.config.initial_capital) * 100
            
            self.session_data["summary"] = {
                "total_symbols_analyzed": len(symbols),
                "symbols_with_data": symbols_with_data,
                "skipped_symbols_count": len(skipped_symbols),
                "current_cash": self.executor.get_current_capital(),
                "portfolio_value": portfolio_value,
                "total_pnl": total_pnl,
                "pnl_percentage": pnl_pct,
                "positions_count": len(self.executor.positions),
                "positions": {
                    symbol: {
                        "quantity": pos.quantity,
                        "entry_price": pos.entry_price,
                        "trade_type": pos.trade_type.value,
                    }
                    for symbol, pos in self.executor.positions.items()
                },
            }
            
            # Take snapshots
            timestamp = datetime.now()
            self.executor.snapshot_positions(timestamp)
            self.executor.snapshot_portfolio(timestamp)

            # Portfolio update only to file, not terminal
            portfolio_msg = (
                f"\n💰 Portfolio Update\n"
                f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Total Value: ${portfolio_value:,.2f}\n"
                f"P&L: ${total_pnl:,.2f} ({pnl_pct:+.2f}%)\n"
                f"Open Positions: {len(self.executor.positions)}\n"
                f"Available Capital: ${self.executor.current_capital:,.2f}\n"
            )
            logger.debug(portfolio_msg)

            if self.executor.positions:
                portfolio_msg += "\nOpen Positions:\n"
                provider = TechnicalAnalyzer._market_data_provider
                for symbol, pos in self.executor.positions.items():
                    try:
                        current_price = (
                            provider.get_current_price(symbol) or pos.entry_price
                        )
                        if pos.trade_type.value == "long":
                            current_pnl = (current_price - pos.entry_price) * abs(
                                pos.quantity
                            )
                        else:
                            current_pnl = (pos.entry_price - current_price) * abs(
                                pos.quantity
                            )
                        pnl_emoji = "🟢" if current_pnl >= 0 else "🔴"
                        portfolio_msg += (
                            f"  {symbol}: {pos.trade_type.value.upper()} @ "
                            f"${pos.entry_price:,.2f} → ${current_price:,.2f} "
                            f"{pnl_emoji} P&L: ${current_pnl:,.2f}\n"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to calculate P&L for {symbol}: {e}")
                        portfolio_msg += (
                            f"  {symbol}: {pos.trade_type.value.upper()} @ "
                            f"${pos.entry_price:,.2f}\n"
                        )

            logger.debug(portfolio_msg)

        except Exception as e:
            logger.error(f"Error processing trading cycle: {e}", exc_info=True)

    async def run(self) -> None:
        """
        Run the auto trading agent continuously.

        This is the main entry point. It will:
        1. Initialize exchange and executor
        2. Run trading cycles at configured intervals
        3. Continue until stopped (set self.active = False)
        """
        try:
            # Initialize exchange
            logger.info("🔌 Connecting to exchange...")
            self.exchange = await self._build_exchange(self.config)
            logger.info(f"✅ Connected to {self.config.exchange} exchange")

            # Initialize executor
            self.executor = TradingExecutor(self.config, exchange=self.exchange)
            logger.info("✅ Trading executor initialized")

            # Log initial configuration
            symbols = self._get_symbols()
            logger.info(
                f"\n{'=' * 50}\n"
                f"🚀 Starting Auto Trading Agent ({self.market_type.upper()})\n"
                f"{'=' * 50}\n"
                f"Configuration:\n"
                f"  Symbols: {', '.join(symbols)}\n"
                f"  Initial Capital: ${self.config.initial_capital:,.2f}\n"
                f"  Check Interval: {self.config.check_interval}s\n"
                f"  Risk Per Trade: {self.config.risk_per_trade * 100:.1f}%\n"
                f"  Max Positions: {self.config.max_positions}\n"
                f"  Exchange: {self.config.exchange} ({self.config.exchange_network})\n"
                f"  Live Trading: {'✅' if self.config.allow_live_trading else '❌'}\n"
                f"  AI Signals: {'✅' if self.config.use_ai_signals else '❌'}\n"
                f"  Model: {self.config.agent_model}\n"
                f"{'=' * 50}\n"
            )

            # Record initial portfolio snapshot
            initial_value = self.executor.get_portfolio_value()
            self.executor.snapshot_portfolio(datetime.now())
            logger.info(f"💰 Initial Portfolio Value: ${initial_value:,.2f}\n")

            # Main trading loop
            while self.active:
                await self._process_trading_cycle()

                # Wait for next check interval
                logger.info(
                    f"⏳ Waiting {self.config.check_interval}s until next check...\n"
                )
                await asyncio.sleep(self.config.check_interval)

        except KeyboardInterrupt:
            logger.info("\n⚠️  Received interrupt signal, stopping agent...")
            self.active = False
        except Exception as e:
            logger.error(f"Critical error in run(): {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            if self.exchange:
                try:
                    await self.exchange.disconnect()
                    logger.info("🔌 Disconnected from exchange")
                except Exception as e:
                    logger.warning(f"Error disconnecting from exchange: {e}")

            final_value = (
                self.executor.get_portfolio_value() if self.executor else 0
            )
            logger.info(f"\n💰 Final Portfolio Value: ${final_value:,.2f}")
            logger.info("👋 Auto Trading Agent stopped")

    def stop(self) -> None:
        """Stop the trading agent."""
        logger.info("🛑 Stopping trading agent...")
        self.active = False

    @abstractmethod
    def get_trading_dates(self, init_date: str, end_date: str) -> List[str]:
        """
        Get trading date list (implemented by subclasses).

        Args:
            init_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of trading dates
        """
        raise NotImplementedError

    def _save_session_json(self, date: str, hour: Optional[str] = None) -> None:
        """
        Save session data as JSON file to data/{signature}/log/{date}/output.json
        If hour is provided, saves to data/{signature}/log/{date}/{hour}.json
        
        Args:
            date: Date string (YYYY-MM-DD)
            hour: Optional hour string (HH:MM:SS or HH:00:00)
        """
        if not self.session_data:
            return
        
        # Create date directory
        date_dir = self.log_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        if hour:
            # Extract hour part (e.g., "10:00:00" -> "10")
            hour_part = hour.split(':')[0]
            json_filename = f"{hour_part}.json"
        else:
            json_filename = "output.json"
        
        # Save to JSON file
        json_file = date_dir / json_filename
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Only log file save to debug, not terminal
        logger.debug(f"📝 Session output saved to: {json_file}")

    async def run_trading_session(self, today_date: str, hour: Optional[str] = None) -> None:
        """
        Run a single trading session for a specific date and hour (for backtesting).

        Args:
            today_date: Date string (YYYY-MM-DD)
            hour: Optional hour string (HH:00:00), e.g., "10:00:00"
        """
        if hour:
            # Set current date and time for historical data
            current_datetime = f"{today_date} {hour}"
            self.current_date = current_datetime  # Store for use in _process_trading_cycle
            TechnicalAnalyzer.set_current_date(current_datetime)
            if self.exchange and hasattr(self.exchange, "set_current_date"):
                self.exchange.set_current_date(current_datetime)
            # Reduced terminal output - detailed info goes to file
            logger.debug(f"🔄 Processing trading session for {current_datetime}")
        else:
            # Set current date for historical data
            self.current_date = today_date  # Store for use in _process_trading_cycle
            TechnicalAnalyzer.set_current_date(today_date)
            if self.exchange and hasattr(self.exchange, "set_current_date"):
                self.exchange.set_current_date(today_date)
            logger.debug(f"🔄 Processing trading session for {today_date}")

        # Process trading cycle
        await self._process_trading_cycle()

        # Save session data as JSON
        self._save_session_json(today_date, hour)

        # Save position snapshot (save every hour for hourly trading)
        if self.executor:
            positions_dict = {}
            for symbol, position in self.executor.positions.items():
                positions_dict[symbol] = position.quantity

            cash = self.executor.get_current_capital()

            # Save to file with datetime if hour is provided (for hourly trading)
            if hour:
                # For hourly trading, save with datetime to track each hour
                datetime_str = f"{today_date} {hour}"
                self.position_persistence.save_position(
                    date=datetime_str,
                    positions=positions_dict,
                    cash=cash,
                )
            else:
                # For daily trading, save with date only
                self.position_persistence.save_position(
                    date=today_date,
                    positions=positions_dict,
                    cash=cash,
                )

    async def run_date_range(self, init_date: str, end_date: str) -> None:
        """
        Run historical backtesting for a date range.

        Args:
            init_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        """
        logger.info(f"📅 Running date range: {init_date} to {end_date}")

        # Initialize exchange
        logger.info("🔌 Connecting to exchange...")
        self.exchange = await self._build_exchange(self.config)
        logger.info(f"✅ Connected to {self.config.exchange} exchange")

        # Initialize executor
        self.executor = TradingExecutor(self.config, exchange=self.exchange)
        logger.info("✅ Trading executor initialized")

        # Load latest position if exists
        latest_position = self.position_persistence.load_latest_position()
        if latest_position:
            logger.info(f"📂 Loading position from {latest_position.get('date')}")
            positions = latest_position.get("positions", {})
            cash = positions.get("CASH", self.config.initial_capital)

            logger.info(f"💰 Restored cash: ${cash:,.2f}")
        else:
            # Initialize position file
            symbols = self._get_symbols()
            self.position_persistence.initialize_position(
                init_date=init_date,
                initial_cash=self.config.initial_capital,
                symbols=symbols,
            )

        # Get trading dates
        trading_dates = self.get_trading_dates(init_date, end_date)

        if not trading_dates:
            logger.info("ℹ️  No trading days to process")
            return

        logger.info(f"📊 Trading days to process: {len(trading_dates)} days")

        # Trading hours: 10:00-15:00 (6 hours per day)
        trading_hours = ["10:00:00", "11:00:00", "12:00:00", "13:00:00", "14:00:00", "15:00:00"]
        
        # Process each trading day and each hour
        total_sessions = len(trading_dates) * len(trading_hours)
        session_count = 0
        
        for date in trading_dates:
            for hour in trading_hours:
                try:
                    session_count += 1
                    # Show progress in terminal with clear datetime
                    datetime_str = f"{date} {hour}"
                    print(f"[{datetime_str}] 🔄 [{session_count}/{total_sessions}] Processing...", flush=True)
                    await self.run_trading_session(date, hour)
                    print(f"[{datetime_str}] ✅ Done")
                    # Detailed log only to file
                    logger.debug(f"🔄 Processing {self.signature} - Date: {date} Hour: {hour} ({session_count}/{total_sessions})")
                    logger.debug(f"✅ Completed {date} {hour}")
                except Exception as e:
                    print(f"❌ Error")
                    logger.error(f"❌ Error processing {date} {hour}: {e}")
                    raise

        print(f"\n✅ {self.signature} backtesting completed")

        # Display final summary (brief in terminal, detailed in file)
        if self.executor:
            final_value = self.executor.get_portfolio_value()
            total_pnl = final_value - self.config.initial_capital
            pnl_pct = (total_pnl / self.config.initial_capital) * 100

            # Brief summary in terminal
            print(f"📊 Final Summary: ${final_value:,.2f} (P&L: ${total_pnl:,.2f}, {pnl_pct:+.2f}%)")
            
            # Detailed summary to file
            logger.debug(
                f"\n{'=' * 50}\n"
                f"📊 Final Backtest Summary\n"
                f"{'=' * 50}\n"
                f"Initial Capital: ${self.config.initial_capital:,.2f}\n"
                f"Final Value: ${final_value:,.2f}\n"
                f"Total P&L: ${total_pnl:,.2f} ({pnl_pct:+.2f}%)\n"
                f"{'=' * 50}\n"
            )

