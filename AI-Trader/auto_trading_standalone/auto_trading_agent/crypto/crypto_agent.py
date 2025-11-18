"""Cryptocurrency trading agent implementation"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add project root to path for importing tools
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ..base.base_agent import AutoTradingAgentBase
from .crypto_config import CryptoTradingConfig

logger = logging.getLogger(__name__)


class AutoTradingAgentCrypto(AutoTradingAgentBase):
    """
    Cryptocurrency trading agent.

    Handles crypto-specific logic:
    - Symbol normalization (BTC-USD -> BTCUSDT)
    - 24/7 trading days
    """

    def __init__(
        self,
        config: CryptoTradingConfig,
        signature: Optional[str] = None,
        log_path: Optional[str] = None,
    ):
        """
        Initialize cryptocurrency trading agent.

        Args:
            config: Cryptocurrency trading configuration
            signature: Agent signature/identifier
            log_path: Log path for data persistence
        """
        super().__init__(config, signature, log_path)
        self.crypto_config = config

    def _get_symbols(self) -> List[str]:
        """Get list of cryptocurrency symbols."""
        return self.crypto_config.crypto_symbols

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize crypto symbol for exchange format.

        Args:
            symbol: Original symbol (e.g., "BTC-USD")

        Returns:
            Normalized symbol (e.g., "BTCUSDT")
        """
        return symbol.replace("-USD", "USDT").replace("-USDT", "USDT")

    def get_trading_dates(self, init_date: str, end_date: str) -> List[str]:
        """
        Get trading date list for crypto (24/7 trading).

        Args:
            init_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of trading dates
        """
        try:
            from tools.price_tools import is_trading_day
        except ImportError:
            # Fallback: assume all dates are trading days for crypto
            logger.warning(
                "Could not import is_trading_day, assuming all dates are trading days"
            )
            dates = []
            current_date = datetime.strptime(init_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

            # Check latest date from position file
            latest_date = self.position_persistence.get_latest_date()
            if latest_date:
                # Parse latest date
                if " " in latest_date:
                    latest_date_obj = datetime.strptime(
                        latest_date, "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d")

                # Start from day after latest date
                current_date = latest_date_obj + timedelta(days=1)
                current_date = current_date.replace(hour=0, minute=0, second=0)

            while current_date <= end_date_obj:
                dates.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)

            return dates

        # Use is_trading_day for crypto market
        dates = []
        current_date = datetime.strptime(init_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

        # Check latest date from position file
        latest_date = self.position_persistence.get_latest_date()
        if latest_date:
            # Parse latest date
            if " " in latest_date:
                latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d %H:%M:%S")
            else:
                latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d")

            # Start from day after latest date
            current_date = latest_date_obj + timedelta(days=1)
            current_date = current_date.replace(hour=0, minute=0, second=0)

        if current_date > end_date_obj:
            return []

        while current_date <= end_date_obj:
            date_str = current_date.strftime("%Y-%m-%d")
            # For crypto, all dates are trading days (24/7)
            if is_trading_day(date_str, market="crypto"):
                dates.append(date_str)
            current_date += timedelta(days=1)

        return dates


