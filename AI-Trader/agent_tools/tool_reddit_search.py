from typing import Dict, Any, Optional, List
import os
import logging
import json
from pathlib import Path
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load .env file from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(project_root, ".env")
load_dotenv(env_file)
import random
from datetime import datetime, timedelta
import re
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.general_tools import get_config_value

logger = logging.getLogger(__name__)


def _load_injected_news_text(platform: str) -> Optional[str]:
    """Return injected news as a formatted text block for the given platform ("reddit").

    Resolution order: f"{TODAY_DATE}#{SIGNATURE}" -> TODAY_DATE -> "*".
    Returns a single string or None if disabled/missing.
    """
    enabled_value = get_config_value("INJECT_NEWS_ENABLED")
    if str(enabled_value).lower() not in {"1", "true", "yes", "on"}:
        return None

    # prompts/injected_news.json relative to project root (AI-Trader)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    keys: List[str] = []
    if today and signature:
        keys.append(f"{today}#{signature}")
    if today:
        keys.append(today)
    keys.append("*")

    selected = None
    for k in keys:
        if k in data and isinstance(data[k], dict):
            selected = data[k]
            break
    if not selected:
        return None

    entries = selected.get(platform)
    if not isinstance(entries, list) or not entries:
        return None

    blocks = []
    for idx, entry in enumerate(entries, start=1):
        if isinstance(entry, str):
            # Support simple string format for backward compatibility
            blocks.append(f"""
{'='*80}
Injected Reddit News #{idx}
{'='*80}
{entry}
""")
        elif isinstance(entry, dict):
            # Support full object format with all fields
            title = entry.get("title", "")
            selftext = entry.get("selftext", "")
            author = entry.get("author", "[deleted]")
            subreddit = entry.get("subreddit", "")
            score = entry.get("score", 0)
            num_comments = entry.get("num_comments", 0)
            upvote_ratio = entry.get("upvote_ratio", 0.0)
            created_time = entry.get("created_utc", "")
            url = entry.get("url", "")
            
            # Format as Reddit post
            blocks.append(f"""
{'='*80}
Injected Reddit News #{idx}
{'='*80}
URL: {url}
Subreddit: r/{subreddit}
Title: {title}
Author: u/{author}
Score: {score} | Comments: {num_comments} | Upvote Ratio: {upvote_ratio:.1%}
Created: {created_time}
Content: {selftext}
{'='*80}
""")
    if not blocks:
        return None
    return "\n".join(blocks)

def parse_date_to_standard(date_str: str) -> str:
    """
    Convert various date formats to standard format (YYYY-MM-DD HH:MM:SS)
    
    Args:
        date_str: Date string in various formats, such as "2025-10-01T08:19:28+00:00", "4 hours ago", "1 day ago", "May 31, 2025"
        
    Returns:
        Standard format datetime string, such as "2025-10-01 08:19:28"
    """
    if not date_str or date_str == 'unknown':
        return 'unknown'
    
    # Handle relative time formats
    if 'ago' in date_str.lower():
        try:
            now = datetime.now()
            if 'hour' in date_str.lower():
                hours = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(hours=hours)
            elif 'day' in date_str.lower():
                days = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(days=days)
            elif 'week' in date_str.lower():
                weeks = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(weeks=weeks)
            elif 'month' in date_str.lower():
                months = int(re.findall(r'\d+', date_str)[0])
                target_date = now - timedelta(days=months * 30)  # Approximate handling
            else:
                return 'unknown'
            return target_date.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
    
    # Handle ISO 8601 format, such as "2025-10-01T08:19:28+00:00"
    try:
        if 'T' in date_str and ('+' in date_str or 'Z' in date_str or date_str.endswith('00:00')):
            # Remove timezone information, keep only date and time part
            if '+' in date_str:
                date_part = date_str.split('+')[0]
            elif 'Z' in date_str:
                date_part = date_str.replace('Z', '')
            else:
                date_part = date_str
            
            # Parse ISO format
            if '.' in date_part:
                # Handle microseconds part, such as "2025-10-01T08:19:28.123456"
                parsed_date = datetime.strptime(date_part.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            else:
                # Standard ISO format "2025-10-01T08:19:28"
                parsed_date = datetime.strptime(date_part, '%Y-%m-%dT%H:%M:%S')
            return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    
    # Handle other common formats
    try:
        # Handle "May 31, 2025" format
        if ',' in date_str and len(date_str.split()) >= 3:
            parsed_date = datetime.strptime(date_str, '%b %d, %Y')
            return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    
    try:
        # Handle "2025-10-01" format
        if re.match(r'\d{4}-\d{2}-\d{2}$', date_str):
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    
    # If unable to parse, return original string
    return date_str


class RedditSearchTool:
    def __init__(self):
        self.client_id = os.environ.get("REDDIT_CLIENT_ID")
        self.client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        self.user_agent = os.environ.get("REDDIT_USER_AGENT", "SafeTradingAgent/1.0")
        
        if not self.client_id or not self.client_secret:
            logger.warning("Reddit credentials not provided! Will use public API with limited functionality.")
            self.access_token = None
        else:
            self.access_token = self._get_access_token()

    def _get_access_token(self) -> Optional[str]:
        """
        Get Reddit API access token using OAuth2
        """
        try:
            auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
            data = {
                'grant_type': 'client_credentials'
            }
            headers = {
                'User-Agent': self.user_agent
            }
            response = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                auth=auth,
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('access_token')
            else:
                logger.error(f"Failed to get Reddit access token: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting Reddit access token: {e}")
            return None

    def __call__(self, query: str, subreddits: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search Reddit for posts matching the query
        
        Args:
            query: Search query string
            subreddits: List of subreddit names to search in (e.g. ['stocks', 'wallstreetbets'])
            limit: Maximum number of posts to return (default: 5)
        
        Returns:
            List of post information dictionaries
        """
        print(f"Searching Reddit for: {query}")
        
        all_posts = self._reddit_search(query, subreddits, limit)
        
        print(f"Found {len(all_posts)} posts")
        
        if len(all_posts) > limit:
            # Randomly select from results
            all_posts = random.sample(all_posts, limit)
        
        return_content = []
        for post in all_posts:
            print(f"Processing post: {post['title'][:50]}...")
            return_content.append(self._format_post(post))
        
        return return_content

    def _reddit_search(self, query: str, subreddits: Optional[List[str]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search Reddit using the JSON API
        
        Args:
            query: Search query
            subreddits: Optional list of subreddit names
            limit: Maximum results to fetch
        
        Returns:
            List of post data
        """
        # Build search URL
        if subreddits and len(subreddits) > 0:
            # Search in specific subreddits
            subreddit_str = '+'.join(subreddits)
            search_url = f'https://www.reddit.com/r/{subreddit_str}/search.json'
        else:
            # Search all of Reddit
            search_url = 'https://www.reddit.com/search.json'
        
        params = {
            'q': query,
            'limit': min(limit * 2, 100),  # Fetch more to account for filtering
            'sort': 'relevance',
            'restrict_sr': 'on' if subreddits else 'off',
            't': 'all'  # Time filter: all time
        }
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        # Add OAuth token if available
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        try:
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data or 'children' not in data['data']:
                print("⚠️ Reddit API returned invalid data structure")
                return []
            
            posts = []
            today_date = get_config_value("TODAY_DATE")
            
            for child in data['data']['children']:
                post_data = child.get('data', {})
                
                # Extract post information
                created_utc = post_data.get('created_utc', 0)
                created_datetime = datetime.fromtimestamp(created_utc)
                created_str = created_datetime.strftime('%Y-%m-%d %H:%M:%S')
                
                # Filter by date if TODAY_DATE is set
                if today_date:
                    if today_date < created_str:
                        continue  # Skip future posts
                
                post_info = {
                    'id': post_data.get('id'),
                    'title': post_data.get('title', ''),
                    'selftext': post_data.get('selftext', ''),
                    'author': post_data.get('author', '[deleted]'),
                    'subreddit': post_data.get('subreddit', ''),
                    'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                    'score': post_data.get('score', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'created_utc': created_str,
                    'upvote_ratio': post_data.get('upvote_ratio', 0),
                }
                
                posts.append(post_info)
            
            print(f"Found {len(posts)} posts after filtering")
            return posts
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Reddit API request failed: {e}")
            return []
        except ValueError as e:
            print(f"❌ Reddit API response parsing failed: {e}")
            return []
        except Exception as e:
            print(f"❌ Reddit search unknown error: {e}")
            return []

    def _format_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format post data for output
        
        Args:
            post: Raw post data
        
        Returns:
            Formatted post information
        """
        return {
            'url': post['url'],
            'title': post['title'],
            'subreddit': post['subreddit'],
            'author': post['author'],
            'content': post['selftext'][:2000] if post['selftext'] else '[No text content - may be a link post]',
            'score': post['score'],
            'num_comments': post['num_comments'],
            'upvote_ratio': post['upvote_ratio'],
            'created_time': post['created_utc']
        }


mcp = FastMCP("RedditSearch")


@mcp.tool()
def reddit_search(
    query: str, 
    subreddits: Optional[str] = None,
    limit: int = 5
) -> str:
    """
    Search Reddit for posts related to specified query and return structured information.
    
    Args:
        query: Search keywords or terms you want to find on Reddit
        subreddits: Optional comma-separated list of subreddit names to search in 
                   (e.g. "stocks,wallstreetbets,investing"). If not provided, searches all of Reddit.
        limit: Maximum number of posts to return (default: 5, max: 20)
    
    Returns:
        A string containing retrieved Reddit posts with structured content including:
        - URL: Direct link to the Reddit post
        - Title: Post title
        - Subreddit: Which subreddit the post is from
        - Author: Username of the poster
        - Score: Net upvotes (upvotes - downvotes)
        - Comments: Number of comments
        - Upvote Ratio: Percentage of upvotes
        - Created Time: When the post was created
        - Content: Post text content (first 2000 characters)
        
        If search fails, returns corresponding error information.
    """
    try:
        # 1) Injected news short-circuit
        injected = _load_injected_news_text(platform="reddit")
        if injected is not None:
            return injected

        # 2) Fallback to real Reddit search
        # Parse subreddits if provided
        subreddit_list = None
        if subreddits:
            subreddit_list = [s.strip() for s in subreddits.split(',')]
        
        # Limit to reasonable range
        limit = max(1, min(limit, 20))
        
        tool = RedditSearchTool()
        results = tool(query, subreddits=subreddit_list, limit=limit)
        
        # Check if results are empty
        if not results:
            return f"⚠️ Reddit search for '{query}' found no results. May be network issue or API limitation."
        
        # Convert results to string format
        formatted_results = []
        for result in results:
            if 'error' in result:
                formatted_results.append(f"Error: {result['error']}")
            else:
                formatted_results.append(f"""
{'='*80}
URL: {result['url']}
Subreddit: r/{result['subreddit']}
Title: {result['title']}
Author: u/{result['author']}
Score: {result['score']} | Comments: {result['num_comments']} | Upvote Ratio: {result['upvote_ratio']:.1%}
Created: {result['created_time']}
Content: {result['content']}
{'='*80}
""")
        
        if not formatted_results:
            return f"⚠️ Reddit search for '{query}' returned empty results after processing."
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"❌ Reddit search tool execution failed: {str(e)}"


@mcp.tool()
def reddit_get_post(
    post_url: str,
    max_comments: int = 10
) -> str:
    """
    Get detailed information about a specific Reddit post, including top comments.
    
    Args:
        post_url: Full Reddit post URL (e.g. "https://www.reddit.com/r/stocks/comments/abc123/...")
                 or just the post path (e.g. "/r/stocks/comments/abc123/...")
        max_comments: Maximum number of top comments to retrieve (default: 10, max: 50)
    
    Returns:
        A string containing detailed post information including:
        - Post title, author, score, and full content
        - Post statistics (upvotes, comments count, awards, etc.)
        - Top comments with their scores and authors
        - Nested replies to top comments (limited depth)
        
        If retrieval fails, returns corresponding error information.
    """
    try:
        # Parse URL to get the post path
        if post_url.startswith('http'):
            # Extract path from full URL
            import re
            match = re.search(r'reddit\.com(/r/[^/]+/comments/[^/]+/[^/?]*)', post_url)
            if match:
                post_path = match.group(1)
            else:
                return f"❌ Invalid Reddit post URL: {post_url}"
        else:
            post_path = post_url
        
        # Ensure path starts with /
        if not post_path.startswith('/'):
            post_path = '/' + post_path
        
        # Construct JSON API URL
        json_url = f"https://www.reddit.com{post_path}.json"
        
        headers = {
            'User-Agent': 'SafeTradingAgent/1.0'
        }
        
        # Limit comments to reasonable range
        max_comments = max(1, min(max_comments, 50))
        params = {
            'limit': max_comments,
            'depth': 2  # Get replies up to 2 levels deep
        }
        
        print(f"Fetching post details from: {json_url}")
        
        response = requests.get(json_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Reddit returns a list with 2 elements: [post_data, comments_data]
        if not isinstance(data, list) or len(data) < 2:
            return "❌ Invalid response format from Reddit API"
        
        post_listing = data[0]
        comments_listing = data[1]
        
        # Extract post data
        if 'data' not in post_listing or 'children' not in post_listing['data']:
            return "❌ Could not find post data"
        
        post_data = post_listing['data']['children'][0]['data']
        
        # Format post details
        title = post_data.get('title', '')
        author = post_data.get('author', '[deleted]')
        subreddit = post_data.get('subreddit', '')
        score = post_data.get('score', 0)
        upvote_ratio = post_data.get('upvote_ratio', 0)
        num_comments = post_data.get('num_comments', 0)
        created_utc = datetime.fromtimestamp(post_data.get('created_utc', 0))
        created_str = created_utc.strftime('%Y-%m-%d %H:%M:%S')
        selftext = post_data.get('selftext', '')
        url = post_data.get('url', '')
        post_url_full = f"https://www.reddit.com{post_data.get('permalink', '')}"
        
        # Check if it's a link post or text post
        is_self = post_data.get('is_self', False)
        
        result = [f"""
{'='*80}
📝 帖子详情
{'='*80}
标题: {title}
Subreddit: r/{subreddit}
作者: u/{author}
发布时间: {created_str}
URL: {post_url_full}

📊 统计数据:
- 得分: {score}
- 点赞率: {upvote_ratio:.1%}
- 评论数: {num_comments}

"""]
        
        # Add post content
        if is_self and selftext:
            content_preview = selftext[:1500] + "..." if len(selftext) > 1500 else selftext
            result.append(f"📄 帖子内容:\n{content_preview}\n")
        elif not is_self and url:
            result.append(f"🔗 链接: {url}\n")
        
        # Extract comments
        result.append(f"\n{'='*80}\n💬 热门评论 (Top {max_comments})\n{'='*80}\n")
        
        if 'data' in comments_listing and 'children' in comments_listing['data']:
            comments = comments_listing['data']['children']
            comment_count = 0
            
            for comment_obj in comments:
                if comment_obj.get('kind') != 't1':  # t1 is comment type
                    continue
                
                comment_data = comment_obj.get('data', {})
                
                # Skip deleted/removed comments
                if comment_data.get('author') in ['[deleted]', '[removed]']:
                    continue
                
                comment_author = comment_data.get('author', '[deleted]')
                comment_body = comment_data.get('body', '')
                comment_score = comment_data.get('score', 0)
                comment_created = datetime.fromtimestamp(comment_data.get('created_utc', 0))
                comment_time = comment_created.strftime('%Y-%m-%d %H:%M:%S')
                
                comment_count += 1
                
                # Truncate long comments
                body_preview = comment_body[:500] + "..." if len(comment_body) > 500 else comment_body
                
                result.append(f"""
【评论 {comment_count}】 by u/{comment_author} (得分: {comment_score})
时间: {comment_time}
{body_preview}
""")
                
                # Get replies if available
                replies = comment_data.get('replies')
                if replies and isinstance(replies, dict):
                    if 'data' in replies and 'children' in replies['data']:
                        reply_list = replies['data']['children'][:3]  # Only show top 3 replies
                        for reply_obj in reply_list:
                            if reply_obj.get('kind') != 't1':
                                continue
                            
                            reply_data = reply_obj.get('data', {})
                            if reply_data.get('author') in ['[deleted]', '[removed]']:
                                continue
                            
                            reply_author = reply_data.get('author', '[deleted]')
                            reply_body = reply_data.get('body', '')
                            reply_score = reply_data.get('score', 0)
                            
                            reply_preview = reply_body[:300] + "..." if len(reply_body) > 300 else reply_body
                            result.append(f"""  ↳ 回复 by u/{reply_author} (得分: {reply_score})
    {reply_preview}
""")
                
                result.append("─" * 80 + "\n")
                
                if comment_count >= max_comments:
                    break
            
            if comment_count == 0:
                result.append("暂无评论或评论已被删除\n")
        else:
            result.append("无法获取评论数据\n")
        
        result.append(f"\n{'='*80}\n")
        
        return "".join(result)
        
    except requests.exceptions.RequestException as e:
        return f"❌ Failed to fetch post details: {e}"
    except Exception as e:
        return f"❌ Error retrieving post details: {str(e)}"


if __name__ == "__main__":
    # Run with streamable-http, support configuring port through environment variables to avoid conflicts
    port = int(os.getenv("REDDIT_HTTP_PORT", "8005"))
    mcp.run(transport="streamable-http", port=port)

