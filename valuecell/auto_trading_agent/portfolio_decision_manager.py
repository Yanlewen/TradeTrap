"""Portfolio-level decision manager using AI for coordinated multi-asset trading decisions"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Agent:
    """Minimal async agent wrapper that parses JSON into optional schemas."""

    def __init__(self, model, output_schema=None, markdown: bool = False, **kwargs):
        self.model = model
        self.output_schema = output_schema
        self.markdown = markdown

    async def arun(self, prompt: str, **kwargs):
        response = await self.model.ainvoke(prompt)
        raw_content = response.content if hasattr(response, "content") else str(response)

        if self.output_schema:
            content = self._parse_to_schema(raw_content)
        else:
            content = raw_content

        class Response:
            def __init__(self, content):
                self.content = content

        return Response(content)

    def _parse_to_schema(self, text: str):
        """Extract JSON payload (supports fenced blocks) and load into schema."""
        json_text = text
        if "```json" in json_text:
            json_text = json_text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in json_text:
            json_text = json_text.split("```", 1)[1].split("```", 1)[0]

        data = json.loads(json_text)
        if self.output_schema:
            return self.output_schema(**data)
        return data


_PORTFOLIO_AGENT_AVAILABLE = True

from pydantic import BaseModel, Field

from .models import (
    AssetAnalysis,
    AutoTradingConfig,
    Position,
    TechnicalIndicators,
    TradeAction,
    TradeType,
)
from .prompts.portfolio_prompt import get_portfolio_prompt


class TradeDecision(BaseModel):
    """Single trade decision"""

    symbol: str = Field(..., description="Trading symbol")
    action: str = Field(..., description="BUY, SELL, or HOLD")
    trade_type: str = Field(..., description="LONG or SHORT")
    priority: int = Field(..., description="Priority score 1-100")
    reasoning: str = Field(..., description="Reasoning for this trade decision")


class PortfolioDecisionSchema(BaseModel):
    """AI-generated portfolio decision schema"""

    overall_market_sentiment: str = Field(
        ..., description="Overall market sentiment: BULLISH, BEARISH, or NEUTRAL"
    )
    portfolio_risk_assessment: str = Field(
        ..., description="Assessment of current portfolio risk: LOW, MEDIUM, or HIGH"
    )
    recommended_trades: List[TradeDecision] = Field(
        default_factory=list,
        description="List of recommended trades in priority order (max 3)",
    )
    portfolio_strategy: str = Field(
        ...,
        description="Overall portfolio strategy: AGGRESSIVE_GROWTH, BALANCED, DEFENSIVE, or HOLD",
    )
    risk_warnings: List[str] = Field(
        default_factory=list, description="Any risk warnings or concerns"
    )
    reasoning: str = Field(
        ..., description="Comprehensive reasoning for the portfolio decision"
    )


class PortfolioDecision:
    """Portfolio-level trading decision"""

    def __init__(self):
        self.trades_to_execute: List[Tuple[str, TradeAction, TradeType]] = []
        self.reasoning: str = ""
        self.risk_level: float = 0.0  # 0-1 scale
        self.market_sentiment: str = "neutral"
        self.portfolio_strategy: str = "balanced"
        self.risk_warnings: List[str] = []


class PortfolioDecisionManager:
    """
    AI-powered portfolio-level decision manager that considers all assets holistically.

    This manager:
    1. Collects analysis for all assets in the portfolio
    2. Uses LLM to analyze portfolio state, risk, and market conditions
    3. Makes coordinated trading decisions based on AI reasoning
    4. Provides transparent reasoning for all decisions
    """

    def __init__(self, config: AutoTradingConfig, llm_client=None, signature: Optional[str] = None):
        """
        Initialize portfolio decision manager.

        Args:
            config: Trading configuration
            llm_client: OpenRouter LLM client for portfolio analysis
            signature: Agent signature for prompt injection matching
        """
        self.config = config
        self.llm_client = llm_client
        self.signature = signature
        self.asset_analyses: Dict[str, AssetAnalysis] = {}

    def add_asset_analysis(self, analysis: AssetAnalysis):
        """
        Add analysis for a single asset.

        Args:
            analysis: Asset analysis result
        """
        self.asset_analyses[analysis.symbol] = analysis
        logger.debug(
            f"Added analysis for {analysis.symbol}: "
            f"{analysis.recommended_action.value} {analysis.recommended_trade_type.value}"
        )

    def clear_analyses(self):
        """Clear all asset analyses for a new decision cycle"""
        self.asset_analyses.clear()

    async def make_portfolio_decision(
        self,
        current_positions: Dict[str, Position],
        available_cash: float,
        total_portfolio_value: float,
    ) -> PortfolioDecision:
        """
        Make AI-powered portfolio-level trading decision.

        Args:
            current_positions: Current open positions
            available_cash: Available cash for trading
            total_portfolio_value: Total portfolio value

        Returns:
            PortfolioDecision with AI-coordinated trading actions
        """
        decision = PortfolioDecision()

        if not self.asset_analyses:
            decision.reasoning = "No asset analyses available"
            return decision

        # Calculate basic portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics(
            current_positions, available_cash, total_portfolio_value
        )

        # Use AI to make portfolio decision if available
        if self.llm_client and _PORTFOLIO_AGENT_AVAILABLE:
            try:
                ai_decision = await self._get_ai_portfolio_decision(
                    current_positions,
                    portfolio_metrics,
                    available_cash,
                    total_portfolio_value,
                )
                decision = self._convert_ai_decision(ai_decision, current_positions)
            except Exception as e:
                logger.error(f"Failed to get AI portfolio decision: {e}")
                # Fallback to rule-based decision
                decision = self._make_rule_based_decision(
                    current_positions,
                    portfolio_metrics,
                    available_cash,
                    total_portfolio_value,
                )
        else:
            # Fallback to rule-based decision
            decision = self._make_rule_based_decision(
                current_positions,
                portfolio_metrics,
                available_cash,
                total_portfolio_value,
            )

        return decision

    async def _get_ai_portfolio_decision(
        self,
        current_positions: Dict[str, Position],
        portfolio_metrics: Dict,
        available_cash: float,
        total_portfolio_value: float,
    ) -> PortfolioDecisionSchema:
        """
        Use LLM to analyze portfolio and make trading decisions.

        Returns:
            AI-generated portfolio decision
        """
        if not _PORTFOLIO_AGENT_AVAILABLE:
            raise RuntimeError("No agent framework available for portfolio decision making")

        # Construct comprehensive prompt using prompt module (with signature for injection matching)
        prompt = get_portfolio_prompt(
            current_positions=current_positions,
            portfolio_metrics=portfolio_metrics,
            asset_analyses=self.asset_analyses,
            available_cash=available_cash,
            total_portfolio_value=total_portfolio_value,
            max_positions=self.config.max_positions,
            risk_per_trade=self.config.risk_per_trade,
            signature=self.signature,
        )

        # Create agent with structured output
        agent = Agent(
            model=self.llm_client,
            output_schema=PortfolioDecisionSchema,
            markdown=False,
        )

        # Get AI decision
        response = await agent.arun(prompt)
        ai_decision = response.content

        logger.info(
            f"AI Portfolio Decision: {ai_decision.portfolio_strategy}, "
            f"Sentiment: {ai_decision.overall_market_sentiment}, "
            f"Recommended Trades: {len(ai_decision.recommended_trades)}"
        )
        if ai_decision.recommended_trades:
            logger.debug(f"   Trade details: {[(t.symbol, t.action, t.trade_type) for t in ai_decision.recommended_trades]}")

        return ai_decision

    def _build_portfolio_analysis_prompt(
        self,
        current_positions: Dict[str, Position],
        portfolio_metrics: Dict,
        available_cash: float,
        total_portfolio_value: float,
    ) -> str:
        """
        Build comprehensive prompt for portfolio analysis.
        
        NOTE: This method is deprecated. Use get_portfolio_prompt() from prompts.portfolio_prompt instead.
        This is kept for backward compatibility.
        """
        return get_portfolio_prompt(
            current_positions=current_positions,
            portfolio_metrics=portfolio_metrics,
            asset_analyses=self.asset_analyses,
            available_cash=available_cash,
            total_portfolio_value=total_portfolio_value,
            max_positions=self.config.max_positions,
            risk_per_trade=self.config.risk_per_trade,
        )

    def _build_portfolio_analysis_prompt_old(
        self,
        current_positions: Dict[str, Position],
        portfolio_metrics: Dict,
        available_cash: float,
        total_portfolio_value: float,
    ) -> str:
        """DEPRECATED: Old implementation kept for reference. Use get_portfolio_prompt() instead."""
        # Current time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Portfolio state section
        prompt_parts = [
            "You are an expert portfolio manager for cryptocurrency trading. Analyze the following portfolio state and asset analyses to make coordinated trading decisions.",
            "",
            f"=== ANALYSIS TIME: {current_time} ===",
            "",
            "=== PORTFOLIO STATE ===",
            f"Total Portfolio Value: ${total_portfolio_value:,.2f}",
            f"Available Cash: ${available_cash:,.2f} ({portfolio_metrics['cash_ratio'] * 100:.1f}%)",
            f"Cash in Positions: ${total_portfolio_value - available_cash:,.2f}",
            f"Open Positions: {portfolio_metrics['position_count']}/{self.config.max_positions}",
            f"Risk Per Trade: {self.config.risk_per_trade * 100:.1f}%",
            f"Max Positions Allowed: {self.config.max_positions}",
            "",
        ]

        # Current positions section
        if current_positions:
            prompt_parts.append("=== CURRENT POSITIONS ===")
            for symbol, position in current_positions.items():
                if symbol in self.asset_analyses:
                    current_price = self.asset_analyses[symbol].current_price
                    position_value = abs(position.quantity) * current_price

                    if position.trade_type == TradeType.LONG:
                        unrealized_pnl = (current_price - position.entry_price) * abs(
                            position.quantity
                        )
                    else:
                        unrealized_pnl = (position.entry_price - current_price) * abs(
                            position.quantity
                        )

                    pnl_pct = (
                        (unrealized_pnl / position.notional * 100)
                        if position.notional > 0
                        else 0
                    )
                    concentration = (
                        (position_value / total_portfolio_value * 100)
                        if total_portfolio_value > 0
                        else 0
                    )

                    prompt_parts.extend(
                        [
                            f"\n{symbol}:",
                            f"  Type: {position.trade_type.value.upper()}",
                            f"  Entry Price: ${position.entry_price:,.2f}",
                            f"  Current Price: ${current_price:,.2f}",
                            f"  Quantity: {abs(position.quantity):.4f}",
                            f"  Position Value: ${position_value:,.2f}",
                            f"  Unrealized P&L: ${unrealized_pnl:,.2f} ({pnl_pct:+.2f}%)",
                            f"  Portfolio Concentration: {concentration:.1f}%",
                        ]
                    )
            prompt_parts.append("")
        else:
            prompt_parts.extend(
                [
                    "=== CURRENT POSITIONS ===",
                    "No open positions",
                    "",
                ]
            )

        # Asset analyses section
        prompt_parts.append("=== ASSET ANALYSES ===")
        for symbol, analysis in self.asset_analyses.items():
            indicators = analysis.indicators
            prompt_parts.extend(
                [
                    f"\n{symbol}:",
                    f"  Current Price: ${analysis.current_price:,.2f}",
                    f"  Volume: {indicators.volume:,.0f}",
                    "",
                    "  Technical Indicators:",
                ]
            )

            # MACD
            if indicators.macd is not None and indicators.macd_signal is not None:
                macd_trend = (
                    "BULLISH" if indicators.macd > indicators.macd_signal else "BEARISH"
                )
                prompt_parts.append(
                    f"    - MACD: {indicators.macd:.4f} / Signal: {indicators.macd_signal:.4f} ({macd_trend})"
                )

            # RSI
            if indicators.rsi is not None:
                if indicators.rsi < 30:
                    rsi_status = "OVERSOLD (Potential Buy)"
                elif indicators.rsi > 70:
                    rsi_status = "OVERBOUGHT (Potential Sell)"
                else:
                    rsi_status = "NEUTRAL"
                prompt_parts.append(f"    - RSI: {indicators.rsi:.2f} ({rsi_status})")

            # EMAs
            if indicators.ema_12 is not None and indicators.ema_26 is not None:
                ema_trend = (
                    "BULLISH" if indicators.ema_12 > indicators.ema_26 else "BEARISH"
                )
                prompt_parts.append(
                    f"    - EMA 12/26: ${indicators.ema_12:,.2f} / ${indicators.ema_26:,.2f} ({ema_trend})"
                )

            # Bollinger Bands
            if indicators.bb_upper is not None and indicators.bb_lower is not None:
                if analysis.current_price > indicators.bb_upper:
                    bb_status = "ABOVE UPPER BAND (Overbought)"
                elif analysis.current_price < indicators.bb_lower:
                    bb_status = "BELOW LOWER BAND (Oversold)"
                else:
                    bb_status = "WITHIN BANDS"
                prompt_parts.append(
                    f"    - Bollinger Bands: ${indicators.bb_lower:,.2f} - ${indicators.bb_upper:,.2f} ({bb_status})"
                )

            prompt_parts.append("")
            prompt_parts.append("  Technical Analysis Signal:")
            prompt_parts.append(
                f"    - Action: {analysis.technical_action.value.upper()}"
            )
            if analysis.technical_action != TradeAction.HOLD:
                prompt_parts.append(
                    f"    - Type: {analysis.technical_trade_type.value.upper()}"
                )

            # AI signal if available
            if analysis.ai_action:
                prompt_parts.append("")
                prompt_parts.append("  AI-Enhanced Signal:")
                prompt_parts.append(f"    - Action: {analysis.ai_action.value.upper()}")
                if analysis.ai_action != TradeAction.HOLD:
                    prompt_parts.append(
                        f"    - Type: {analysis.ai_trade_type.value.upper()}"
                    )
                if analysis.ai_confidence:
                    prompt_parts.append(
                        f"    - Confidence: {analysis.ai_confidence:.0f}%"
                    )
                if analysis.ai_reasoning:
                    prompt_parts.append(f"    - Reasoning: {analysis.ai_reasoning}")

            # Current position status
            if symbol in current_positions:
                prompt_parts.append(
                    f"  ⚠️ CURRENTLY HOLDING: {current_positions[symbol].trade_type.value.upper()} position"
                )
            else:
                prompt_parts.append("  ℹ️ No current position")

            prompt_parts.append("")

        # Risk management constraints
        prompt_parts.extend(
            [
                "",
                "=== RISK MANAGEMENT CONSTRAINTS ===",
                f"- Maximum {self.config.max_positions} concurrent positions allowed",
                "- Maximum 3 trades per decision cycle",
                f"- Risk per trade: {self.config.risk_per_trade * 100:.1f}% of available cash",
                "- Avoid single asset concentration >40% of portfolio",
                "- Prioritize closing losing positions if risk is high",
                "- Maintain minimum 10% cash reserve",
                "",
            ]
        )

        # Decision instructions
        prompt_parts.extend(
            [
                "=== YOUR TASK ===",
                "As a professional portfolio manager, analyze:",
                "1. Overall market sentiment across all assets",
                "2. Current portfolio risk level and concentration",
                "3. Individual asset signals (both technical and AI)",
                "4. Correlation and diversification opportunities",
                "5. Risk/reward of each potential trade",
                "",
                "Then provide:",
                "- overall_market_sentiment: BULLISH, BEARISH, or NEUTRAL",
                "- portfolio_risk_assessment: LOW, MEDIUM, or HIGH",
                "- recommended_trades: Up to 3 trades in priority order",
                "  * For each trade: symbol, action (BUY/SELL/HOLD), trade_type (LONG/SHORT), priority (1-100), reasoning",
                "  * Prioritize closing positions (SELL) over opening new ones if risk is high",
                "  * Only recommend BUY if we have room and cash available",
                "- portfolio_strategy: AGGRESSIVE_GROWTH, BALANCED, DEFENSIVE, or HOLD",
                "- risk_warnings: List any concerns (concentration, volatility, etc.)",
                "- reasoning: Comprehensive explanation of your portfolio-level decision",
                "",
                "Important considerations:",
                "- Consider the portfolio as a whole, not just individual assets",
                "- Balance risk and opportunity across all positions",
                "- Prioritize capital preservation when risk is high",
                "- Consider taking profits on winning positions",
                "- Cut losses on losing positions if trend has reversed",
                "- Ensure diversification and avoid over-concentration",
                "",
            ]
        )

        return "\n".join(prompt_parts)

    def _convert_ai_decision(
        self,
        ai_decision: PortfolioDecisionSchema,
        current_positions: Dict[str, Position],
    ) -> PortfolioDecision:
        """Convert AI decision schema to PortfolioDecision"""
        decision = PortfolioDecision()

        # Set metadata
        decision.market_sentiment = ai_decision.overall_market_sentiment.lower()
        decision.portfolio_strategy = ai_decision.portfolio_strategy.lower()
        decision.risk_warnings = ai_decision.risk_warnings
        decision.reasoning = ai_decision.reasoning

        # Map risk assessment to risk level
        risk_map = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}
        decision.risk_level = risk_map.get(
            ai_decision.portfolio_risk_assessment.upper(), 0.6
        )

        # Convert trades
        for trade in ai_decision.recommended_trades:
            try:
                action = TradeAction(trade.action.lower())
                trade_type = TradeType(trade.trade_type.lower())

                # Validate trade
                if action == TradeAction.BUY and trade.symbol in current_positions:
                    logger.warning(
                        f"Skipping BUY for {trade.symbol} - position already exists"
                    )
                    continue

                if action == TradeAction.SELL and trade.symbol not in current_positions:
                    logger.warning(
                        f"Skipping SELL for {trade.symbol} - no position to close"
                    )
                    continue

                if action == TradeAction.SELL and trade.symbol in current_positions:
                    # Verify trade type matches
                    if current_positions[trade.symbol].trade_type != trade_type:
                        logger.warning(
                            f"Skipping SELL for {trade.symbol} - trade type mismatch "
                            f"(have {current_positions[trade.symbol].trade_type.value}, "
                            f"trying to close {trade_type.value})"
                        )
                        continue

                if action != TradeAction.HOLD:
                    decision.trades_to_execute.append(
                        (trade.symbol, action, trade_type)
                    )

            except Exception as e:
                logger.error(
                    f"Failed to convert trade decision for {trade.symbol}: {e}"
                )

        return decision

    def _make_rule_based_decision(
        self,
        current_positions: Dict[str, Position],
        portfolio_metrics: Dict,
        available_cash: float,
        total_portfolio_value: float,
    ) -> PortfolioDecision:
        """Fallback rule-based decision making"""
        decision = PortfolioDecision()

        # Simple rule-based logic
        max_trades = 3
        trades_added = 0

        # Prioritize selling losing positions
        for symbol, position in current_positions.items():
            if trades_added >= max_trades:
                break

            if symbol in self.asset_analyses:
                analysis = self.asset_analyses[symbol]
                current_price = analysis.current_price

                # Calculate P&L
                if position.trade_type == TradeType.LONG:
                    pnl = (current_price - position.entry_price) * abs(
                        position.quantity
                    )
                else:
                    pnl = (position.entry_price - current_price) * abs(
                        position.quantity
                    )

                # Close losing positions if analysis suggests exit
                if pnl < 0 and analysis.recommended_action == TradeAction.SELL:
                    decision.trades_to_execute.append(
                        (symbol, TradeAction.SELL, position.trade_type)
                    )
                    trades_added += 1

        # Add new positions if we have room and strong signals
        for symbol, analysis in self.asset_analyses.items():
            if trades_added >= max_trades:
                break

            if (
                symbol not in current_positions
                and analysis.recommended_action == TradeAction.BUY
            ):
                if portfolio_metrics["position_count"] < self.config.max_positions:
                    decision.trades_to_execute.append(
                        (symbol, TradeAction.BUY, analysis.recommended_trade_type)
                    )
                    trades_added += 1

        decision.reasoning = (
            f"Rule-based decision: {len(decision.trades_to_execute)} trades selected"
        )
        decision.risk_level = portfolio_metrics.get("risk_level", 0.5)

        return decision

    def _calculate_portfolio_metrics(
        self,
        current_positions: Dict[str, Position],
        available_cash: float,
        total_portfolio_value: float,
    ) -> Dict:
        """Calculate basic portfolio metrics"""
        metrics = {
            "position_count": len(current_positions),
            "cash_ratio": (
                available_cash / total_portfolio_value
                if total_portfolio_value > 0
                else 0
            ),
            "risk_level": 0.0,
            "concentration": {},
            "max_concentration": 0.0,
        }

        # Calculate concentration
        for symbol, position in current_positions.items():
            if symbol in self.asset_analyses:
                current_value = (
                    abs(position.quantity) * self.asset_analyses[symbol].current_price
                )
                concentration = (
                    current_value / total_portfolio_value
                    if total_portfolio_value > 0
                    else 0
                )
                metrics["concentration"][symbol] = concentration
                metrics["max_concentration"] = max(
                    metrics["max_concentration"], concentration
                )

        # Calculate risk level
        concentration_risk = metrics["max_concentration"] * 0.4
        cash_risk = (1 - metrics["cash_ratio"]) * 0.3
        position_count_risk = (
            min(metrics["position_count"] / self.config.max_positions, 1.0) * 0.3
        )
        metrics["risk_level"] = concentration_risk + cash_risk + position_count_risk

        return metrics

    def get_portfolio_summary(self) -> str:
        """Get summary of current portfolio analysis"""
        if not self.asset_analyses:
            return "No asset analyses available"

        summary = (
            f"**Portfolio Analysis Summary** ({len(self.asset_analyses)} assets)\n\n"
        )

        for symbol, analysis in self.asset_analyses.items():
            summary += (
                f"**{symbol}:**\n"
                f"- Price: ${analysis.current_price:,.2f}\n"
                f"- Technical Signal: {analysis.technical_action.value.upper()}"
            )
            if analysis.technical_action != TradeAction.HOLD:
                summary += f" ({analysis.technical_trade_type.value.upper()})"
            summary += "\n"

            if analysis.ai_action:
                summary += f"- AI Signal: {analysis.ai_action.value.upper()}"
                if analysis.ai_action != TradeAction.HOLD:
                    summary += f" ({analysis.ai_trade_type.value.upper()})"
                if analysis.ai_confidence:
                    summary += f" - Confidence: {analysis.ai_confidence:.0f}%"
                summary += "\n"

            if analysis.ai_reasoning:
                summary += f"- AI Reasoning: {analysis.ai_reasoning}\n"

            summary += "\n"

        return summary
