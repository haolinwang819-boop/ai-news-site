"""
AI资讯采集器配置模板
复制此文件为 config.py 并填入实际配置
"""
import os
from pathlib import Path

from source_catalog import (
    build_instagram_sources,
    build_news_sources,
    build_reddit_sources,
    build_registry_counts,
    build_tool_sources,
    build_wechat_sources,
    build_x_sources,
    build_xiaohongshu_sources,
)


def _load_root_env_file():
    """向上查找工作区根目录的 .env.local，并填充到 os.environ。"""
    for base in Path(__file__).resolve().parents:
        env_path = base / ".env.local"
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]

            os.environ.setdefault(key, value)
        return


_load_root_env_file()


def _safe_source_list(name, builder):
    try:
        return builder()
    except FileNotFoundError as exc:
        print(f"⚠️ Nexttoken source registry unavailable for {name}: {exc}")
        return []


def _safe_registry_counts():
    try:
        return build_registry_counts()
    except FileNotFoundError as exc:
        print(f"⚠️ Nexttoken source registry unavailable: {exc}")
        return {}


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),  # SMTP服务器地址
    "smtp_port": int(os.environ.get("SMTP_PORT", "587")),            # SMTP端口（TLS用587，SSL用465）
    "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() != "false",
    "sender_email": os.environ.get("SMTP_SENDER_EMAIL", "haolin.wang819@gmail.com"),
    "sender_password": os.environ.get("SMTP_SENDER_PASSWORD", ""),
    "recipient_email": os.environ.get("SMTP_RECIPIENT_EMAIL", "haolin.wang@yale.edu"),
}

# X平台API配置（可选）
X_API_CONFIG = {
    "enabled": bool(os.environ.get("X_API_KEY")),
    "api_key": os.environ.get("X_API_KEY", ""),
    "base_url": os.environ.get("X_API_BASE_URL", "https://api.twitterapi.io"),
    "bearer_token": os.environ.get("X_BEARER_TOKEN", ""),
    "timeout_seconds": int(os.environ.get("X_TIMEOUT_SECONDS", "30")),
    "max_tweets_per_user": int(os.environ.get("X_TWEETS_PER_USER", "3")),
    "max_sources": int(os.environ.get("X_MAX_SOURCES", "0")),
    "max_workers": int(os.environ.get("X_MAX_WORKERS", "8")),
    "retry_attempts": int(os.environ.get("X_RETRY_ATTEMPTS", "2")),
    "search_queries": [
        "AI news",
        "GPT",
        "Claude AI",
        "Midjourney",
        "Sora"
    ]
}
X_SOURCES = _safe_source_list("x", build_x_sources)
if X_API_CONFIG["max_sources"] > 0:
    X_SOURCES = X_SOURCES[: X_API_CONFIG["max_sources"]]

NEXTTOKEN_SOURCE_COUNTS = _safe_registry_counts()
INSTAGRAM_SOURCES = _safe_source_list("instagram", build_instagram_sources)
XIAOHONGSHU_SOURCES = _safe_source_list("xiaohongshu", build_xiaohongshu_sources)
WECHAT_SOURCES = _safe_source_list("wechat", build_wechat_sources)
TOOL_SITE_SOURCES = _safe_source_list("tools", build_tool_sources)
NEWS_SITE_SOURCES = _safe_source_list("news", build_news_sources)
REDDIT_SOURCES = _safe_source_list("reddit", build_reddit_sources)
MANUAL_SITE_SOURCES = [
    {
        "source_name": "Anthropic News",
        "source_url": "https://www.anthropic.com/news",
        "platform": "site",
        "source_type": "official",
        "priority_hint": 0,
    },
    {
        "source_name": "Meta AI Blog",
        "source_url": "https://ai.meta.com/blog/",
        "platform": "site",
        "source_type": "official",
        "priority_hint": 0,
    },
]
INSTAGRAM_COOKIE = os.environ.get("INSTAGRAM_COOKIE", "")
INSTAGRAM_CONFIG = {
    "enabled": _env_flag("INSTAGRAM_CRAWLER_ENABLED", bool(INSTAGRAM_COOKIE)),
    "user_agent": os.environ.get("INSTAGRAM_USER_AGENT", "Mozilla/5.0"),
    "cookie": INSTAGRAM_COOKIE,
    "app_id": os.environ.get("INSTAGRAM_APP_ID", "936619743392459"),
    "timeout_seconds": int(os.environ.get("INSTAGRAM_TIMEOUT_SECONDS", "30")),
    "max_items_per_source": int(os.environ.get("INSTAGRAM_ITEMS_PER_SOURCE", "3")),
    "max_sources": int(os.environ.get("INSTAGRAM_MAX_SOURCES", "0")),
    "max_workers": int(os.environ.get("INSTAGRAM_MAX_WORKERS", "1")),
    "request_delay_seconds": float(os.environ.get("INSTAGRAM_REQUEST_DELAY_SECONDS", "8")),
    "retry_attempts": int(os.environ.get("INSTAGRAM_RETRY_ATTEMPTS", "2")),
    "retry_backoff_seconds": float(os.environ.get("INSTAGRAM_RETRY_BACKOFF_SECONDS", "30")),
}
if INSTAGRAM_CONFIG["max_sources"] > 0:
    INSTAGRAM_SOURCES = INSTAGRAM_SOURCES[: INSTAGRAM_CONFIG["max_sources"]]

SITE_SOURCE_LIMIT = int(os.environ.get("SITE_SOURCE_LIMIT", "0"))
SITE_CRAWLER_CONFIG = {
    "enabled": os.environ.get("SITE_CRAWLER_ENABLED", "true").lower() != "false",
    "timeout_seconds": int(os.environ.get("SITE_TIMEOUT_SECONDS", "20")),
    "max_items_per_source": int(os.environ.get("SITE_ITEMS_PER_SOURCE", "3")),
    "max_workers": int(os.environ.get("SITE_MAX_WORKERS", "10")),
    "use_browser": os.environ.get("SITE_USE_BROWSER", "true").lower() != "false",
    "browser_executable_path": os.environ.get(
        "SITE_BROWSER_PATH",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ),
    "wait_after_load_ms": int(os.environ.get("SITE_WAIT_AFTER_LOAD_MS", "2500")),
}
SITE_SOURCES = MANUAL_SITE_SOURCES + TOOL_SITE_SOURCES + NEWS_SITE_SOURCES
if SITE_SOURCE_LIMIT > 0:
    SITE_SOURCES = SITE_SOURCES[:SITE_SOURCE_LIMIT]

# 小红书登录态（后续爬虫接入使用）
XIAOHONGSHU_CONFIG = {
    "enabled": bool(os.environ.get("XIAOHONGSHU_COOKIE")),
    "cookie": os.environ.get("XIAOHONGSHU_COOKIE", ""),
    "user_agent": os.environ.get("XIAOHONGSHU_USER_AGENT", ""),
    "origin": os.environ.get("XIAOHONGSHU_ORIGIN", "https://www.xiaohongshu.com"),
    "referer": os.environ.get("XIAOHONGSHU_REFERER", "https://www.xiaohongshu.com/"),
    "timeout_seconds": int(os.environ.get("XIAOHONGSHU_TIMEOUT_SECONDS", "30")),
    "max_items_per_source": int(os.environ.get("XIAOHONGSHU_ITEMS_PER_SOURCE", "3")),
    "max_sources": int(os.environ.get("XIAOHONGSHU_MAX_SOURCES", "0")),
    "use_browser": os.environ.get("XIAOHONGSHU_USE_BROWSER", "true").lower() != "false",
    "browser_executable_path": os.environ.get(
        "XIAOHONGSHU_BROWSER_PATH",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ),
    "wait_after_load_ms": int(os.environ.get("XIAOHONGSHU_WAIT_AFTER_LOAD_MS", "5000")),
}
if XIAOHONGSHU_CONFIG["max_sources"] > 0:
    XIAOHONGSHU_SOURCES = XIAOHONGSHU_SOURCES[: XIAOHONGSHU_CONFIG["max_sources"]]

WECHAT_CONFIG = {
    "enabled": os.environ.get("WECHAT_CRAWLER_ENABLED", "true").lower() != "false",
    "user_agent": os.environ.get("WECHAT_USER_AGENT", "Mozilla/5.0"),
    "timeout_seconds": int(os.environ.get("WECHAT_TIMEOUT_SECONDS", "30")),
    "max_items_per_source": int(os.environ.get("WECHAT_ITEMS_PER_SOURCE", "3")),
    "max_sources": int(os.environ.get("WECHAT_MAX_SOURCES", "0")),
    "retry_attempts": int(os.environ.get("WECHAT_RETRY_ATTEMPTS", "3")),
    "max_workers": int(os.environ.get("WECHAT_MAX_WORKERS", "6")),
}
if WECHAT_CONFIG["max_sources"] > 0:
    WECHAT_SOURCES = WECHAT_SOURCES[: WECHAT_CONFIG["max_sources"]]

REDDIT_CONFIG = {
    "enabled": os.environ.get("REDDIT_CRAWLER_ENABLED", "true").lower() != "false",
    "user_agent": os.environ.get("REDDIT_USER_AGENT", "Mozilla/5.0 (compatible; ai-news-bot/0.1)"),
    "timeout_seconds": int(os.environ.get("REDDIT_TIMEOUT_SECONDS", "30")),
    "max_workers": int(os.environ.get("REDDIT_MAX_WORKERS", "2")),
}

PRODUCT_HUNT_CONFIG = {
    "enabled": os.environ.get("PRODUCT_HUNT_MODE", "scrape").lower() == "scrape",
    "leaderboard_url": os.environ.get("PRODUCT_HUNT_LEADERBOARD_URL", ""),
    "leaderboard_url_template": os.environ.get(
        "PRODUCT_HUNT_LEADERBOARD_URL_TEMPLATE",
        "https://www.producthunt.com/leaderboard/daily/{year}/{month}/{day}?ref=header_nav",
    ),
    "leaderboard_date": os.environ.get("PRODUCT_HUNT_LEADERBOARD_DATE", ""),
    "top_n": int(os.environ.get("PRODUCT_HUNT_TOP_N", "8")),
    "max_page_items": int(os.environ.get("PRODUCT_HUNT_MAX_PAGE_ITEMS", "20")),
    "priority": int(os.environ.get("PRODUCT_HUNT_PRIORITY", "1")),
    "timeout_seconds": int(os.environ.get("PRODUCT_HUNT_TIMEOUT_SECONDS", "30")),
}

# RSS源配置
RSS_CRAWLER_CONFIG = {
    "timeout_seconds": int(os.environ.get("RSS_TIMEOUT_SECONDS", "20")),
    "max_workers": int(os.environ.get("RSS_MAX_WORKERS", "6")),
}

RSS_SOURCES = [
    # AI News Media
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "priority": 1, "platform": "site", "source_type": "media", "source_url": "https://www.theverge.com/ai-artificial-intelligence"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "priority": 1, "platform": "site", "source_type": "media", "source_url": "https://techcrunch.com/category/artificial-intelligence/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "priority": 1, "platform": "site", "source_type": "media", "source_url": "https://venturebeat.com/ai/"},
    {"name": "Ars Technica AI", "url": "https://arstechnica.com/tag/ai/feed/", "priority": 1, "platform": "site", "source_type": "media", "source_url": "https://arstechnica.com/tag/ai/"},
    # Rundown AI usually doesn't have a public RSS, putting a placeholder or main site for now if crawler supports direct HTML
    # {"name": "Rundown AI", "url": "https://www.therundown.ai/", "priority": 1}, 
    
    # Chinese Media
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "priority": 1, "platform": "site", "source_type": "media", "source_url": "https://www.jiqizhixin.com/"},
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "priority": 1, "platform": "site", "source_type": "media", "source_url": "https://www.qbitai.com/"},
    
    # Official Blogs (Top Priority)
    {"name": "OpenAI", "url": "https://openai.com/blog/rss.xml", "priority": 0, "platform": "site", "source_type": "official", "source_url": "https://openai.com/news/"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "priority": 0, "platform": "site", "source_type": "official", "source_url": "https://blog.google/technology/ai/"},
    {"name": "DeepMind", "url": "https://deepmind.google/blog/rss.xml", "priority": 0, "platform": "site", "source_type": "official", "source_url": "https://deepmind.google/discover/blog/"},
    {"name": "Microsoft AI", "url": "https://news.microsoft.com/source/feed/", "priority": 0, "platform": "site", "source_type": "official", "source_url": "https://news.microsoft.com/source/"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "priority": 0, "platform": "site", "source_type": "official", "source_url": "https://huggingface.co/blog"},
    {"name": "Midjourney", "url": "https://updates.midjourney.com/rss/", "priority": 0, "platform": "site", "source_type": "official", "source_url": "https://updates.midjourney.com/"},
]

# 采集时间范围（小时）
TIME_RANGE_HOURS = 24

# 每个模块最大条目数
MAX_ITEMS_PER_CATEGORY = 10

# 输出设置
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")  # 临时输出目录
