"""Unified entry point for auto trading agent - factory pattern"""

import logging
from typing import Optional

from .base.base_agent import AutoTradingAgentBase
from .crypto.crypto_agent import AutoTradingAgentCrypto
from .crypto.crypto_config import CryptoTradingConfig
from .stock.stock_agent import AutoTradingAgentStock
from .stock.stock_config import StockTradingConfig

logger = logging.getLogger(__name__)


class AutoTradingAgent:
    """
    Unified entry point for auto trading agent.
    
    Factory class that creates the appropriate agent implementation
    based on market_type configuration.
    
    Usage:
        # From config dict
        agent = AutoTradingAgent.create(config_dict, signature="test", log_path="./data")
        
        # Or directly with config objects
        from .crypto.crypto_config import CryptoTradingConfig
        config = CryptoTradingConfig(crypto_symbols=["BTC-USD"], ...)
        agent = AutoTradingAgentCrypto(config, signature="test")
    """

    @staticmethod
    def create(
        config_dict: dict,
        signature: Optional[str] = None,
        log_path: Optional[str] = None,
    ) -> AutoTradingAgentBase:
        """
        Factory method: Create appropriate agent based on market_type.

        Args:
            config_dict: Configuration dictionary
            signature: Agent signature/identifier
            log_path: Log path for data persistence

        Returns:
            AutoTradingAgentBase instance (either Crypto or Stock)

        Raises:
            ValueError: If market_type is not supported
        """
        # Get market_type from config, default to crypto for backward compatibility
        market_type = config_dict.get("market_type", "crypto")

        if market_type == "crypto":
            # Create crypto agent
            try:
                config = CryptoTradingConfig(**config_dict)
                return AutoTradingAgentCrypto(config, signature, log_path)
            except Exception:
                logger.exception("Failed to create crypto agent")
            raise

        if market_type == "stock":
            # Create stock agent
            try:
                config = StockTradingConfig(**config_dict)
                return AutoTradingAgentStock(config, signature, log_path)
            except Exception:
                logger.exception("Failed to create stock agent")
                raise

        raise ValueError(f"Unsupported market_type: {market_type}. Must be 'crypto' or 'stock'")

    # Backward compatibility: allow direct instantiation
    def __new__(cls, *args, **kwargs):
        """
        Backward compatibility: redirect to create() method.
        
        This allows old code like:
            agent = AutoTradingAgent(config, signature, log_path)
        to still work, but it's recommended to use create() instead.
        """
        if args and isinstance(args[0], dict):
            # Called as factory: AutoTradingAgent.create(config_dict, ...)
            return cls.create(*args, **kwargs)
        else:
            # Try to determine from config object
            if args:
                config = args[0]
                if hasattr(config, "market_type"):
                    market_type = config.market_type
                elif hasattr(config, "crypto_symbols"):
                    market_type = "crypto"
                elif hasattr(config, "stock_symbols"):
                    market_type = "stock"
                else:
                    # Default to crypto for backward compatibility
                    market_type = "crypto"

                if market_type == "crypto":
                    return AutoTradingAgentCrypto(*args, **kwargs)
                elif market_type == "stock":
                    return AutoTradingAgentStock(*args, **kwargs)

        raise ValueError(
            "Cannot determine market_type. Use AutoTradingAgent.create(config_dict, ...) instead."
        )
