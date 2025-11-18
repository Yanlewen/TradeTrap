"""Main entry point for standalone auto trading agent"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auto_trading_agent.models import AutoTradingConfig
from auto_trading_agent.agent import AutoTradingAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config_from_env() -> AutoTradingConfig:
    """Load configuration from environment variables."""
    # Parse crypto symbols (comma-separated)
    symbols_str = os.getenv("CRYPTO_SYMBOLS", "BTC-USD,ETH-USD")
    crypto_symbols = [s.strip() for s in symbols_str.split(",")]

    # Parse initial capital
    initial_capital = float(os.getenv("INITIAL_CAPITAL", "100000"))

    # Parse check interval (in seconds)
    check_interval = int(os.getenv("CHECK_INTERVAL", "60"))

    # Parse risk per trade (as percentage, e.g., "5" means 5%)
    risk_per_trade_pct = float(os.getenv("RISK_PER_TRADE", "5"))
    risk_per_trade = risk_per_trade_pct / 100.0

    # Parse max positions
    max_positions = int(os.getenv("MAX_POSITIONS", "5"))

    # Parse AI signals
    use_ai_signals = os.getenv("USE_AI_SIGNALS", "true").lower() in {"true", "1", "yes"}

    # Parse agent model
    agent_model = os.getenv("AGENT_MODEL", "gpt-4o-mini")

    return AutoTradingConfig(
        initial_capital=initial_capital,
        crypto_symbols=crypto_symbols,
        check_interval=check_interval,
        risk_per_trade=risk_per_trade,
        max_positions=max_positions,
        use_ai_signals=use_ai_signals,
        agent_model=agent_model,
        exchange="paper",
        exchange_network="paper",
    )


async def main():
    """Main entry point."""
    logger.info("🚀 Starting Standalone Auto Trading Agent")

    # Load configuration
    try:
        config = load_config_from_env()
        logger.info("✅ Configuration loaded from environment variables")
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        return

    # Create and run agent
    agent = AutoTradingAgent(config)
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")

