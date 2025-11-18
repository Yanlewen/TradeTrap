"""Stock trading agent implementation"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add project root to path for importing tools
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ..base.base_agent import AutoTradingAgentBase
from .stock_config import StockTradingConfig

logger = logging.getLogger(__name__)


class AutoTradingAgentStock(AutoTradingAgentBase):
    """
    Stock trading agent.

    Handles stock-specific logic:
    - Symbol normalization (AAPL -> AAPL, no conversion needed)
    - Trading days (excludes weekends and holidays)
    - Stock market specific rules
    """

    def __init__(
        self,
        config: StockTradingConfig,
        signature: Optional[str] = None,
        log_path: Optional[str] = None,
    ):
        """
        Initialize stock trading agent.

        Args:
            config: Stock trading configuration
            signature: Agent signature/identifier
            log_path: Log path for data persistence
        """
        super().__init__(config, signature, log_path)
        self.stock_config = config

    def _get_symbols(self) -> List[str]:
        """
        Get list of stock symbols.
        If stock_symbols is None, automatically uses NASDAQ 100 for US market or SSE 50 for CN market.
        """
        if self.stock_config.stock_symbols is not None:
            return self.stock_config.stock_symbols

        # Auto-select stock symbols based on market (same as BaseAgent)
        if self.stock_config.market == "cn":
            # Import A-shares symbols when needed
            try:
                from tools.price_tools import all_sse_50_symbols
                logger.info(f"Using default SSE 50 symbols ({len(all_sse_50_symbols)} stocks)")
                return all_sse_50_symbols
            except ImportError:
                logger.error("Could not import all_sse_50_symbols")
                raise
        else:
            # Default to US NASDAQ 100
            try:
                from tools.price_tools import all_nasdaq_100_symbols
                logger.info(f"Using default NASDAQ 100 symbols ({len(all_nasdaq_100_symbols)} stocks)")
                return all_nasdaq_100_symbols
            except ImportError:
                logger.error("Could not import all_nasdaq_100_symbols")
                raise

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol (usually just uppercase).

        Args:
            symbol: Original symbol (e.g., "AAPL")

        Returns:
            Normalized symbol (e.g., "AAPL")
        """
        return symbol.upper()

    def get_trading_dates(self, init_date: str, end_date: str) -> List[str]:
        """
        Get trading date list for stocks (excludes weekends and holidays).

        Args:
            init_date: Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end_date: End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)

        Returns:
            List of trading dates
        """
        try:
            from tools.price_tools import is_trading_day
        except ImportError:
            logger.error("Could not import is_trading_day, required for stock trading")
            raise

        # Parse dates, supporting both "YYYY-MM-DD" and "YYYY-MM-DD HH:MM:SS" formats
        def parse_date(date_str: str) -> datetime:
            """Parse date string, supporting multiple formats."""
            date_str = date_str.strip()
            if " " in date_str:
                # Has time component, extract date part only
                date_part = date_str.split(" ")[0]
                return datetime.strptime(date_part, "%Y-%m-%d")
            else:
                return datetime.strptime(date_str, "%Y-%m-%d")

        dates = []
        init_date_obj = parse_date(init_date)
        end_date_obj = parse_date(end_date)
        current_date = init_date_obj

        # Check latest date from position file
        latest_date = self.position_persistence.get_latest_date()
        if latest_date:
            # Parse latest date
            if " " in latest_date:
                latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d %H:%M:%S")
            else:
                latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d")

            # Only resume from latest date if latest_date is AFTER init_date
            # If latest_date is on or before init_date, start from init_date
            # Compare dates (ignore time component)
            latest_date_only = latest_date_obj.replace(hour=0, minute=0, second=0)
            init_date_only = init_date_obj.replace(hour=0, minute=0, second=0)
            
            logger.debug(f"Date comparison: latest_date_only={latest_date_only}, init_date_only={init_date_only}")
            
            if latest_date_only > init_date_only:
                # Resume from latest date (for continuing previous run)
                resume_date = latest_date_obj + timedelta(days=1)
                resume_date = resume_date.replace(hour=0, minute=0, second=0)
                current_date = resume_date
                logger.info(f"📂 Resuming from {latest_date} - starting from {current_date.strftime('%Y-%m-%d')}")
            elif latest_date_only == init_date_only:
                # Same date: start from init_date (re-run from beginning of configured date)
                current_date = init_date_obj
                logger.info(f"📂 Position file has same date as init_date ({latest_date}), starting from configured init_date: {current_date.strftime('%Y-%m-%d')}")
            else:
                # latest_date < init_date: start from init_date
                current_date = init_date_obj
                logger.info(f"📂 Position file date ({latest_date}) is before init_date, starting from configured init_date: {current_date.strftime('%Y-%m-%d')}")

        if current_date > end_date_obj:
            return []

        # Use market type from config (us or cn)
        market = self.stock_config.market

        while current_date <= end_date_obj:
            date_str = current_date.strftime("%Y-%m-%d")
            # Check if this is a trading day (excludes weekends and holidays)
            if is_trading_day(date_str, market=market):
                dates.append(date_str)
            current_date += timedelta(days=1)

        return dates


