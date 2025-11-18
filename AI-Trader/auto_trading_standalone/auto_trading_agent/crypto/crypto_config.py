"""Cryptocurrency trading configuration"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from ..base.base_config import BaseTradingConfig
from ..constants import MAX_SYMBOLS


class CryptoTradingConfig(BaseTradingConfig):
    """Configuration for cryptocurrency trading agent"""

    crypto_symbols: List[str] = Field(
        ...,
        description="List of crypto symbols to trade (max 10)",
        max_length=MAX_SYMBOLS,
    )

    @field_validator("crypto_symbols")
    @classmethod
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one crypto symbol is required")
        if len(v) > MAX_SYMBOLS:
            raise ValueError(f"Maximum {MAX_SYMBOLS} symbols allowed")
        # Normalize symbols to uppercase
        return [s.upper() for s in v]

    def __init__(self, **data):
        # Ensure market_type is set to crypto
        if "market_type" not in data:
            data["market_type"] = "crypto"
        super().__init__(**data)


