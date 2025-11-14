from typing import Dict, Any, Optional, List
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load .env file from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(project_root, ".env")
load_dotenv(env_file)

X_API_ENDPOINT = "https://api.twitter.com/2/tweets/search/recent"

"""
X search tool with replay-time protection:
- If caller does not pass start_time/end_time, we will constrain the search window
  to the agent's TODAY_DATE (from runtime_env/env):
    start_time = (TODAY_DATE - 7 days)T00:00:00Z
    end_time   = TODAY_DATE T23:59:59Z
- We additionally filter results client-side to ensure created_at is within the window.
"""

# Add project root to import tools.general_tools.get_config_value
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from tools.general_tools import get_config_value

mcp = FastMCP("XSearch")


def _load_injected_news(platform: str) -> Optional[Dict[str, Any]]:
    """Return injected news payload for given platform ("x" or "reddit") if enabled.

    Resolution order for keys: f"{TODAY_DATE}#{SIGNATURE}" -> TODAY_DATE -> "*".
    Returns a dict with "items" shaped like the normal API output, or None if disabled/missing.
    """
    # Feature flag
    enabled_value = get_config_value("INJECT_NEWS_ENABLED")
    if str(enabled_value).lower() not in {"1", "true", "yes", "on"}:
        return None

    # Determine JSON path
    default_path = os.path.join(project_root, "prompts", "injected_news.json")
    path_value = get_config_value("INJECTED_NEWS_PATH", default_path)
    try:
        payload_path = Path(path_value)
        if not payload_path.exists():
            return None
        with payload_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    today = get_config_value("TODAY_DATE") or ""
    signature = get_config_value("SIGNATURE") or ""
    # resolution order
    candidates: List[str] = []
    if today and signature:
        candidates.append(f"{today}#{signature}")
    if today:
        candidates.append(today)
    candidates.append("*")

    selected = None
    for key in candidates:
        if key in data and isinstance(data[key], dict):
            selected = data[key]
            break
    if not selected:
        return None

    entries = selected.get(platform)
    if not isinstance(entries, list):
        return None

    # Normalize to items list similar to API output
    items = []
    for idx, entry in enumerate(entries):
        if isinstance(entry, str):
            # Support simple string format for backward compatibility
            items.append({
                "id": None,
                "text": entry,
                "author_id": None,
                "created_at": None,
                "lang": None,
                "public_metrics": {},
            })
        elif isinstance(entry, dict):
            # Support full object format with all fields
            items.append({
                "id": entry.get("id"),
                "text": entry.get("text", ""),
                "author_id": entry.get("author_id"),
                "created_at": entry.get("created_at"),
                "lang": entry.get("lang", "en"),
                "public_metrics": entry.get("public_metrics", {}),
            })
    return {"items": items, "next_token": None, "result_count": len(items)}

def _fetch_x_search_sync(
    bearer: str,
    query: str,
    max_results: int,
    lang: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    # Derive default window from TODAY_DATE if not provided
    derived_start: Optional[str] = None
    derived_end: Optional[str] = None
    today_str = get_config_value("TODAY_DATE")
    try:
        if today_str and (start_time is None or end_time is None):
            # Detect date format: hourly (YYYY-MM-DD HH:MM:SS) or daily (YYYY-MM-DD)
            if ' ' in today_str or 'T' in today_str:
                # Hourly format: YYYY-MM-DD HH:MM:SS
                today_dt = datetime.strptime(today_str, "%Y-%m-%d %H:%M:%S")
                # Convert to UTC timezone
                today_dt_utc = today_dt.replace(tzinfo=timezone.utc)
                # Set window: start_time = (TODAY_DATE - 7 days), end_time = TODAY_DATE
                window_start = today_dt_utc - timedelta(days=7)
                window_end = today_dt_utc
            else:
                # Daily format: YYYY-MM-DD
                today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
                window_start = datetime.combine(today_dt - timedelta(days=7), datetime.min.time(), tzinfo=timezone.utc)
                window_end = datetime.combine(today_dt, datetime.max.time(), tzinfo=timezone.utc)
            # Twitter expects RFC3339 (e.g., 2025-10-22T23:59:59Z)
            derived_start = window_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            derived_end = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass

    params = {
        "query": query,
        "max_results": max(10, min(max_results, 100)),
        "tweet.fields": "created_at,lang,public_metrics,author_id",
    }
    if lang:
        params["query"] += f" lang:{lang}"
    # apply provided or derived window
    eff_start = start_time or derived_start
    eff_end = end_time or derived_end
    if eff_start:
        params["start_time"] = eff_start
    if eff_end:
        params["end_time"] = eff_end
    if next_token:
        params["next_token"] = next_token

    headers = {"Authorization": f"Bearer {bearer}"}

    try:
        resp = requests.get(X_API_ENDPOINT, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            return {"error": "Rate limited by X API (429)", "items": [], "result_count": 0}
        if resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:1000]}", "items": [], "result_count": 0}
        data = resp.json()
    except requests.RequestException as e:
        return {"error": f"Request error: {e}", "items": [], "result_count": 0}
    except ValueError as e:
        return {"error": f"JSON parse error: {e}", "items": [], "result_count": 0}

    items = data.get("data", [])
    meta = data.get("meta", {})
    normalized = []
    for t in items:
        if not isinstance(t, dict):
            continue
        created_at = t.get("created_at")
        # client-side guard: ensure created_at within [eff_start, eff_end]
        within_window = True
        try:
            if created_at and (eff_start or eff_end):
                # Normalize Z suffix
                ca = created_at.replace("Z", "+00:00")
                ca_dt = datetime.fromisoformat(ca)
                if eff_start:
                    s_dt = datetime.fromisoformat(eff_start.replace("Z", "+00:00"))
                    if ca_dt < s_dt:
                        within_window = False
                if eff_end and within_window:
                    e_dt = datetime.fromisoformat(eff_end.replace("Z", "+00:00"))
                    if ca_dt > e_dt:
                        within_window = False
        except Exception:
            # if parse fails, keep item (be permissive)
            pass
        if not within_window:
            continue
        normalized.append({
            "id": t.get("id"),
            "text": t.get("text", ""),
            "author_id": t.get("author_id"),
            "created_at": created_at,
            "lang": t.get("lang"),
            "public_metrics": t.get("public_metrics", {}),
        })
    return {
        "items": normalized,
        "next_token": meta.get("next_token"),
        "result_count": meta.get("result_count", len(normalized)),
    }


@mcp.tool()
def x_search(
    query: str,
    max_results: int = 20,
    lang: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search recent posts from X (Twitter) using v2 Recent Search API.

    Args:
        query: Search query string (supports X query operators)
        max_results: 10-100
        lang: Optional language filter (adds `lang:xx`)
        start_time: ISO8601 start time
        end_time: ISO8601 end time
        next_token: Pagination token

    Returns: Dict with items, next_token, result_count. May include error.
    """
    # 1) Try injected news first (disables external API when enabled)
    injected = _load_injected_news(platform="x")
    if injected is not None:
        return injected

    # 2) Fallback to real API
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        return {"error": "X_BEARER_TOKEN not set", "items": [], "result_count": 0}
    if not query or not isinstance(query, str):
        return {"error": "query must be a non-empty string", "items": [], "result_count": 0}

    bounded = max(10, min(int(max_results), 100))
    try:
        return _fetch_x_search_sync(
            bearer=bearer,
            query=query,
            max_results=bounded,
            lang=lang,
            start_time=start_time,
            end_time=end_time,
            next_token=next_token,
        )
    except Exception as e:
        return {"error": f"X search failed: {e}", "items": [], "result_count": 0}


if __name__ == "__main__":
    port = int(os.getenv("X_HTTP_PORT", "8004"))
    mcp.run(transport="streamable-http", port=port)


