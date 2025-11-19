"""Stock trading configuration"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from ..base.base_config import BaseTradingConfig
from ..constants import MAX_SYMBOLS


class StockTradingConfig(BaseTradingConfig):
    """Configuration for stock trading agent"""

    stock_symbols: Optional[List[str]] = Field(
        default=None,
        description="List of stock symbols to trade. If None, uses NASDAQ 100 for US market or SSE 50 for CN market",
    )
    market: str = Field(
        default="us",
        description="Stock market: 'us' for US stocks, 'cn' for A-shares",
    )

    @field_validator("stock_symbols")
    @classmethod
    def validate_symbols(cls, v):
        if v is None:
            return None  # Will use default symbols based on market
        if len(v) == 0:
            return None  # Empty list means use default
        if len(v) > MAX_SYMBOLS:
            raise ValueError(f"Maximum {MAX_SYMBOLS} symbols allowed")
        # Normalize symbols to uppercase
        return [s.upper() for s in v]

    @field_validator("market")
    @classmethod
    def validate_market(cls, v):
        if v not in {"us", "cn"}:
            raise ValueError("Market must be 'us' or 'cn'")
        return v.lower()

    def __init__(self, **data):
        # Ensure market_type is set to stock
        if "market_type" not in data:
            data["market_type"] = "stock"
        super().__init__(**data)


