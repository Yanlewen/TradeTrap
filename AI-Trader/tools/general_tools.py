import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

def _resolve_runtime_env_path() -> str:
    """Resolve runtime env path from RUNTIME_ENV_PATH in .env file.
    
    Simple strategy:
    1. Read RUNTIME_ENV_PATH from environment (.env file)
    2. If relative path, resolve from project root
    3. Return the path (will be created by write_config_value if needed)
    
    Returns:
        str: Resolved absolute path to runtime env file
    """
    path = os.environ.get("RUNTIME_ENV_PATH")
    
    if not path or not isinstance(path, str) or not path.strip():
        # Fallback to default if not set
        path = "data/.runtime_env.json"
    else:
        path = path.strip()
        # If empty after strip, use default
        if not path:
            path = "data/.runtime_env.json"
    
    # If relative path, resolve from project root
    if not os.path.isabs(path):
        try:
            base_dir = Path(__file__).resolve().parents[2]
            path = str(base_dir / path)
        except Exception as e:
            # Fallback to default if path resolution fails
            base_dir = Path(__file__).resolve().parents[2]
            path = str(base_dir / "data/.runtime_env.json")
    
    # Normalize the path
    try:
        path = os.path.normpath(path)
    except Exception:
        # If normalization fails, use default
        base_dir = Path(__file__).resolve().parents[2]
        path = str(base_dir / "data/.runtime_env.json")
    
    # Validate path is not empty
    if not path or not path.strip():
        base_dir = Path(__file__).resolve().parents[2]
        path = str(base_dir / "data/.runtime_env.json")
    
    # Ensure directory exists
    try:
        path_obj = Path(path)
        if path_obj.parent:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # If directory creation fails, log but continue
        print(f"⚠️  Warning: Failed to create directory for runtime env path: {e}")
    
    return path


def _load_runtime_env() -> dict:
    path = _resolve_runtime_env_path()
    if not path or not isinstance(path, str):
        return {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def get_config_value(key: str, default=None):
    _RUNTIME_ENV = _load_runtime_env()

    if key in _RUNTIME_ENV:
        return _RUNTIME_ENV[key]

    return os.getenv(key, default)


def write_config_value(key: str, value: Any):
    path = _resolve_runtime_env_path()
    if not path or not isinstance(path, str):
        print(f"⚠️  WARNING: Invalid runtime env path, config value '{key}' not persisted")
        return
    _RUNTIME_ENV = _load_runtime_env()
    _RUNTIME_ENV[key] = value
    try:
        # Ensure directory exists before writing
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_RUNTIME_ENV, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Error writing config to {path}: {e}")


def extract_conversation(conversation: dict, output_type: str):
    """Extract information from a conversation payload.

    Args:
        conversation: A mapping that includes 'messages' (list of dicts or objects with attributes).
        output_type: 'final' to return the model's final answer content; 'all' to return the full messages list.

    Returns:
        For 'final': the final assistant content string if found, otherwise None.
        For 'all': the original messages list (or empty list if missing).
    """

    def get_field(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def get_nested(obj, path, default=None):
        current = obj
        for key in path:
            current = get_field(current, key, None)
            if current is None:
                return default
        return current

    messages = get_field(conversation, "messages", []) or []

    if output_type == "all":
        return messages

    if output_type == "final":
        # Prefer the last message with finish_reason == 'stop' and non-empty content.
        for msg in reversed(messages):
            finish_reason = get_nested(msg, ["response_metadata", "finish_reason"])
            content = get_field(msg, "content")
            if finish_reason == "stop" and isinstance(content, str) and content.strip():
                return content

        # Fallback: last AI-like message with non-empty content and not a tool call.
        for msg in reversed(messages):
            content = get_field(msg, "content")
            additional_kwargs = get_field(msg, "additional_kwargs", {}) or {}
            tool_calls = None
            if isinstance(additional_kwargs, dict):
                tool_calls = additional_kwargs.get("tool_calls")
            else:
                tool_calls = getattr(additional_kwargs, "tool_calls", None)

            is_tool_invoke = isinstance(tool_calls, list)
            # Tool messages often have 'tool_call_id' or 'name' (tool name)
            has_tool_call_id = get_field(msg, "tool_call_id") is not None
            tool_name = get_field(msg, "name")
            is_tool_message = has_tool_call_id or isinstance(tool_name, str)

            if not is_tool_invoke and not is_tool_message and isinstance(content, str) and content.strip():
                return content

        return None

    raise ValueError("output_type must be 'final' or 'all'")


def extract_tool_messages(conversation: dict):
    """Return all ToolMessage-like entries from the conversation.

    A ToolMessage is identified heuristically by having either:
      - a non-empty 'tool_call_id', or
      - a string 'name' (tool name) and no 'finish_reason' like normal AI messages

    Supports both dict-based and object-based messages.
    """

    def get_field(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def get_nested(obj, path, default=None):
        current = obj
        for key in path:
            current = get_field(current, key, None)
            if current is None:
                return default
        return current

    messages = get_field(conversation, "messages", []) or []
    tool_messages = []
    for msg in messages:
        tool_call_id = get_field(msg, "tool_call_id")
        name = get_field(msg, "name")
        finish_reason = get_nested(msg, ["response_metadata", "finish_reason"])  # present for AIMessage
        # Treat as ToolMessage if it carries a tool_call_id, or looks like a tool response
        if tool_call_id or (isinstance(name, str) and not finish_reason):
            tool_messages.append(msg)
    return tool_messages


def extract_first_tool_message_content(conversation: dict):
    """Return the content of the first ToolMessage if available, else None."""
    msgs = extract_tool_messages(conversation)
    if not msgs:
        return None

    first = msgs[0]
    if isinstance(first, dict):
        return first.get("content")
    return getattr(first, "content", None)
