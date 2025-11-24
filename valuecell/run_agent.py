"""Main entry point for standalone auto trading agent"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Load environment variables from .env file in project root
# This must be done before importing other modules that use environment variables
from dotenv import load_dotenv

# Look for .env in parent directory (project root)
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from: {env_file}")
else:
    print(f"⚠️  .env file not found at: {env_file}")
    print("   Please copy .env.example to .env and configure your API keys")

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

    # Parse news settings
    enable_news = os.getenv("ENABLE_NEWS", "false").lower() in {"true", "1", "yes"}
    enable_alpha_vantage_news = os.getenv("ENABLE_ALPHA_VANTAGE_NEWS", "true").lower() in {"true", "1", "yes"}
    enable_x_news = os.getenv("ENABLE_X_NEWS", "false").lower() in {"true", "1", "yes"}
    enable_reddit_news = os.getenv("ENABLE_REDDIT_NEWS", "false").lower() in {"true", "1", "yes"}

    # Parse market type
    market_type = os.getenv("MARKET_TYPE", "crypto")

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
        market_type=market_type,
        enable_news=enable_news,
        enable_alpha_vantage_news=enable_alpha_vantage_news,
        enable_x_news=enable_x_news,
        enable_reddit_news=enable_reddit_news,
    )


async def main():
    """Main entry point."""
    logger.info("🚀 Starting Standalone Auto Trading Agent")

    # Load configuration
    try:
        config = load_config_from_env()
        logger.info("✅ Configuration loaded from environment variables")
        logger.info(f"News collection: {'✅ Enabled' if config.enable_news else '❌ Disabled'}")
        if config.enable_news:
            logger.info(f"  Alpha Vantage: {'✅' if config.enable_alpha_vantage_news else '❌'}")
            logger.info(f"  X/Twitter: {'✅' if config.enable_x_news else '❌'}")
            logger.info(f"  Reddit: {'✅' if config.enable_reddit_news else '❌'}")
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

