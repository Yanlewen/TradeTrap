import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from typing import Dict, List, Optional, Any
import fcntl
from pathlib import Path
# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
import json

from tools.general_tools import get_config_value, write_config_value
from tools.price_tools import (get_latest_position, get_open_prices,
                               get_yesterday_date,
                               get_yesterday_open_and_close_price,
                               get_yesterday_profit)

mcp = FastMCP("TradeTools")

def _position_lock(signature: str):
    """Context manager for file-based lock to serialize position updates per signature."""
    class _Lock:
        def __init__(self, name: str):
            base_dir = Path(project_root) / "data" / "agent_data" / name
            base_dir.mkdir(parents=True, exist_ok=True)
            self.lock_path = base_dir / ".position.lock"
            # Ensure lock file exists
            self._fh = open(self.lock_path, "a+")
        def __enter__(self):
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            return self
        def __exit__(self, exc_type, exc, tb):
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
    return _Lock(signature)



@mcp.tool()
def buy(symbol: str, amount: int) -> Dict[str, Any]:
    """
    Buy stock function

    This function stages a buy order, letting PositionLedger handle final settlement:
    1. Get current position and operation ID
    2. Get stock opening price for the day
    3. Validate input basics (amount format, lot size)
    4. Build order payload along with the agent-observed position

    Args:
        symbol: Stock symbol, such as "AAPL", "MSFT", etc.
        amount: Buy quantity, must be a positive integer, indicating how many shares to buy
                For Chinese A-shares (symbols ending with .SH or .SZ), must be multiples of 100

    Returns:
        Dict[str, Any]:
          - Success: Returns {"order": {...}, "position_before": {...}}
          - Failure: Returns {"error": error message, ...}

    Raises:
        ValueError: Raised when SIGNATURE environment variable is not set

    Example:
        >>> result = buy("AAPL", 10)
        >>> print(result)  # {"AAPL": 110, "MSFT": 5, "CASH": 5000.0, ...}
        >>> result = buy("600519.SH", 100)  # Chinese A-shares must be multiples of 100
        >>> print(result)  # {"600519.SH": 100, "CASH": 85000.0, ...}
    """
    # Step 1: Get environment variables and basic information
    # Get signature (model name) from environment variable, used to determine data storage path
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")

    # Get current trading date from environment variable
    today_date = get_config_value("TODAY_DATE")

    # Auto-detect market type based on symbol format
    if symbol.endswith((".SH", ".SZ")):
        market = "cn"
    else:
        market = "us"

    # Amount validation for stocks
    try:
        amount = int(amount)  # Convert to int for stocks
    except ValueError:
        return {
            "error": f"Invalid amount format. Amount must be an integer for stock trading. You provided: {amount}",
            "symbol": symbol,
            "date": today_date,
        }

    if amount <= 0:
        return {
            "error": f"Amount must be positive. You tried to buy {amount} shares.",
            "symbol": symbol,
            "amount": amount,
            "date": today_date,
        }

    # 🇨🇳 Chinese A-shares trading rule: Must trade in lots of 100 shares (一手 = 100股)
    if market == "cn" and amount % 100 != 0:
        return {
            "error": f"Chinese A-shares must be traded in multiples of 100 shares (1 lot = 100 shares). You tried to buy {amount} shares.",
            "symbol": symbol,
            "amount": amount,
            "date": today_date,
            "suggestion": f"Please use {(amount // 100) * 100} or {((amount // 100) + 1) * 100} shares instead.",
        }

    # Step 2: Get current latest position and operation ID
    # get_latest_position returns two values: position dictionary and current maximum operation ID
    # This ID is used to ensure each operation has a unique identifier
    # Acquire lock for atomic read-modify-write on positions
    with _position_lock(signature):
        try:
            current_position, current_action_id = get_latest_position(today_date, signature)
        except Exception as e:
            print(e)
            print(today_date, signature)
            return {"error": f"Failed to load latest position: {e}", "symbol": symbol, "date": today_date}
    # Step 3: Get stock opening price for the day
    # Use get_open_prices function to get the opening price of specified stock for the day
    # If stock symbol does not exist or price data is missing, KeyError exception will be raised
    try:
        this_symbol_price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        # Stock symbol does not exist or price data is missing, return error message
        return {
            "error": f"Symbol {symbol} not found! This action will not be allowed.",
            "symbol": symbol,
            "date": today_date,
        }

    # Step 4: Validate buy conditions
    # Calculate cash required for purchase: stock price × buy quantity
    try:
        cash_left = current_position["CASH"] - this_symbol_price * amount
    except Exception as e:
        print(current_position, "CASH", this_symbol_price, amount)

    # Check if cash balance is sufficient for purchase
    if cash_left < 0:
        # Insufficient cash, return error message
        return {
            "error": "Insufficient cash! This action will not be allowed.",
            "required_cash": this_symbol_price * amount,
            "cash_available": current_position.get("CASH", 0),
            "symbol": symbol,
            "date": today_date,
        }
    order_payload = {
                        "id": current_action_id + 1,
        "timestamp": today_date,
        "action": "buy",
        "symbol": symbol,
        "amount": amount,
        "price": this_symbol_price,
        "market": market,
    }

    staged_record = {
        "order": order_payload,
        "position_before": current_position,
    }

    write_config_value("IF_TRADE", True)
    print("IF_TRADE", get_config_value("IF_TRADE"))
    return staged_record


def _get_today_buy_amount(symbol: str, today_date: str, signature: str) -> int:
    """
    Helper function to get the total amount bought today for T+1 restriction check

    Args:
        symbol: Stock symbol
        today_date: Trading date
        signature: Model signature

    Returns:
        Total shares bought today
    """
    log_path = get_config_value("LOG_PATH", "./data/agent_data")
    if log_path.startswith("./data/"):
        log_path = log_path[7:]  # Remove "./data/" prefix
    position_file_path = os.path.join(project_root, "data", log_path, signature, "position", "position.jsonl")

    if not os.path.exists(position_file_path):
        return 0

    total_bought_today = 0
    with open(position_file_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("date") == today_date:
                    this_action = record.get("this_action", {})
                    if this_action.get("action") == "buy" and this_action.get("symbol") == symbol:
                        total_bought_today += this_action.get("amount", 0)
            except Exception:
                continue

    return total_bought_today


@mcp.tool()
def sell(symbol: str, amount: int) -> Dict[str, Any]:
    """
    Sell stock function

    This function simulates stock selling operations, including the following steps:
    1. Get current position and operation ID
    2. Get stock opening price for the day
    3. Validate sell conditions (position exists, sufficient quantity, lot size, T+1 for CN market)
    4. Update position (decrease stock quantity, increase cash)
    5. Record transaction to position.jsonl file

    Args:
        symbol: Stock symbol, such as "AAPL", "MSFT", etc.
        amount: Sell quantity, must be a positive integer, indicating how many shares to sell
                For Chinese A-shares (symbols ending with .SH or .SZ), must be multiples of 100
                and cannot sell shares bought on the same day (T+1 rule)

    Returns:
        Dict[str, Any]:
          - Success: Returns new position dictionary (containing stock quantity and cash balance)
          - Failure: Returns {"error": error message, ...} dictionary

    Raises:
        ValueError: Raised when SIGNATURE environment variable is not set

    Example:
        >>> result = sell("AAPL", 10)
        >>> print(result)  # {"AAPL": 90, "MSFT": 5, "CASH": 15000.0, ...}
        >>> result = sell("600519.SH", 100)  # Chinese A-shares must be multiples of 100
        >>> print(result)  # {"600519.SH": 0, "CASH": 115000.0, ...}
    """
    # Step 1: Get environment variables and basic information
    # Get signature (model name) from environment variable, used to determine data storage path
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")

    # Get current trading date from environment variable
    today_date = get_config_value("TODAY_DATE")

    # Auto-detect market type based on symbol format
    if symbol.endswith((".SH", ".SZ")):
        market = "cn"
    else:
        market = "us"

    # Amount validation for stocks
    try:
        amount = int(amount)  # Convert to int for stocks
    except ValueError:
        return {
            "error": f"Invalid amount format. Amount must be an integer for stock trading. You provided: {amount}",
            "symbol": symbol,
            "date": today_date,
        }

    if amount <= 0:
        return {
            "error": f"Amount must be positive. You tried to sell {amount} shares.",
            "symbol": symbol,
            "amount": amount,
            "date": today_date,
        }

    # 🇨🇳 Chinese A-shares trading rule: Must trade in lots of 100 shares (一手 = 100股)
    if market == "cn" and amount % 100 != 0:
        return {
            "error": f"Chinese A-shares must be traded in multiples of 100 shares (1 lot = 100 shares). You tried to sell {amount} shares.",
            "symbol": symbol,
            "amount": amount,
            "date": today_date,
            "suggestion": f"Please use {(amount // 100) * 100} or {((amount // 100) + 1) * 100} shares instead.",
        }

    # Step 2: Get current latest position and operation ID
    # get_latest_position returns two values: position dictionary and current maximum operation ID
    # This ID is used to ensure each operation has a unique identifier
    current_position, current_action_id = get_latest_position(today_date, signature)

    # Step 3: Get stock opening price for the day
    # Use get_open_prices function to get the opening price of specified stock for the day
    # If stock symbol does not exist or price data is missing, KeyError exception will be raised
    try:
        this_symbol_price = get_open_prices(today_date, [symbol], market=market)[f"{symbol}_price"]
    except KeyError:
        # Stock symbol does not exist or price data is missing, return error message
        return {
            "error": f"Symbol {symbol} not found! This action will not be allowed.",
            "symbol": symbol,
            "date": today_date,
        }

    # Step 4: Validate sell conditions
    # Check if holding this stock
    if symbol not in current_position:
        return {
            "error": f"No position for {symbol}! This action will not be allowed.",
            "symbol": symbol,
            "date": today_date,
        }

    # Check if position quantity is sufficient for selling
    if current_position[symbol] < amount:
        return {
            "error": "Insufficient shares! This action will not be allowed.",
            "have": current_position.get(symbol, 0),
            "want_to_sell": amount,
            "symbol": symbol,
            "date": today_date,
        }

    # 🇨🇳 Chinese A-shares T+1 trading rule: Cannot sell shares bought on the same day
    if market == "cn":
        bought_today = _get_today_buy_amount(symbol, today_date, signature)
        if bought_today > 0:
            # Calculate sellable quantity (total position - bought today)
            sellable_amount = current_position[symbol] - bought_today
            if amount > sellable_amount:
                return {
                    "error": f"T+1 restriction violated! You bought {bought_today} shares of {symbol} today and cannot sell them until tomorrow.",
                    "symbol": symbol,
                    "total_position": current_position[symbol],
                    "bought_today": bought_today,
                    "sellable_today": max(0, sellable_amount),
                    "want_to_sell": amount,
                    "date": today_date,
                }

    order_payload = {
                    "id": current_action_id + 1,
        "timestamp": today_date,
        "action": "sell",
        "symbol": symbol,
        "amount": amount,
        "price": this_symbol_price,
        "market": market,
    }

    staged_record = {
        "order": order_payload,
        "position_before": current_position,
                }

    write_config_value("IF_TRADE", True)
    return staged_record


if __name__ == "__main__":
    # new_result = buy("AAPL", 1)
    # print(new_result)
    # new_result = sell("AAPL", 1)
    # print(new_result)
    port = int(os.getenv("TRADE_HTTP_PORT", "8002"))
    mcp.run(transport="streamable-http", port=port)
