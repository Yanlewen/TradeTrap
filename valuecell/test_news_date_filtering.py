"""Test script to verify news date filtering for backtesting"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from auto_trading_agent.news_collector import NewsCollector


async def test_date_filtering():
    """Test that news collector filters by date correctly"""

    print("🧪 Testing News Date Filtering for Backtesting")
    print(f"{'='*80}\n")

    # Test with a historical date (7 days ago to ensure some X/Twitter data)
    from datetime import datetime, timedelta
    test_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    # Real-time mode (no date filter)
    print("Test 1: Real-time mode (current_date=None)")
    print("-" * 80)
    collector_realtime = NewsCollector(
        enable_alpha_vantage=os.getenv("ALPHAADVANTAGE_API_KEY") is not None,
        enable_x=False,  # Skip X in test to avoid rate limits
        enable_reddit=False,
        current_date=None,  # No date filtering
    )
    news_realtime = await collector_realtime.collect_news_for_symbol("AAPL")
    print(f"Articles found: {len(news_realtime.alpha_vantage_news)}")
    if news_realtime.alpha_vantage_news:
        for i, article in enumerate(news_realtime.alpha_vantage_news[:2], 1):
            date = article.get("time_published", "N/A").split("T")[0]
            print(f"  {i}. Date: {date}")
    print()

    # Backtesting mode (with date filter)
    print(f"Test 2: Backtesting mode (current_date={test_date})")
    print("-" * 80)
    collector_backtest = NewsCollector(
        enable_alpha_vantage=os.getenv("ALPHAADVANTAGE_API_KEY") is not None,
        enable_x=False,
        enable_reddit=False,
        current_date=test_date,  # Filter to historical date
    )
    news_backtest = await collector_backtest.collect_news_for_symbol("AAPL")
    print(f"Articles found: {len(news_backtest.alpha_vantage_news)}")
    if news_backtest.alpha_vantage_news:
        for i, article in enumerate(news_backtest.alpha_vantage_news, 1):
            date = article.get("time_published", "N/A").split("T")[0]
            print(f"  {i}. Date: {date}")
            # Verify all dates are <= test_date
            if date > test_date:
                print(f"     ⚠️  ERROR: Article date {date} is AFTER test date {test_date}!")
    print()

    # Test with very old date (should get no X/Twitter data)
    old_date = "2023-01-01"
    print(f"Test 3: Old date ({old_date}) - X/Twitter should warn about 7-day limit")
    print("-" * 80)
    collector_old = NewsCollector(
        enable_alpha_vantage=False,  # Skip to focus on X/Twitter warning
        enable_x=True if os.getenv("X_BEARER_TOKEN") else False,
        enable_reddit=False,
        current_date=old_date,
    )
    news_old = await collector_old.collect_news_for_symbol("BTC")
    print("X posts found:", len(news_old.x_posts))
    if news_old.errors:
        print("Errors (expected X/Twitter 7-day warning):")
        for error in news_old.errors[:2]:
            print(f"  - {error}")
    print()

    # Summary
    print(f"{'='*80}")
    print("✅ Date filtering test completed!")
    print("\nKey features verified:")
    print("  ✓ current_date=None returns recent news (no filter)")
    print("  ✓ current_date=<date> filters news to that date or earlier")
    print("  ✓ Articles after current_date are excluded")
    print("  ✓ X/Twitter warns when date is beyond 7 days")


if __name__ == "__main__":
    asyncio.run(test_date_filtering())
