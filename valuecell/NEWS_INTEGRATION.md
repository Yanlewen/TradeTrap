# News Integration Guide for ValueCell

This guide explains how to use the news integration feature added to ValueCell, which collects news from Alpha Vantage, X/Twitter, and Reddit to enhance AI trading decisions.

## Overview

The news integration feature adds fundamental analysis to ValueCell's technical analysis pipeline. Before making trading decisions, the agent can now collect and analyze:

- **Alpha Vantage News**: Professional financial news with sentiment analysis
- **X/Twitter Posts**: Real-time social media sentiment and discussions
- **Reddit Posts**: Community discussions from finance subreddits

## Architecture

```
Phase 1: Asset Analysis (Updated)
├─ Calculate Technical Indicators (MACD, RSI, Bollinger Bands)
├─ Generate Technical Signals
├─ Collect News (NEW - Parallel execution)
│   ├─ Alpha Vantage News
│   ├─ X/Twitter Search
│   └─ Reddit Search
└─ Generate AI Signals (Enhanced with news)

Phase 2: Portfolio Decision
└─ AI considers both technical and news data

Phase 3: Trade Execution
└─ Execute based on comprehensive analysis
```

## Quick Start

### Step 1: Set Up API Keys

1. **Copy the example environment file** (from project root):

```bash
cd /home/eakal/Word/ai_lab/AI_trade_4_news/TradeTrap
cp .env.example .env
```

2. **Edit the `.env` file** and add your API keys:

```bash
# Required for Alpha Vantage News (used by news collector)
ALPHAADVANTAGE_API_KEY=your_alpha_vantage_key_here

# Optional: For X/Twitter sentiment analysis
X_BEARER_TOKEN=your_x_bearer_token_here

# Optional: For Reddit community discussions
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here

# OpenRouter API Key (required for AI signals)
OPENROUTER_API_KEY=your_openrouter_key_here
```

**Get API Keys:**
- Alpha Vantage: https://www.alphavantage.co/support/#api-key (Free tier available)
- X/Twitter: https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api
- Reddit: https://www.reddit.com/prefs/apps

**Note**: The `.env` file should be located in the project root (`TradeTrap/`), not in the `valuecell/` subdirectory. The main script (`main.py`) loads it and passes configuration to `valuecell`.

### Step 2: Configure Trading Agent

You can configure the agent in two ways:

#### Option A: Using Environment Variables (Recommended)

Set these in your `.env` file (in project root):

```bash
# Trading Configuration
CRYPTO_SYMBOLS=BTC-USD,ETH-USD,AAPL,NVDA
INITIAL_CAPITAL=100000
CHECK_INTERVAL=60
RISK_PER_TRADE=5
MAX_POSITIONS=5
USE_AI_SIGNALS=true
AGENT_MODEL=anthropic/claude-3.5-sonnet

# News Configuration
ENABLE_NEWS=true
ENABLE_ALPHA_VANTAGE_NEWS=true
ENABLE_X_NEWS=false
ENABLE_REDDIT_NEWS=false
MARKET_TYPE=stock

# API Keys (must be set)
ALPHAADVANTAGE_API_KEY=your_key
OPENROUTER_API_KEY=your_key
```

Then run: `python valuecell/run_agent.py`

#### Option B: Programmatic Configuration

```python
from auto_trading_agent.models import AutoTradingConfig
from auto_trading_agent.agent import AutoTradingAgent
import asyncio

# Create configuration with news enabled
config = AutoTradingConfig(
    initial_capital=100000,
    crypto_symbols=["BTC-USD", "ETH-USD", "AAPL", "NVDA"],
    check_interval=60,  # Check every 60 seconds
    risk_per_trade=0.05,  # Risk 5% per trade
    max_positions=5,

    # AI Settings
    use_ai_signals=True,  # Must be True to use news in AI decisions
    agent_model="anthropic/claude-3.5-sonnet",  # or "gpt-4o", etc.

    # News Settings
    enable_news=True,  # Master switch for news collection
    enable_alpha_vantage_news=True,  # Enable Alpha Vantage news
    enable_x_news=False,  # Optional: Enable X/Twitter
    enable_reddit_news=True,  # Optional: Enable Reddit

    market_type="stock",  # "crypto" or "stock"
)

# Create and run agent
async def main():
    agent = AutoTradingAgent(config)
    await agent.run()

asyncio.run(main())
```

**Note**: Even with programmatic config, API keys are still read from environment variables.

### Step 3: Run the Agent

**IMPORTANT**: The `.env` file must be in the project root, and you'll typically run the main script from there:

```bash
# From project root (/home/eakal/Word/ai_lab/AI_trade_4_news/TradeTrap)
cd /home/eakal/Word/ai_lab/AI_trade_4_news/TradeTrap

# Set environment variables (loads .env from current directory)
export $(cat .env | xargs)

# Run your main script (which will configure valuecell)
python main.py

# Or run valuecell directly (it will load .env from parent directory)
cd valuecell
python run_agent.py
```

The `run_agent.py` automatically looks for `.env` in the parent directory (project root) and loads it if found.

## Configuration Options

### News Collection Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_news` | bool | False | Master switch for news collection |
| `enable_alpha_vantage_news` | bool | True | Enable Alpha Vantage financial news |
| `enable_x_news` | bool | False | Enable X/Twitter social media search |
| `enable_reddit_news` | bool | False | Enable Reddit community discussions |

### Requirements

- `enable_news=True` requires `use_ai_signals=True` (news only used in AI analysis)
- Alpha Vantage requires `ALPHAADVANTAGE_API_KEY`
- X/Twitter requires `X_BEARER_TOKEN`
- Reddit requires `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`

## Example Output

When news collection is enabled, you'll see:

```
[2025-10-24 10:00:00] 📊 Phase 1: Analyzing all assets...
DEBUG - Collected news for 4 symbols
DEBUG - AI signal for AAPL: BUY LONG (confidence: 85%)
DEBUG - AI Reasoning: MACD shows bullish crossover and Alpha Vantage news indicates positive earnings sentiment
```

The JSON output will include news data:

```json
{
  "phase1_analysis": [
    {
      "symbol": "AAPL",
      "price": 195.50,
      "indicators": { "macd": 0.45, "rsi": 62.3, ... },
      "ai_signal": {
        "action": "buy",
        "confidence": 85,
        "reasoning": "MACD bullish crossover + positive earnings news"
      },
      "news": {
        "alpha_vantage": [
          {
            "title": "Apple Q4 Earnings Beat Expectations",
            "summary": "Apple reported strong earnings...",
            "overall_sentiment_label": "Positive"
          }
        ]
      }
    }
  ]
}
```

## Testing

Run the test script from the **project root** to verify news collection:

```bash
# From project root
cd /home/eakal/Word/ai_lab/ai_trade_4_news/TradeTrap

# Set environment variables
export $(cat .env | xargs)

# Run test
python valuecell/test_news_integration.py
```

This will:
1. Check your API key configuration from the `.env` file (in project root)
2. Test news collection for AAPL, MSFT, NVDA
3. Display formatted news in prompt format

**Note**: The test script reads API keys from environment variables, so make sure you've loaded your `.env` file first.

## Date Filtering for Backtesting

When running backtests with specific dates (via `run_date_range()` or `run_trading_session()`), the news collector automatically applies date filtering to prevent look-ahead bias:

- **Alpha Vantage**: Filters articles published on or before the current trading date
- **X/Twitter**: Filters tweets posted on or before the current date (limited to last 7 days due to API constraints)
- **Reddit**: Filters posts created on or before the current date

This ensures that the AI agent only sees news that would have been available at the time of each trading decision, making backtest results more realistic.

**Important**: X/Twitter API only supports searching the last 7 days of tweets. When backtesting dates older than 7 days, X/Twitter will return no data and log a warning. Alpha Vantage and Reddit are not subject to this limitation.

### Implementation Details

The date filtering is handled automatically by the `NewsCollector`:

1. When you call `run_trading_session("2025-10-24", "10:00:00")`, the `current_date` is set to "2025-10-24 10:00:00"
2. The `NewsCollector` receives this date and uses it to filter all news sources
3. Only articles/posts published **on or before** 2025-10-24 10:00:00 are returned
4. This prevents the AI from seeing future information

Example log output during backtesting:
```
DEBUG - Collected news for 4 symbols
DEBUG - Date filter applied: 2025-10-24
DEBUG - Alpha Vantage date filter: time_to=20251024T2359
DEBUG - Filtered to 3 articles on/before 2025-10-24
```

## Performance Considerations

### Parallel Execution

News collection is optimized for performance:

- **Outside loop**: Collect news for all symbols once before the trading cycle loop
- **Parallel API calls**: Multiple symbols queried simultaneously using `asyncio.gather`
- **Error isolation**: News failures don't affect technical analysis

```python
# This happens ONCE before the loop
news_dict = await collector.collect_news_for_symbols(symbols)

# Then inside loop:
for symbol in symbols:
    news_result = news_dict.get(symbol)  # Instant lookup
```

### Timeouts and Retries

- Alpha Vantage: 30s timeout
- X/Twitter: 30s timeout
- Reddit: 30s timeout (includes token fetch)

If a news source fails, the error is logged but doesn't stop the trading process.

## Troubleshooting

### News Not Appearing

**Symptom**: No news in output despite `enable_news=True`

**Solutions**:
1. Verify `ALPHAADVANTAGE_API_KEY` is set and valid
2. Check logs for errors: `logger.debug(f"Collected news for {len(symbols)} symbols")`
3. Ensure `use_ai_signals=True` (news only used in AI analysis)
4. Test with `test_news_integration.py`

### API Rate Limits

**Alpha Vantage**: 5 API requests per minute (free tier), 500/day
**X/Twitter**: Varies by subscription tier
**Reddit**: 600 requests per 10 minutes

If hitting rate limits:
- Reduce number of symbols
- Add caching (future enhancement)
- Upgrade API subscription

### Missing Environment Variables

```bash
# From project root, check if .env is loaded
cd /home/eakal/Word/ai_lab/AI_trade_4_news/TradeTrap
export $(cat .env | xargs)

echo $ALPHAADVANTAGE_API_KEY

# Or in Python:
import os
print(os.getenv("ALPHAADVANTAGE_API_KEY"))
```

**If variables are not loaded**: Make sure you're running from the project root directory where `.env` file is located.

## Advanced Usage

### Custom News Processing

You can extend the `NewsCollector` class to add custom news sources:

```python
from auto_trading_agent.news_collector import NewsCollector

class CustomNewsCollector(NewsCollector):
    async def _search_custom_source(self, symbol: str, result: NewsResult):
        # Your custom news API logic
        pass

    async def collect_news_for_symbol(self, symbol: str) -> NewsResult:
        result = await super().collect_news_for_symbol(symbol)
        await self._search_custom_source(symbol, result)
        return result
```

### Filtering News by Relevance

The `to_prompt_text()` method can be customized to filter news:

```python
class FilteredNewsResult(NewsResult):
    def to_prompt_text(self) -> str:
        # Filter by sentiment or date
        filtered = [n for n in self.alpha_vantage_news if n.get("relevance_score", 0) > 0.7]
        self.alpha_vantage_news = filtered
        return super().to_prompt_text()
```

## Future Enhancements

Planned improvements:

- [ ] **News Sentiment Scoring**: Automatic sentiment analysis using LLM
- [ ] **News Caching**: Cache news across trading cycles to reduce API calls
- [ ] **Weighted Importance**: Prioritize news by source credibility and recency
- [ ] **Duplicate Detection**: Remove duplicate news across sources
- [ ] **Custom Filters**: Filter news by keywords, sentiment, or sources
- [ ] **News Impact Analysis**: Historical analysis of news impact on prices

## Contributing

To add a new news source:

1. Add API credentials to `NewsCollector.__init__()`
2. Implement `_search_your_source()` method
3. Update configuration options in `BaseTradingConfig`
4. Add environment variable checks
5. Update this documentation

## Support

For issues or questions:
- Check logs for detailed error messages
- Run test script: `python test_news_integration.py`
- Verify API keys are valid and not rate-limited
- Ensure all required environment variables are set
