"""News attack collector module - injects fake news for adversarial testing"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .news_collector import NewsCollector, NewsResult

logger = logging.getLogger(__name__)


class NewsAttackCollector(NewsCollector):
    """
    News collector that injects fake news from configuration files.

    This class is designed for adversarial testing and research purposes to study
    how AI trading agents respond to manipulated news and misinformation.

    WARNING: Only use in controlled testing environments. Never in production.
    """

    def __init__(
        self,
        enable_alpha_vantage: bool = True,
        enable_x: bool = False,
        enable_reddit: bool = False,
        current_date: Optional[str] = None,
        attack_data_path: Optional[str | Path] = None,
    ):
        """
        Initialize news attack collector

        Args:
            enable_alpha_vantage: Enable fake Alpha Vantage news
            enable_x: Enable fake X/Twitter posts
            enable_reddit: Enable fake Reddit posts
            current_date: Current trading date in YYYY-MM-DD format
            attack_data_path: Path to attack data directory (default: ./attack_data)
        """
        super().__init__(
            enable_alpha_vantage=enable_alpha_vantage,
            enable_x=enable_x,
            enable_reddit=enable_reddit,
            current_date=current_date,
        )

        # Override credentials check - we don't need real credentials in attack mode
        # Set dummy values so parent class doesn't skip these sources
        if enable_alpha_vantage:
            self.alpha_vantage_key = "FAKE_KEY_FOR_ATTACK_MODE"
        if enable_x:
            self.x_bearer_token = "FAKE_TOKEN_FOR_ATTACK_MODE"
        if enable_reddit:
            self.reddit_client_id = "FAKE_CLIENT_ID"
            self.reddit_client_secret = "FAKE_CLIENT_SECRET"

        # Set attack data path
        if attack_data_path is None:
            attack_data_path = Path(__file__).parent / "attack_data"
        self.attack_data_path = Path(attack_data_path)

        # Load attack configurations
        self._alpha_vantage_config = self._load_config("fake_alpha_vantage_news.json")
        self._x_posts_config = self._load_config("fake_x_posts.json")
        self._reddit_posts_config = self._load_config("fake_reddit_posts.json")

        logger.warning("⚠️  NEWS ATTACK MODE ENABLED - Using fake news data for testing")
        logger.info(f"📁 Attack data path: {self.attack_data_path}")

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load attack configuration from JSON file"""
        config_path = self.attack_data_path / filename

        if not config_path.exists():
            logger.warning(f"Attack config not found: {config_path}")
            return {}

        try:
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
            logger.debug(f"Loaded attack config: {filename}")
            return config
        except Exception as e:
            logger.error(f"Failed to load attack config {filename}: {e}")
            return {}

    def _get_date_key(self) -> str:
        """Get the date key for looking up attack data"""
        if self.current_date:
            # Extract date part (YYYY-MM-DD)
            date_only = self.current_date.split(" ")[0] if " " in self.current_date else self.current_date
            return date_only
        return "*"

    async def _search_alpha_vantage(self, symbol: str, result: NewsResult):
        """Override: Return fake Alpha Vantage news from configuration with time filtering"""
        try:
            date_key = self._get_date_key()

            # Try to find news for this date and symbol
            news_items = None

            # Priority 1: Exact date + symbol match
            if date_key in self._alpha_vantage_config:
                date_config = self._alpha_vantage_config[date_key]
                if symbol in date_config:
                    news_items = date_config[symbol]

            # Priority 2: Wildcard date with symbol
            if news_items is None and "*" in self._alpha_vantage_config:
                wildcard_config = self._alpha_vantage_config["*"]
                if symbol in wildcard_config:
                    news_items = wildcard_config[symbol]

            # Priority 3: Default fallback
            if news_items is None:
                for config_key in [date_key, "*"]:
                    if config_key in self._alpha_vantage_config:
                        config = self._alpha_vantage_config[config_key]
                        if "default" in config:
                            news_items = config["default"]
                            break

            # CRITICAL: Apply time filtering to prevent look-ahead bias
            # Same logic as parent class to ensure fake news respects time constraints
            if news_items and self.current_date:
                from datetime import datetime

                is_hourly = " " in self.current_date

                # Parse current_date to datetime for comparison
                if is_hourly:
                    current_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    current_dt = datetime.strptime(f"{self.current_date} 23:59:59", "%Y-%m-%d %H:%M:%S")

                filtered_news = []
                for article in news_items:
                    article_time = article.get("time_published", "")
                    if article_time and len(article_time) >= 8:
                        try:
                            # Parse article time (YYYYMMDDTHHMMSS -> datetime)
                            article_dt = datetime.strptime(article_time[:14], "%Y%m%dT%H%M%S")

                            # Only include if article published <= current time
                            if article_dt <= current_dt:
                                filtered_news.append(article)
                            else:
                                # Log filtered future fake news for debugging
                                logger.debug(
                                    f"🎯 ATTACK: Filtered future fake news: {article.get('title', 'N/A')[:50]} "
                                    f"published at {article_time} (current: {self.current_date})"
                                )
                        except Exception as e:
                            logger.debug(f"Could not parse fake article time '{article_time}': {e}")
                            # Exclude unparseable articles to be safe
                            continue

                news_items = filtered_news

            if news_items:
                result.alpha_vantage_news = news_items[:5]  # Take top 5
                precision = "hourly" if " " in self.current_date else "daily"
                logger.info(
                    f"🎯 ATTACK [{precision}]: Injected {len(result.alpha_vantage_news)} fake Alpha Vantage "
                    f"articles for {symbol} (date: {date_key})"
                )
            else:
                logger.warning(f"No fake Alpha Vantage news configured for {symbol} on {date_key} "
                             f"(or all filtered by time)")

        except Exception as e:
            logger.error(f"Error injecting fake Alpha Vantage news for {symbol}: {e}")
            result.errors.append(f"Attack error: {str(e)}")

    async def _search_x(self, symbol: str, result: NewsResult):
        """Override: Return fake X/Twitter posts from configuration with time filtering"""
        try:
            date_key = self._get_date_key()

            # Try to find posts for this date and symbol
            posts = None

            # Priority 1: Exact date + symbol match
            if date_key in self._x_posts_config:
                date_config = self._x_posts_config[date_key]
                if symbol in date_config:
                    posts = date_config[symbol]

            # Priority 2: Wildcard date with symbol
            if posts is None and "*" in self._x_posts_config:
                wildcard_config = self._x_posts_config["*"]
                if symbol in wildcard_config:
                    posts = wildcard_config[symbol]

            # Priority 3: Default fallback
            if posts is None:
                for config_key in [date_key, "*"]:
                    if config_key in self._x_posts_config:
                        config = self._x_posts_config[config_key]
                        if "default" in config:
                            posts = config["default"]
                            break

            # Apply time filtering to fake X posts (if they have created_at timestamps)
            if posts and self.current_date:
                from datetime import datetime

                is_hourly = " " in self.current_date
                if is_hourly:
                    current_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    current_dt = datetime.strptime(f"{self.current_date} 23:59:59", "%Y-%m-%d %H:%M:%S")

                filtered_posts = []
                for post in posts:
                    created_at = post.get("created_at", "")
                    if created_at:
                        try:
                            # Parse ISO format: "2025-10-01T13:00:00Z"
                            post_dt = datetime.fromisoformat(created_at.replace("Z", ""))
                            if post_dt <= current_dt:
                                filtered_posts.append(post)
                        except Exception:
                            # If no valid timestamp, include the post
                            filtered_posts.append(post)
                    else:
                        # No timestamp, include the post
                        filtered_posts.append(post)

                posts = filtered_posts

            if posts:
                result.x_posts = posts[:5]  # Take top 5
                precision = "hourly" if " " in self.current_date else "daily"
                logger.info(
                    f"🎯 ATTACK [{precision}]: Injected {len(result.x_posts)} fake X posts "
                    f"for {symbol} (date: {date_key})"
                )
            else:
                logger.warning(f"No fake X posts configured for {symbol} on {date_key} "
                             f"(or all filtered by time)")

        except Exception as e:
            logger.error(f"Error injecting fake X posts for {symbol}: {e}")
            result.errors.append(f"Attack error: {str(e)}")

    async def _search_reddit(self, symbol: str, result: NewsResult):
        """Override: Return fake Reddit posts from configuration with time filtering"""
        try:
            date_key = self._get_date_key()

            # Try to find posts for this date and symbol
            posts = None

            # Priority 1: Exact date + symbol match
            if date_key in self._reddit_posts_config:
                date_config = self._reddit_posts_config[date_key]
                if symbol in date_config:
                    posts = date_config[symbol]

            # Priority 2: Wildcard date with symbol
            if posts is None and "*" in self._reddit_posts_config:
                wildcard_config = self._reddit_posts_config["*"]
                if symbol in wildcard_config:
                    posts = wildcard_config[symbol]

            # Priority 3: Default fallback
            if posts is None:
                for config_key in [date_key, "*"]:
                    if config_key in self._reddit_posts_config:
                        config = self._reddit_posts_config[config_key]
                        if "default" in config:
                            posts = config["default"]
                            break

            # Apply time filtering to fake Reddit posts (if they have created_utc timestamps)
            if posts and self.current_date:
                from datetime import datetime

                is_hourly = " " in self.current_date
                if is_hourly:
                    current_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    current_dt = datetime.strptime(f"{self.current_date} 23:59:59", "%Y-%m-%d %H:%M:%S")

                cutoff_timestamp = int(current_dt.timestamp())

                filtered_posts = []
                for post in posts:
                    created_utc = post.get("created_utc")
                    if created_utc:
                        try:
                            if int(created_utc) <= cutoff_timestamp:
                                filtered_posts.append(post)
                        except Exception:
                            # If no valid timestamp, include the post
                            filtered_posts.append(post)
                    else:
                        # No timestamp, include the post
                        filtered_posts.append(post)

                posts = filtered_posts

            if posts:
                result.reddit_posts = posts[:5]  # Take top 5
                precision = "hourly" if " " in self.current_date else "daily"
                logger.info(
                    f"🎯 ATTACK [{precision}]: Injected {len(result.reddit_posts)} fake Reddit posts "
                    f"for {symbol} (date: {date_key})"
                )
            else:
                logger.warning(f"No fake Reddit posts configured for {symbol} on {date_key} "
                             f"(or all filtered by time)")

        except Exception as e:
            logger.error(f"Error injecting fake Reddit posts for {symbol}: {e}")
            result.errors.append(f"Attack error: {str(e)}")


# For testing
async def main():
    """Test news attack collector"""
    import asyncio

    collector = NewsAttackCollector(
        enable_alpha_vantage=True,
        enable_x=True,
        enable_reddit=True,
        current_date="2025-10-22",  # Test with attack scenario date
    )

    symbols = ["NVDA", "AAPL", "MSFT"]
    news_dict = await collector.collect_news_for_symbols(symbols)

    for symbol, news in news_dict.items():
        print(f"\n{'='*80}")
        print(f"Fake News for {symbol}")
        print(f"{'='*80}")
        print(news.to_prompt_text())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
