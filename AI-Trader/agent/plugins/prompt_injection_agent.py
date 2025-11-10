"""
Prompt injection aware agent that composes the existing `BaseAgent`.

This implementation overrides `run_trading_session` to inject additional
messages after the system prompt is constructed but before the reasoning
loop begins, without requiring any changes to `BaseAgent` itself.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from langchain.agents import create_agent

from agent.base_agent.base_agent import BaseAgent
from prompts.agent_prompt import STOP_SIGNAL, get_agent_system_prompt
from tools.general_tools import (
    extract_conversation,
    extract_tool_messages,
    write_config_value,
)

from .prompt_injection_manager import InjectionContext, PromptInjectionManager


class PromptInjectionAgent(BaseAgent):
    """
    `BaseAgent` drop-in replacement that injects additional messages from
    prompt-injection rules before delegating to the standard trading loop.
    """

    def __init__(
        self,
        signature: str,
        basemodel: str,
        *,
        injection_manager: Optional[PromptInjectionManager] = None,
        prompt_config_path: Optional[str | Path] = None,
        **base_kwargs,
    ) -> None:
        super().__init__(signature=signature, basemodel=basemodel, **base_kwargs)

        if injection_manager is not None:
            self.injection_manager = injection_manager
        else:
            if prompt_config_path is None:
                prompt_config_path = Path(__file__).resolve().parents[2] / "prompts" / "prompt_injections.json"
            self.injection_manager = PromptInjectionManager(config_path=prompt_config_path)

    async def run_trading_session(self, today_date: str) -> None:  # noqa: D401
        """
        Run a trading session with prompt injection support.
        """
        print(f"📈 Starting trading session with injections: {today_date}")

        # Set up logging (same as BaseAgent)
        log_file = self._setup_logging(today_date)
        write_config_value("LOG_FILE", log_file)

        # Update system prompt and agent
        self.agent = create_agent(
            self.model,
            tools=self.tools,
            system_prompt=get_agent_system_prompt(today_date, self.signature, self.market, self.stock_symbols),
        )

        # Initial user query
        user_query = [{"role": "user", "content": f"Please analyze and update today's ({today_date}) positions."}]
        message: List[Dict[str, str]] = user_query.copy()

        # Log initial message
        self._log_message(log_file, user_query)

        # Inject additional prompts (if any) before the reasoning loop
        injections = self._get_pre_decision_injections(today_date)
        if injections:
            message.extend(injections)
            for injection in injections:
                self._log_message(log_file, injection)

        # Trading loop (copied from BaseAgent)
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"🔄 Step {current_step}/{self.max_steps}")

            try:
                response = await self._ainvoke_with_retry(message)
                agent_response = extract_conversation(response, "final")

                if STOP_SIGNAL in agent_response:
                    print("✅ Received stop signal, trading session ended")
                    print(agent_response)
                    self._log_message(log_file, [{"role": "assistant", "content": agent_response}])
                    break

                tool_msgs = extract_tool_messages(response)
                tool_response = "\n".join([msg.content for msg in tool_msgs])

                new_messages = [
                    {"role": "assistant", "content": agent_response},
                    {"role": "user", "content": f"Tool results: {tool_response}"},
                ]

                message.extend(new_messages)
                self._log_message(log_file, new_messages[0])
                self._log_message(log_file, new_messages[1])

            except Exception as exc:
                print(f"❌ Trading session error: {str(exc)}")
                print(f"Error details: {exc}")
                raise

        await self._handle_trading_result(today_date)

    def _get_pre_decision_injections(self, today_date: str) -> List[Dict[str, str]]:
        context = InjectionContext(
            stage="pre_decision",
            signature=self.signature,
            trading_date=today_date,
            current_dt=self._parse_trading_datetime(today_date),
        )
        return self.injection_manager.get_injections(context)

    @staticmethod
    def _parse_trading_datetime(value: str) -> Optional[datetime]:
        formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None


