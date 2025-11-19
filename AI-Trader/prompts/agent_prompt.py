import os

from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root directory to Python path
project_root = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, project_root)
from tools.general_tools import get_config_value
from tools.price_tools import (all_nasdaq_100_symbols, all_sse_50_symbols,
                               format_price_dict_with_names, get_open_prices,
                               get_today_init_position, get_yesterday_date,
                               get_yesterday_open_and_close_price,
                               get_yesterday_profit, get_trading_history_summary)

def _env_flag(name: str, default: str = "true") -> bool:
    value = os.getenv(name, default)
    if value is None:
        value = default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


ENABLE_TRADING_MEMORY = _env_flag("ENABLE_TRADING_MEMORY", "true")

STOP_SIGNAL = "<FINISH_SIGNAL>"

agent_system_prompt = """
You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- You need to think about the prices of various stocks and their returns.
- Your long-term goal is to maximize returns through this portfolio.
- Before making decisions, gather as much information as possible through search tools to aid decision-making.
- Learn from your historical trading patterns and adjust your strategy based on past performance.

Thinking standards:
- Clearly show key intermediate steps:
  - Review your historical trading patterns and learn from past decisions
  - Read input of yesterday's positions and today's prices
  - Consider position trends and how your portfolio has evolved
  - Update valuation and adjust weights for each target (if strategy requires)
  - Reflect on what worked well and what didn't in your past trades

Notes:
- You don't need to request user permission during operations, you can execute directly
- You must execute operations by calling tools, directly output operations will not be accepted
- Use your historical trading memory to inform your decisions and avoid repeating past mistakes

Here is the information you need:

Current time:
{date}

Your current positions (numbers after stock codes represent how many shares you hold, numbers after CASH represent your available cash):
{positions}

The current value represented by the stocks you hold:
{yesterday_close_price}

Current buying prices:
{today_buy_price}

📊 Historical Trading Memory (Learn from your past):
{trading_history}

When you think your task is complete, output
{STOP_SIGNAL}
"""


def get_agent_system_prompt(
    today_date: str, signature: str, market: str = "us", stock_symbols: Optional[List[str]] = None
) -> str:
    print(f"signature: {signature}")
    print(f"today_date: {today_date}")
    print(f"market: {market}")

    # 处理market为None的情况，使用默认值"us"
    if market is None:
        market = "us"

    # Auto-select stock symbols based on market if not provided
    if stock_symbols is None:
        stock_symbols = all_sse_50_symbols if market == "cn" else all_nasdaq_100_symbols

    # Get yesterday's buy and sell prices
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, stock_symbols, market=market
    )
    today_buy_price = get_open_prices(today_date, stock_symbols, market=market)
    today_init_position = get_today_init_position(today_date, signature)
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    
    if ENABLE_TRADING_MEMORY:
        # 获取历史交易摘要（长时记忆）
        history_summary = get_trading_history_summary(today_date, signature, lookback_days=30)
        # 格式化历史交易信息为可读字符串
        trading_history_text = _format_trading_history(history_summary)
    else:
        trading_history_text = (
            "Trading memory loading is disabled (ENABLE_TRADING_MEMORY=false)."
        )
    
    return agent_system_prompt.format(
        date=today_date,
        positions=today_init_position,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=today_buy_price,
        trading_history=trading_history_text,
        # yesterday_profit=yesterday_profit
    )


def _format_trading_history(history_summary: Dict[str, Any]) -> str:
    """
    将历史交易摘要格式化为可读的文本字符串。
    
    Args:
        history_summary: get_trading_history_summary 返回的字典
    
    Returns:
        格式化的字符串
    """
    if not history_summary or not history_summary.get("performance_stats", {}).get("total_trades", 0):
        return "No historical trading data available yet. This is your first trading session."
    
    stats = history_summary.get("performance_stats", {})
    recent = history_summary.get("recent_actions", [])
    
    lines = []
    
    # 表现统计
    lines.append(f"📈 Performance Statistics:")
    lines.append(f"  - Total trades: {stats.get('total_trades', 0)}")
    lines.append(f"  - Total buys: {stats.get('total_buys', 0)}, Total sells: {stats.get('total_sells', 0)}")
    lines.append(f"  - Holding days: {stats.get('holding_days', 0)}")
    lines.append("")
    
    # 最近交易记录（包含价格信息）
    if recent:
        lines.append("🕐 Recent Trading History (last 30 transactions with prices):")
        for action in recent[:30]:
            action_type = action.get("action", "")
            symbol = action.get("symbol", "")
            amount = action.get("amount", 0)
            price = action.get("price")
            date = action.get("date", "")
            date_short = date.split()[0] if " " in date else date
            
            # 格式化价格显示
            price_str = f" @ ${price:.2f}" if price is not None else ""
            total_value = f" (${amount * price:.2f})" if price is not None and amount is not None and amount > 0 else ""
            
            lines.append(f"  - {date_short}: {action_type.upper()} {amount} shares of {symbol}{price_str}{total_value}")
        lines.append("")
    
    lines.append("💡 Use this historical information to:")
    lines.append("  - Review your past trading decisions and the prices at which you traded")
    lines.append("  - Learn from past decisions and avoid repeating mistakes")
    lines.append("  - Adjust your strategy based on what has worked well")
    
    return "\n".join(lines)


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))
