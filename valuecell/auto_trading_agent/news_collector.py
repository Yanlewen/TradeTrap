"""News collection module for integrating AI-Trader news sources"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


class NewsResult:
    """News search result for a symbol"""

    def __init__(self):
        self.alpha_vantage_news: List[Dict[str, Any]] = []  # Alpha Vantage 专业新闻
        self.x_posts: List[Dict[str, Any]] = []            # Twitter/X 帖子
        self.reddit_posts: List[Dict[str, Any]] = []       # Reddit 帖子
        self.errors: List[str] = []                        # 错误信息

    def is_empty(self) -> bool:
        """Check if all news sources are empty"""
        return (
            len(self.alpha_vantage_news) == 0
            and len(self.x_posts) == 0
            and len(self.reddit_posts) == 0
        )

    def to_prompt_text(self) -> str:
        """Convert news to prompt text for LLM"""
        sections = []

        if self.alpha_vantage_news:
            sections.append("=== Alpha Vantage News (Professional) ===")
            for i, article in enumerate(self.alpha_vantage_news[:5], 1):
                title = article.get("title", "N/A")
                summary = article.get("summary", "")[:500]
                sentiment = article.get("overall_sentiment_label", "N/A")
                sections.append(f"{i}. {title}\n   Sentiment: {sentiment}\n   Summary: {summary}\n")

        if self.x_posts:
            sections.append("=== X/Twitter Posts (Social Media) ===")
            for i, post in enumerate(self.x_posts[:5], 1):
                text = post.get("text", "")[:300]
                metrics = post.get("public_metrics", {})
                likes = metrics.get("like_count", 0)
                retweets = metrics.get("retweet_count", 0)
                sections.append(f"{i}. {text}\n   Engagement: {likes} likes, {retweets} retweets\n")

        if self.reddit_posts:
            sections.append("=== Reddit Posts (Community Discussion) ===")
            for i, post in enumerate(self.reddit_posts[:5], 1):
                title = post.get("title", "N/A")
                subreddit = post.get("subreddit", "N/A")
                score = post.get("score", 0)
                comments = post.get("num_comments", 0)
                content = post.get("selftext", "")[:300]
                sections.append(
                    f"{i}. r/{subreddit}: {title}\n"
                    f"   Score: {score} | Comments: {comments}\n"
                    f"   Content: {content}\n"
                )

        if not sections:
            return "No news data available for this asset.\n"

        if self.errors:
            sections.append("=== Errors ===")
            for error in self.errors:
                sections.append(f"- {error}\n")

        return "\n".join(sections)


class NewsCollector:
    """Collect news from multiple sources for a list of symbols"""

    def __init__(
        self,
        enable_alpha_vantage: bool = True,
        enable_x: bool = False,
        enable_reddit: bool = False,
        current_date: Optional[str] = None,
    ):
        """
        Initialize news collector

        Args:
            enable_alpha_vantage: Enable Alpha Vantage news (requires API key)
            enable_x: Enable X/Twitter search (requires bearer token)
            enable_reddit: Enable Reddit search
            current_date: Current trading date in YYYY-MM-DD format for backtesting.
                         If None, uses today's date and only gets recent news.
        """
        self.enable_alpha_vantage = enable_alpha_vantage
        self.enable_x = enable_x
        self.enable_reddit = enable_reddit
        self.current_date = current_date  # For backtesting date filtering

        # Load API keys
        self.alpha_vantage_key = os.getenv("ALPHAADVANTAGE_API_KEY")
        self.x_bearer_token = os.getenv("X_BEARER_TOKEN")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")

        # Validate API keys
        if enable_alpha_vantage and not self.alpha_vantage_key:
            logger.warning("Alpha Vantage enabled but ALPHAADVANTAGE_API_KEY not set")

        if enable_x and not self.x_bearer_token:
            logger.warning("X/Twitter enabled but X_BEARER_TOKEN not set")

        if enable_reddit and not (self.reddit_client_id and self.reddit_client_secret):
            logger.warning("Reddit enabled but Reddit credentials not set")

    async def collect_news_for_symbol(self, symbol: str) -> NewsResult:
        """Collect news for a single symbol (parallel execution)"""
        result = NewsResult()

        # Remove exchange suffix for news search (e.g., "AAPL" instead of "AAPL-USD")
        clean_symbol = self._clean_symbol(symbol)

        # Create tasks for parallel execution
        tasks = []

        if self.enable_alpha_vantage and self.alpha_vantage_key:
            tasks.append(self._search_alpha_vantage(clean_symbol, result))

        if self.enable_x and self.x_bearer_token:
            tasks.append(self._search_x(clean_symbol, result))

        if self.enable_reddit and self.reddit_client_id:
            tasks.append(self._search_reddit(clean_symbol, result))

        # Execute all tasks in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return result

    async def collect_news_for_symbols(self, symbols: List[str]) -> Dict[str, NewsResult]:
        """Collect news for multiple symbols (parallel execution)"""
        tasks = []
        for symbol in symbols:
            task = self.collect_news_for_symbol(symbol)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to symbols
        news_dict = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error collecting news for {symbols[i]}: {result}")
                news_dict[symbols[i]] = NewsResult()
                news_dict[symbols[i]].errors.append(str(result))
            else:
                news_dict[symbols[i]] = result

        return news_dict

    def _clean_symbol(self, symbol: str) -> str:
        """Remove exchange suffix and common separators"""
        # Remove common suffixes
        symbol = symbol.split("-")[0]  # BTC-USD -> BTC
        symbol = symbol.split(".")[0]  # AAPL.US -> AAPL
        symbol = symbol.split(":")[0]  # CRYPTO:BTC -> CRYPTO
        return symbol

    async def _search_alpha_vantage(self, symbol: str, result: NewsResult):
        """Search Alpha Vantage news"""
        try:
            import aiohttp

            # Use aiohttp for async requests
            async with aiohttp.ClientSession() as session:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "NEWS_SENTIMENT",
                    "tickers": symbol,
                    "apikey": self.alpha_vantage_key,
                    "limit": 20,  # Get more articles to filter
                    "sort": "LATEST",
                }

                # Add date range filter for backtesting
                # Alpha Vantage requires BOTH time_from and time_to to define a time range
                # IMPORTANT: Prevent look-ahead bias - only get news published BEFORE current time
                if self.current_date:
                    # Parse current_date (format: "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD")
                    from datetime import datetime, timedelta

                    try:
                        is_hourly = " " in self.current_date  # Hourly if datetime, daily if only date

                        if is_hourly:
                            # HOURLY MODE: Parse full datetime for hour-level precision
                            # Example: "2025-10-01 12:00:00" -> get news up to 12:00, NOT 12:30
                            current_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                            precision = "hourly"
                        else:
                            # DAILY MODE: Only date provided, get news for entire day
                            # Example: "2025-10-01" -> get all news on 2025-10-01
                            current_dt = datetime.strptime(f"{self.current_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
                            precision = "daily"

                        # Format: YYYYMMDDTHHMM
                        date_str = current_dt.strftime("%Y%m%d")
                        time_str = current_dt.strftime("%H%M")

                        params["time_from"] = f"{date_str}T0000"  # Start of day
                        params["time_to"] = f"{date_str}T{time_str}"  # Current time (prevents future data)

                        logger.info(f"Alpha Vantage time filter [{precision}]: {params['time_from']} to {params['time_to']}")
                    except Exception as e:
                        logger.warning(f"Could not parse current_date '{self.current_date}': {e}. Using date-only filter.")
                        # Fallback to date-only
                        date_only = self.current_date.split(" ")[0] if " " in self.current_date else self.current_date
                        date_str = date_only.replace("-", "")
                        params["time_from"] = f"{date_str}T0000"
                        params["time_to"] = f"{date_str}T2359"

                async with session.get(url, params=params, timeout=30) as response:
                    logger.info(f"Alpha Vantage API request for {symbol}: status={response.status}, date_filter={params.get('time_to', 'none')}")
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check for API error messages
                        if "Error Message" in data:
                            error_msg = f"Alpha Vantage API error for {symbol}: {data['Error Message']}"
                            logger.error(error_msg)
                            result.errors.append(error_msg)
                            return
                        
                        if "Note" in data:
                            logger.warning(f"Alpha Vantage API note for {symbol}: {data['Note']}")
                        
                        if "Information" in data:
                            logger.warning(f"Alpha Vantage API info for {symbol}: {data['Information']}")
                        
                        feed = data.get("feed", [])
                        logger.info(f"Alpha Vantage raw response for {symbol}: {len(feed)} articles before filtering")
                        
                        # Log first article for debugging if available
                        if feed and logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Sample article: {feed[0].get('title', 'N/A')} - {feed[0].get('time_published', 'N/A')}")

                        # Client-side filtering: Double-check to prevent look-ahead bias
                        # This ensures no future news leaks into trading decisions
                        if self.current_date and feed:
                            from datetime import datetime

                            filtered_feed = []
                            is_hourly = " " in self.current_date

                            # Parse current_date to datetime for comparison
                            try:
                                if is_hourly:
                                    # HOURLY MODE: Strict filtering - only news published BEFORE current hour
                                    current_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                                else:
                                    # DAILY MODE: Get all news on/before current day
                                    current_dt = datetime.strptime(f"{self.current_date} 23:59:59", "%Y-%m-%d %H:%M:%S")

                                for article in feed:
                                    # Alpha Vantage returns time_published in ISO format (YYYYMMDDTHHMMSS)
                                    article_time = article.get("time_published", "")
                                    if article_time and len(article_time) >= 8:
                                        try:
                                            # Parse article time (YYYYMMDDTHHMMSS -> datetime)
                                            article_dt = datetime.strptime(article_time[:14], "%Y%m%dT%H%M%S")

                                            # CRITICAL: Only include if article published <= current time
                                            # This prevents using future information (e.g., 12:30 news when trading at 12:00)
                                            if article_dt <= current_dt:
                                                filtered_feed.append(article)
                                            else:
                                                # Log filtered future articles for debugging
                                                logger.debug(f"Filtered future article: {article.get('title', 'N/A')[:50]} "
                                                           f"published at {article_time} (current: {self.current_date})")
                                        except Exception as e:
                                            logger.debug(f"Could not parse article time '{article_time}': {e}")
                                            # If parsing fails, exclude to be safe (prevent potential data leakage)
                                            continue

                                feed = filtered_feed
                                precision = "hourly" if is_hourly else "daily"
                                logger.info(f"Client-side filter [{precision}]: {len(feed)} articles on/before {self.current_date}")
                            except Exception as e:
                                logger.warning(f"Error in client-side datetime filtering: {e}. Keeping all articles.")
                                # Keep all articles if filtering fails

                        result.alpha_vantage_news = feed[:5]  # Take top 5
                        logger.debug(f"Found {len(feed)} Alpha Vantage articles for {symbol}")
                    else:
                        error_msg = f"Alpha Vantage API error: {response.status}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)
        except Exception as e:
            logger.error(f"Error searching Alpha Vantage for {symbol}: {e}")
            result.errors.append(f"Alpha Vantage error: {str(e)}")

    async def _search_x(self, symbol: str, result: NewsResult):
        """Search X/Twitter posts"""
        try:
            import aiohttp
            from datetime import datetime, timedelta

            # X API v2 Recent Search (only supports last 7 days)
            # For backtesting with older dates, we cannot search but we can still filter
            async with aiohttp.ClientSession() as session:
                url = "https://api.twitter.com/2/tweets/search/recent"

                # Build query (last 7 days)
                query = f"${symbol} OR #{symbol}"
                params = {
                    "query": query,
                    "max_results": 20,
                    "tweet.fields": "created_at,lang,public_metrics,author_id",
                }

                # Add end_time for backtesting if date is within last 7 days
                if self.current_date:
                    # Convert current_date to datetime
                    try:
                        current_dt = datetime.fromisoformat(self.current_date.replace("Z", ""))
                        # X API only supports last 7 days, check if date is recent
                        days_ago = (datetime.now() - current_dt).days
                        if days_ago <= 7:
                            # Format as ISO 8601/RFC 3339 for X API
                            end_time = current_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                            params["end_time"] = end_time
                            logger.debug(f"X/Twitter date filter: end_time={end_time}")
                        else:
                            logger.warning(
                                f"X/Twitter cannot search beyond 7 days. "
                                f"Current date {self.current_date} is {days_ago} days ago. "
                                f"No X data available for backtesting this date."
                            )
                            result.errors.append(
                                f"X/Twitter: Date {self.current_date} is beyond 7-day search limit"
                            )
                    except Exception as e:
                        logger.warning(f"Could not parse current_date for X API: {e}")

                headers = {"Authorization": f"Bearer {self.x_bearer_token}"}

                async with session.get(url, params=params, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        tweets = data.get("data", [])

                        # Filter tweets by date for backtesting
                        if self.current_date and tweets:
                            filtered_tweets = []
                            for tweet in tweets:
                                tweet_time = tweet.get("created_at", "")
                                if tweet_time:
                                    # Compare dates (YYYY-MM-DD format)
                                    tweet_date = tweet_time.split("T")[0]
                                    current_date_only = self.current_date.split(" ")[0] if " " in self.current_date else self.current_date
                                    if tweet_date <= current_date_only:
                                        filtered_tweets.append(tweet)
                            tweets = filtered_tweets
                            logger.debug(f"Filtered to {len(tweets)} tweets on/before {self.current_date}")

                        result.x_posts = tweets[:5]  # Take top 5
                        logger.debug(f"Found {len(tweets)} X posts for {symbol}")
                    else:
                        result.errors.append(f"X API error: {response.status}")
        except Exception as e:
            logger.error(f"Error searching X for {symbol}: {e}")
            result.errors.append(f"X API error: {str(e)}")

    async def _search_reddit(self, symbol: str, result: NewsResult):
        """Search Reddit posts"""
        try:
            import aiohttp
            import asyncio
            from datetime import datetime

            # Calculate cutoff timestamp for backtesting
            cutoff_timestamp = None
            if self.current_date:
                try:
                    # Parse current date (could be "2025-10-24" or "2025-10-24 10:00:00")
                    if " " in self.current_date:
                        current_dt = datetime.fromisoformat(self.current_date)
                    else:
                        # Set to end of day (23:59:59) of current_date
                        current_dt = datetime.fromisoformat(f"{self.current_date}T23:59:59")
                    cutoff_timestamp = int(current_dt.timestamp())
                    logger.debug(f"Reddit cutoff timestamp: {cutoff_timestamp} for {self.current_date}")
                except Exception as e:
                    logger.warning(f"Could not parse current_date for Reddit: {e}")

            # First, get Reddit access token
            token = await self._get_reddit_token()
            if not token:
                result.errors.append("Failed to get Reddit access token")
                return

            async with aiohttp.ClientSession() as session:
                # Search in finance-related subreddits
                search_url = "https://oauth.reddit.com/search.json"
                params = {
                    "q": symbol,
                    "restrict_sr": "off",
                    "sort": "relevance",
                    "t": "week",  # Last week (will filter further)
                    "limit": 20,
                }

                headers = {"Authorization": f"Bearer {token}", "User-Agent": "TradingAgent/1.0"}

                async with session.get(search_url, params=params, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = []
                        for child in data.get("data", {}).get("children", []):
                            post_data = child.get("data", {})
                            if post_data:
                                posts.append({
                                    "title": post_data.get("title", ""),
                                    "selftext": post_data.get("selftext", ""),
                                    "subreddit": post_data.get("subreddit", ""),
                                    "score": post_data.get("score", 0),
                                    "num_comments": post_data.get("num_comments", 0),
                                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                    "created_utc": post_data.get("created_utc"),
                                })

                        # Filter posts by date for backtesting
                        if cutoff_timestamp and posts:
                            filtered_posts = []
                            for post in posts:
                                post_timestamp = post.get("created_utc")
                                if post_timestamp and post_timestamp <= cutoff_timestamp:
                                    filtered_posts.append(post)
                            posts = filtered_posts
                            logger.debug(f"Filtered to {len(posts)} posts on/before {self.current_date}")

                        result.reddit_posts = posts[:5]  # Take top 5
                        logger.debug(f"Found {len(posts)} Reddit posts for {symbol}")
                    else:
                        result.errors.append(f"Reddit API error: {response.status}")
        except Exception as e:
            logger.error(f"Error searching Reddit for {symbol}: {e}")
            result.errors.append(f"Reddit error: {str(e)}")

    async def _get_reddit_token(self) -> Optional[str]:
        """Get Reddit OAuth token"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(self.reddit_client_id, self.reddit_client_secret)
                data = {"grant_type": "client_credentials"}
                headers = {"User-Agent": "TradingAgent/1.0"}

                async with session.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=auth,
                    data=data,
                    headers=headers,
                    timeout=10,
                ) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        return token_data.get("access_token")
                    else:
                        logger.error(f"Reddit auth error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting Reddit token: {e}")
            return None


# For testing
async def main():
    """Test news collector"""
    collector = NewsCollector(
        enable_alpha_vantage=True,
        enable_x=False,  # Set to True if you have X_BEARER_TOKEN
        enable_reddit=False,  # Set to True if you have Reddit credentials
    )

    symbols = ["AAPL", "BTC"]
    news_dict = await collector.collect_news_for_symbols(symbols)

    for symbol, news in news_dict.items():
        print(f"\n{'='*80}")
        print(f"News for {symbol}")
        print(f"{'='*80}")
        print(news.to_prompt_text())


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
