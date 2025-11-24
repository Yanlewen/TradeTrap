"""Technical analysis and signal generation (refactored)"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Agent:
    """Minimal async Agent wrapper built on top of langchain ChatOpenAI clients."""

    def __init__(self, model, markdown: bool = False, **kwargs):
        self.model = model
        self.markdown = markdown

    async def arun(self, prompt: str, **kwargs):
        """Invoke the underlying LLM and wrap the response for backward compatibility."""
        response = await self.model.ainvoke(prompt)

        class Response:
            def __init__(self, content):
                self.content = content

        content = response.content if hasattr(response, "content") else str(response)
        return Response(content)


_AGENT_AVAILABLE = True

from .market_data import MarketDataProvider, SignalGenerator
from .models import TechnicalIndicators, TradeAction, TradeType
from .prompts.ai_signal_prompt import get_ai_signal_prompt


class TechnicalAnalyzer:
    """
    Static interface for technical analysis (backward compatible).

    Now delegates to MarketDataProvider internally.
    """

    _market_data_provider = MarketDataProvider()

    @staticmethod
    def set_provider(provider: MarketDataProvider) -> None:
        """Override the default market data provider."""
        TechnicalAnalyzer._market_data_provider = provider

    @staticmethod
    def set_current_date(date: str) -> None:
        """Set current date for historical backtesting."""
        TechnicalAnalyzer._market_data_provider.set_current_date(date)

    @staticmethod
    def calculate_indicators(
        symbol: str, period: str = "5d", interval: str = "60min"
    ) -> Optional[TechnicalIndicators]:
        """
        Calculate technical indicators using local historical data.

        Args:
            symbol: Trading symbol (e.g., BTC-USD)
            period: Data period
            interval: Data interval

        Returns:
            TechnicalIndicators object or None if calculation fails
        """
        return TechnicalAnalyzer._market_data_provider.calculate_indicators(
            symbol, period, interval
        )

    @staticmethod
    def generate_signal(
        indicators: TechnicalIndicators,
    ) -> tuple[TradeAction, TradeType]:
        """
        Generate trading signal based on technical indicators.

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType)
        """
        return SignalGenerator.generate_signal(indicators)


class AISignalGenerator:
    """AI-enhanced signal generation using LLM"""

    def __init__(self, llm_client, signature: Optional[str] = None):
        """
        Initialize AI signal generator

        Args:
            llm_client: OpenRouter client instance
            signature: Agent signature for prompt injection matching
        """
        self.llm_client = llm_client
        self.signature = signature

    async def get_signal(
        self, indicators: TechnicalIndicators
    ) -> Optional[tuple[TradeAction, TradeType, str, float]]:
        """
        Get AI-enhanced trading signal using OpenRouter model

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType, reasoning, confidence) or None if AI not available
        """
        if not self.llm_client or not _AGENT_AVAILABLE:
            return None

        try:
            # Get prompt from prompt module (with signature for injection matching)
            prompt = get_ai_signal_prompt(indicators, signature=self.signature)

            agent = Agent(model=self.llm_client, markdown=False)
            response = await agent.arun(prompt)

            # Parse response
            content = response.content.strip()
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            action = TradeAction(result["action"].lower())
            trade_type = (
                TradeType(result["type"].lower()) if result["type"] else TradeType.LONG
            )
            reasoning = result["reasoning"]
            confidence = float(result.get("confidence", 75.0))

            logger.debug(
                f"AI Signal for {indicators.symbol}: {action.value} {trade_type.value} "
                f"(confidence: {confidence}%) - {reasoning}"
            )

            return (action, trade_type, reasoning, confidence)

        except Exception as e:
            logger.error(f"Failed to get AI trading signal: {e}")
            return None
