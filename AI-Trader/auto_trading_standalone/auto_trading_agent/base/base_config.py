"""Base configuration for auto trading agent"""

from typing import Optional

from pydantic import BaseModel, Field

from ..constants import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_MAX_POSITIONS,
    DEFAULT_MIN_BARS_DAILY,
    DEFAULT_MIN_BARS_HOURLY,
    DEFAULT_RISK_PER_TRADE,
)


class BaseTradingConfig(BaseModel):
    """Base configuration for auto trading agent (supports both crypto and stock)"""

    initial_capital: float = Field(
        default=DEFAULT_INITIAL_CAPITAL,
        description="Initial capital for trading",
        gt=0,
    )
    check_interval: int = Field(
        default=60,
        description="Check interval in seconds",
        gt=0,
    )
    risk_per_trade: float = Field(
        default=DEFAULT_RISK_PER_TRADE,
        description="Risk per trade as percentage of capital",
        gt=0,
        lt=1,
    )
    max_positions: int = Field(
        default=DEFAULT_MAX_POSITIONS,
        description="Maximum number of concurrent positions",
        gt=0,
    )
    agent_model: str = Field(
        default=DEFAULT_AGENT_MODEL,
        description="Model ID for AI-enhanced trading decisions",
    )
    agent_provider: Optional[str] = Field(
        default=None,
        description="Provider name (null = auto-detect from config system)",
    )
    use_ai_signals: bool = Field(
        default=False,
        description="Whether to use AI model for enhanced signal generation",
    )
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key for AI model access",
    )
    exchange: str = Field(
        default="paper",
        description="Exchange adapter to use (paper only)",
    )
    exchange_network: str = Field(
        default="paper",
        description="Exchange network identifier (paper only)",
    )
    allow_live_trading: bool = Field(
        default=False,
        description="Kept for compatibility; no live trading in this build",
    )
    market_type: str = Field(
        default="crypto",
        description="Market type: 'crypto' or 'stock'",
    )
    min_bars_daily: int = Field(
        default=DEFAULT_MIN_BARS_DAILY,
        description="Minimum number of bars required for daily data analysis",
        gt=0,
    )
    min_bars_hourly: int = Field(
        default=DEFAULT_MIN_BARS_HOURLY,
        description="Minimum number of bars required for hourly data analysis",
        gt=0,
    )
    data_interval: Optional[str] = Field(
        default=None,
        description="Data interval to use: '1d' for daily, '60min' for hourly. If None, auto-selects based on mode (daily for backtesting, hourly for live trading)",
    )
    data_period_daily: str = Field(
        default="30d",
        description="Data period for daily data analysis (e.g., '30d' means 30 days of historical data). Format: 'Nd' for N days",
    )
    data_period_hourly: str = Field(
        default="5d",
        description="Data period for hourly data analysis (e.g., '5d' means 5 days of historical data). Format: 'Nd' for N days",
    )


