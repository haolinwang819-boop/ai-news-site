"""
官方来源覆盖层。

Nexttoken 保留原始入口站点；这里补充真正适合资讯采集的 news / blog / changelog 页面。
"""
from __future__ import annotations


SOURCE_OVERRIDES = {
    "Gemini": {
        "content_url": "https://blog.google/products-and-platforms/products/gemini/",
        "page_mode": "listing",
    },
    "ChatGPT": {
        "content_url": "https://openai.com/news/",
        "feed_url": "https://openai.com/blog/rss.xml",
        "feed_only": True,
        "title_filters": ["chatgpt"],
    },
    "Claude": {
        "content_url": "https://support.claude.com/en/articles/12138966-release-notes",
        "page_mode": "changelog",
    },
    "Perplexity": {
        "content_url": "https://www.perplexity.ai/hub",
        "page_mode": "listing",
        "browser_fallback": True,
    },
    "DeepSeek": {
        "content_url": "https://api-docs.deepseek.com/updates/",
        "page_mode": "changelog",
    },
    "Mistral": {
        "content_url": "https://mistral.ai/news/",
        "page_mode": "listing",
    },
    "Mistral Chat": {
        "content_url": "https://mistral.ai/news/",
        "page_mode": "listing",
    },
    "GitHub Copilot": {
        "content_url": "https://github.blog/changelog/label/copilot/",
        "page_mode": "listing",
        "title_filters": ["copilot"],
    },
    "Notion AI": {
        "content_url": "https://www.notion.com/releases",
        "page_mode": "listing",
    },
    "LangChain": {
        "content_url": "https://changelog.langchain.com/",
        "page_mode": "listing",
    },
    "LlamaIndex": {
        "content_url": "https://developers.llamaindex.ai/python/framework/changelog/",
        "page_mode": "changelog",
    },
    "Runway": {
        "content_url": "https://runwayml.com/changelog",
        "page_mode": "listing",
        "browser_fallback": True,
    },
    "Midjourney": {
        "content_url": "https://updates.midjourney.com/",
        "feed_url": "https://updates.midjourney.com/rss/",
    },
    "OpenAI Blog": {
        "content_url": "https://openai.com/news/",
        "feed_url": "https://openai.com/news/rss.xml",
        "feed_only": True,
    },
    "DALL·E 3": {
        "content_url": "https://openai.com/news/",
        "feed_url": "https://openai.com/news/rss.xml",
        "feed_only": True,
        "title_filters": ["dall-e", "dall·e"],
    },
    "Google AI Blog": {
        "content_url": "https://blog.google/products-and-platforms/products/gemini/",
        "page_mode": "listing",
    },
    "Microsoft Research Blog": {
        "content_url": "https://news.microsoft.com/source/",
        "feed_url": "https://news.microsoft.com/source/feed/",
    },
    "ChatPPT": {
        "content_url": "https://chatppt.com/",
    },
    "ProWritingAid": {
        "content_url": "https://prowritingaid.com/blog",
        "page_mode": "listing",
    },
    "LanguageTool": {
        "content_url": "https://languagetool.org/insights/",
        "page_mode": "listing",
    },
    "Consensus": {
        "content_url": "https://help.consensus.app/en/articles/11117007-new-in-consensus-july-2025-product-updates",
        "page_mode": "changelog",
        "browser_fallback": True,
    },
    "Scholarcy": {
        "content_url": "https://www.scholarcy.com/new/",
        "page_mode": "listing",
        "browser_fallback": True,
    },
    "Canva AI": {
        "content_url": "https://www.canva.dev/blog/",
        "page_mode": "listing",
        "prefer_browser": True,
        "title_filters": ["ai", "magic", "studio", "code", "create"],
    },
    "Figma AI": {
        "content_url": "https://www.figma.com/release-notes/",
        "page_mode": "listing",
        "title_filters": ["ai", "figma make", "figjam ai", "buzz"],
    },
    "Stable Audio": {
        "content_url": "https://stability.ai/news",
        "page_mode": "listing",
        "title_filters": ["audio", "music", "stable audio"],
    },
    "D-ID": {
        "content_url": "https://www.d-id.com/blog/",
        "page_mode": "listing",
    },
    "FocoDesign": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Agaoding.com%2Farticle+AI+OR+%E7%A8%BF%E5%AE%9AAI&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans",
        "feed_only": True,
        "title_filters": ["更新", "公告", "ai"],
    },
    "Riffusion": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Aproducer.ai+Riffusion&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
        "title_filters": ["update", "launch", "release", "news"],
    },
    "Make.com": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Amake.com%2Fen+%22What%E2%80%99s+New+at+Make%22+OR+Introducing+AI&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
        "title_filters": ["what’s new", "what's new", "introducing", "release", "update", "agent"],
    },
    "Rowsy": {
        "content_url": "https://rows.com/docs/whats-new-changelog",
        "page_mode": "listing",
    },
    "StarCoder": {
        "content_url": "https://github.com/bigcode-project/starcoder/releases",
        "feed_url": "https://github.com/bigcode-project/starcoder/releases.atom",
        "feed_only": True,
        "title_filters": ["starcoder"],
    },
    "KDnuggets": {
        "content_url": "https://www.kdnuggets.com/",
        "feed_url": "https://www.kdnuggets.com/feed",
        "feed_only": True,
    },
    "中国信通院": {
        "content_url": "https://gma.caict.ac.cn/plat/news/",
    },
    "极客公园": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Ageekpark.net+%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans",
        "feed_only": True,
    },
    "Datanami": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Ahpcwire.com%2Fbigdatawire+AI&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
    },
    "IEEE Xplore": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Aieeexplore.ieee.org+artificial+intelligence&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
    },
    "ACM Digital Library": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Adl.acm.org+artificial+intelligence&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
    },
    "theinformation": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Atheinformation.com+AI&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
    },
    "techinasia": {
        "feed_url": "https://news.google.com/rss/search?q=site%3Atechinasia.com+AI&hl=en-US&gl=US&ceid=US%3Aen",
        "feed_only": True,
    },
}


def apply_source_overrides(source: dict) -> dict:
    overridden = dict(source)
    patch = SOURCE_OVERRIDES.get(overridden.get("source_name") or overridden.get("name"))
    if patch:
        overridden.update(patch)
    return overridden
