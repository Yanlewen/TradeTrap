"""
Prompt injection plugin package.

Exposes helpers for loading prompt injection rules and composing agents
without modifying the core `BaseAgent` implementation.
"""

from .prompt_injection_manager import PromptInjectionManager  # noqa: F401
from .prompt_injection_agent import PromptInjectionAgent  # noqa: F401
from .prompt_injection_agent_hour import PromptInjectionAgentHour  # noqa: F401


