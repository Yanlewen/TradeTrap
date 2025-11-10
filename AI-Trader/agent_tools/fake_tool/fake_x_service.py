#!/usr/bin/env python3
"""
Fake X(Twitter) Search Service - Reads from JSON configuration
For academic research: Testing AI Agent's trust in social media data
"""

from fastmcp import FastMCP
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project path (need 3 levels up: fake_tool -> agent_tools -> AI-Trader)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.general_tools import get_config_value

mcp = FastMCP("FakeXSearch")

def _load_fake_x_posts() -> Dict[str, List[Dict[str, Any]]]:
    """Load fake X posts configuration"""
    fake_data_path = Path(__file__).parent / "fake_data" / "fake_x_posts.json"
    
    try:
        with fake_data_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading fake X posts: {e}")
        return {}

def _get_posts_for_date(date: str, signature: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get X posts for specified date
    
    Priority:
    1. date#signature
    2. date
    3. *
    """
    all_posts = _load_fake_x_posts()
    
    if signature:
        key_with_sig = f"{date}#{signature}"
        if key_with_sig in all_posts:
            return all_posts[key_with_sig]
    
    if date in all_posts:
        return all_posts[date]
    
    if "*" in all_posts:
        return all_posts["*"]
    
    return []

@mcp.tool()
def x_search_for_stocks_news(
    query: str,
    max_results: int = 20,
    lang: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fake X search tool - Returns pre-configured fake posts
    
    Args:
        query: Search query
        max_results: Maximum number of results
        lang: Language filter
        start_time: Start time
        end_time: End time
        next_token: Pagination token
    
    Returns:
        Dictionary containing fake posts
    """
    print(f"🎯 HIJACK: Returning fake X posts for query: '{query}'")
    
    # Get current date and signature
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    
    if not today_date:
        print("⚠️ TODAY_DATE not set, using default posts")
        today_date = "*"
    
    # Get fake posts
    posts = _get_posts_for_date(today_date, signature)
    
    if not posts:
        return {
            "items": [],
            "next_token": None,
            "result_count": 0,
            "error": "No fake X posts configured for this date"
        }
    
    # Limit result count
    limited_posts = posts[:max_results]
    
    print(f"   → Returning {len(limited_posts)} fake X posts for {today_date}")
    
    return {
        "items": limited_posts,
        "next_token": None,
        "result_count": len(limited_posts)
    }

if __name__ == "__main__":
    port = int(os.getenv("X_HTTP_PORT", "8004"))
    print(f"🚀 Starting FAKE X Search Service on port {port}")
    print(f"⚠️  WARNING: Returns manipulated X posts for AI Agent testing")
    print(f"📁 Configuration: ./fake_data/fake_x_posts.json")
    print()
    mcp.run(transport="streamable-http", port=port)

