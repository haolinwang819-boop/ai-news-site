"""
Final digest routing rules for the daily AI brief.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Iterable

from .models import PipelineItem


CATEGORY_ORDER = (
    "breakout_products",
    "hot_news",
    "llm",
    "image_video",
    "product_updates",
)

CATEGORY_LIMITS = {
    "breakout_products": int(os.environ.get("DIGEST_BREAKOUT_MAX_ITEMS", "10")),
    "hot_news": int(os.environ.get("DIGEST_HOT_NEWS_MAX_ITEMS", "10")),
    "llm": int(os.environ.get("DIGEST_LLM_MAX_ITEMS", "10")),
    "image_video": int(os.environ.get("DIGEST_IMAGE_VIDEO_MAX_ITEMS", "10")),
    "product_updates": int(os.environ.get("DIGEST_PRODUCT_UPDATES_MAX_ITEMS", "10")),
}

MODEL_KEYWORDS = (
    "chatgpt",
    "claude",
    "codex",
    "deepseek",
    "gemini",
    "glm",
    "gpt",
    "grok",
    "kimi",
    "llama",
    "mistral",
    "model",
    "models",
    "moonshot",
    "openai",
    "qwen",
    "reasoning model",
    "weights",
    "开源模型",
    "模型",
)

MULTIMODAL_KEYWORDS = (
    "audio generation",
    "dall-e",
    "edit images",
    "firefly",
    "flux",
    "image generation",
    "image editing",
    "image model",
    "image-to-video",
    "imagen",
    "jimeng",
    "kling",
    "midjourney",
    "multimodal",
    "nano banana",
    "photoshop",
    "photo editing",
    "runway",
    "seedance",
    "seeddance",
    "sora",
    "stable audio",
    "stable diffusion",
    "udio",
    "veo",
    "vidu",
    "video generation",
    "vision model",
    "可灵",
    "即梦",
    "文生图",
    "文生视频",
    "多模态",
)

AI_SIGNAL_KEYWORDS = (
    "ai",
    "ai-native",
    "ai-powered",
    "artificial intelligence",
    "copilot",
    "developer api",
    "developer apis",
    "foundation model",
    "generative ai",
    "llm",
    "machine learning",
    "neural",
    "openai",
    "agi",
    "robotics",
    "embodied",
    "智能",
    "模型",
    "生成式",
    "人工智能",
    "具身",
    "机器人",
)

WEAK_AI_SIGNAL_KEYWORDS = (
    "agent",
    "agents",
    "assistant",
    "automation",
    "intelligence",
    "model",
    "models",
    "prompt",
    "siri",
)

APPLICATION_CUES = (
    "api",
    "apis",
    "app",
    "apps",
    "assistant",
    "browser",
    "cli",
    "coding agent",
    "contact center",
    "copilot",
    "dashboard",
    "developer tool",
    "developer tools",
    "email",
    "extension",
    "feature",
    "features",
    "healthcare assistant",
    "mobile app",
    "platform",
    "plugin",
    "product",
    "productivity",
    "sdk",
    "service",
    "software",
    "spreadsheet",
    "studio",
    "tool",
    "tools",
    "workspace",
    "writing",
)

NEW_PRODUCT_CUES = (
    "debut",
    "debuts",
    "introduced",
    "introduces",
    "launch",
    "launches",
    "launched",
    "new product",
    "now available",
    "opens beta",
    "public beta",
    "ships",
    "unveiled",
    "unveils",
)

UPDATE_CUES = (
    "adds",
    "added",
    "enhances",
    "enhanced",
    "improves",
    "improved",
    "integrates",
    "integration",
    "new feature",
    "new mode",
    "new workflow",
    "rolls out",
    "support for",
    "supports",
    "update",
    "updated",
    "upgrades",
    "upgraded",
)

HOT_NEWS_CUES = (
    "antitrust",
    "acquisition",
    "acquires",
    "adoption",
    "allowed",
    "allowing",
    "appointed",
    "ban",
    "banned",
    "blacklist",
    "breach",
    "breached",
    "chip",
    "chips",
    "collaboration",
    "contract",
    "customer",
    "customers",
    "delay",
    "delayed",
    "defense",
    "deploy",
    "deployed",
    "deploys",
    "deployment",
    "enterprise",
    "executive",
    "export",
    "founder",
    "funding",
    "government",
    "hack",
    "hacked",
    "hires",
    "hiring",
    "investigation",
    "judge",
    "join forces",
    "joins",
    "joined",
    "joins openai",
    "lawsuit",
    "layoff",
    "market",
    "merger",
    "partnership",
    "policy",
    "pentagon",
    "probe",
    "public sector",
    "regulation",
    "report",
    "resigns",
    "sale",
    "security",
    "security incident",
    "sell",
    "spinoff",
    "trade",
    "valuation",
    "workforce",
    "court",
    "block",
    "blocks",
    "nsa",
)

HEAD_PRODUCT_BRANDS = (
    "adobe",
    "adobe photoshop",
    "character ai",
    "character.ai",
    "cursor",
    "figma",
    "github copilot",
    "grammarly",
    "lovart",
    "notion",
    "notion ai",
    "perplexity",
    "photoshop",
    "replit",
    "superhuman",
    "v0",
    "zoom",
)

VIRAL_DISCOVERY_CUES = (
    "breakout",
    "goes viral",
    "hot new product",
    "new startup",
    "trending product",
    "viral",
    "爆火",
    "刷屏",
)

MAJOR_AI_BRANDS = MODEL_KEYWORDS + MULTIMODAL_KEYWORDS + HEAD_PRODUCT_BRANDS + (
    "anthropic",
    "bytedance",
    "google ai",
    "hugging face",
    "minimax",
    "nvidia",
    "openclaw",
    "stability ai",
    "xai",
)

FRAMEWORK_TOOLING_CUES = (
    "langchain",
    "llama-index",
    "llamaindex",
    "flowise",
    "crewai",
    "autogpt",
)

RELEASE_SIGNAL_PHRASES = (
    "changelog",
    "launches",
    "launched",
    "new feature",
    "new mode",
    "new ways",
    "now available",
    "now can",
    "now supports",
    "public preview",
    "preview",
    "release notes",
    "rolls out",
    "ships",
    "unveils",
    "version ",
)

OPINION_CUES = (
    "analysis",
    "episode",
    "hands-on",
    "my take",
    "opinion",
    "podcast",
    "review",
    "tested",
    "thoughts",
    "what we think",
    "why it matters",
)

RESEARCH_BREAKTHROUGH_CUES = (
    "architecture",
    "benchmark",
    "breakthrough",
    "context window",
    "embodied",
    "inference",
    "kv cache",
    "kvcache",
    "nature",
    "paper",
    "published",
    "reasoning",
    "research",
    "robotics",
    "sota",
    "state of the art",
    "study",
    "training",
    "weights",
    "agi",
    "arxiv",
    "context",
    "论文",
    "研究",
    "突破",
    "超长上下文",
    "具身",
    "机器人",
)

LLM_RESEARCH_CUES = RESEARCH_BREAKTHROUGH_CUES + (
    "autocomplete",
    "claude code",
    "developer workflow",
    "engineering workflow",
    "project structure",
)


def _contains_keyword(text: str, keyword: str) -> bool:
    lowered = text.lower()
    token = keyword.lower()
    if re.search(r"[\u4e00-\u9fff]", token):
        return token in lowered
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
    return bool(pattern.search(lowered))


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if _contains_keyword(text, keyword))


def _item_text(item: PipelineItem) -> str:
    return " ".join(
        str(part)
        for part in (
            item.title,
            item.content,
            item.source,
            item.author_handle or "",
        )
        if part
    ).lower()


def _relevance_text(item: PipelineItem) -> str:
    return " ".join(
        str(part)
        for part in (
            item.title,
            item.content,
            item.author_handle or "",
        )
        if part
    ).lower()


def _is_creator_like(item: PipelineItem) -> bool:
    return (item.source_type or "").lower() in {"creator", "community"}


def _is_editorial_source(item: PipelineItem) -> bool:
    return (item.source_type or "").lower() in {"official", "media", "research"}


def _is_trusted_source(item: PipelineItem) -> bool:
    if _is_editorial_source(item):
        return True
    return (item.platform or "").lower() == "x" and (item.source_type or "").lower() == "official"


def _ai_relevance_score(item: PipelineItem, text: str) -> int:
    relevance_text = _relevance_text(item)
    strong_score = _keyword_score(relevance_text, AI_SIGNAL_KEYWORDS)
    strong_score += _keyword_score(relevance_text, MAJOR_AI_BRANDS)
    weak_score = _keyword_score(relevance_text, WEAK_AI_SIGNAL_KEYWORDS)

    source_text = " ".join(part for part in ((item.source or ""), (item.author_handle or "")) if part).lower()
    source_brand_score = _keyword_score(source_text, MAJOR_AI_BRANDS)
    source_signal_score = _keyword_score(source_text, AI_SIGNAL_KEYWORDS)

    score = strong_score * 2
    score += source_brand_score * 2
    if strong_score > 0 or source_brand_score > 0 or source_signal_score > 0:
        score += weak_score
    if (item.source_type or "").lower() == "official":
        score += source_signal_score * 2
    if "product hunt" in text:
        score += 2
    return score


def _is_multimodal_item(item: PipelineItem, text: str) -> bool:
    return _keyword_score(text, MULTIMODAL_KEYWORDS) > 0


def _is_llm_item(item: PipelineItem, text: str) -> bool:
    return _keyword_score(text, MODEL_KEYWORDS) > 0


def _is_product_hunt_item(item: PipelineItem) -> bool:
    source = (item.source or "").lower()
    return source == "product hunt" or "producthunt.com/products" in (item.url or "").lower()


def _is_ai_application(text: str) -> bool:
    return _keyword_score(text, APPLICATION_CUES) > 0 and (
        _keyword_score(text, AI_SIGNAL_KEYWORDS) > 0 or _keyword_score(text, MAJOR_AI_BRANDS) > 0
    )


def _has_release_signal(text: str) -> bool:
    if _keyword_score(text, NEW_PRODUCT_CUES) > 0 or _keyword_score(text, UPDATE_CUES) > 0:
        return True
    if any(phrase in text for phrase in RELEASE_SIGNAL_PHRASES):
        return True
    if re.search(r"\b(?:v|version)\s?\d+(?:\.\d+){0,2}\b", text):
        return True
    return bool(re.search(r"\b(?:gpt|gemini|claude|qwen|deepseek|llama|glm|grok|codex|sora|veo|kling|runway|seedance)\s*\d+(?:\.\d+){0,2}\b", text))


def _is_opinion_item(text: str) -> bool:
    return _keyword_score(text, OPINION_CUES) > 0


def _is_mixed_roundup_item(item: PipelineItem) -> bool:
    title = (item.title or "").lower()
    content = (item.content or "").lower()
    separator_count = title.count("/") + title.count("｜")
    bullet_count = content.count("·")
    roundup_markers = ("早报", "brief", "roundup", "morning", "early know", "早知道")
    if separator_count >= 2:
        return True
    if bullet_count >= 3 and any(marker in title for marker in roundup_markers):
        return True
    return False


def _is_new_ai_product_launch(item: PipelineItem, text: str) -> bool:
    if not _is_ai_application(text):
        return False
    if _keyword_score(text, HOT_NEWS_CUES) > 0:
        return False
    if _keyword_score(text, HEAD_PRODUCT_BRANDS) > 0 and _keyword_score(text, UPDATE_CUES) > 0:
        return False
    return _keyword_score(text, NEW_PRODUCT_CUES) > 0 or _has_release_signal(text)


def _is_llm_release(item: PipelineItem, text: str) -> bool:
    if not _is_trusted_source(item):
        return False
    if _keyword_score(text, MODEL_KEYWORDS) <= 0:
        return False
    if _keyword_score(text, FRAMEWORK_TOOLING_CUES) > 0:
        return False
    if _has_release_signal(text):
        return True
    if _is_opinion_item(text):
        return False
    return _keyword_score(text, LLM_RESEARCH_CUES) > 0


def _is_multimodal_release(item: PipelineItem, text: str) -> bool:
    if not _is_trusted_source(item):
        return False
    if _keyword_score(text, MULTIMODAL_KEYWORDS) <= 0:
        return False
    if _has_release_signal(text):
        return True
    if _is_opinion_item(text):
        return False
    return _keyword_score(text, RESEARCH_BREAKTHROUGH_CUES) > 0


def _is_breakout_product(item: PipelineItem, text: str) -> bool:
    if _is_product_hunt_item(item):
        direct_ai_score = _keyword_score(text, AI_SIGNAL_KEYWORDS) + _keyword_score(text, MAJOR_AI_BRANDS)
        return direct_ai_score > 0 and _is_ai_application(text)

    if _is_multimodal_release(item, text) or _is_llm_release(item, text):
        return False
    if _is_creator_like(item):
        # Creator content is only allowed here if it clearly points to a newly launched AI application.
        return not _is_opinion_item(text) and _keyword_score(text, VIRAL_DISCOVERY_CUES) > 0 and _is_new_ai_product_launch(item, text)

    if not _is_trusted_source(item):
        return False
    if _keyword_score(text, HEAD_PRODUCT_BRANDS) > 0:
        return False
    if not _is_new_ai_product_launch(item, text):
        return False
    return _keyword_score(text, VIRAL_DISCOVERY_CUES) > 0 or (item.source_type or "").lower() == "official"


def _is_head_product_update(item: PipelineItem, text: str) -> bool:
    if _is_multimodal_release(item, text) or _is_llm_release(item, text):
        return False
    if not _is_trusted_source(item):
        return False
    if _keyword_score(text, HEAD_PRODUCT_BRANDS) <= 0:
        return False
    if _keyword_score(text, HOT_NEWS_CUES) > 0 and _keyword_score(text, UPDATE_CUES) <= 0:
        return False
    has_update_phrase = _keyword_score(text, UPDATE_CUES) > 0 or any(
        phrase in text for phrase in ("changelog", "release notes", "public preview", "preview")
    )
    official_release_surface = (item.source_type or "").lower() == "official" and any(
        token in " ".join(part for part in ((item.url or ""), (item.source_url or ""), text) if part)
        for token in ("changelog", "news", "release", "release-notes", "release_notes", "updates")
    )
    if not has_update_phrase and not official_release_surface:
        return False
    return _is_ai_application(text) or _ai_relevance_score(item, text) > 1


def _is_hot_news_item(item: PipelineItem, text: str) -> bool:
    if not _is_trusted_source(item):
        return False
    if _is_mixed_roundup_item(item):
        return False
    if _is_opinion_item(text):
        return False
    if _is_multimodal_release(item, text) or _is_llm_release(item, text) or _is_head_product_update(item, text):
        return False
    ai_score = _ai_relevance_score(item, text)
    if ai_score < 2:
        return False

    hot_news_score = _keyword_score(text, HOT_NEWS_CUES)
    research_score = _keyword_score(text, RESEARCH_BREAKTHROUGH_CUES)

    if hot_news_score > 0:
        return True

    if research_score > 0:
        return True

    if (item.source_type or "").lower() == "official" and any(
        phrase in text
        for phrase in ("customer", "customers", "enterprise", "deploys", "deployment", "workforce", "adoption")
    ):
        return True

    return False


def route_item_for_digest(item: PipelineItem) -> str | None:
    text = _item_text(item)
    ai_score = _ai_relevance_score(item, text)

    if _is_creator_like(item) and ai_score < 3:
        return None
    if ai_score < 2:
        return None

    if _is_breakout_product(item, text):
        return "breakout_products"
    if _is_creator_like(item):
        return None
    if _is_multimodal_release(item, text):
        return "image_video"
    if _is_llm_release(item, text):
        return "llm"
    if _is_head_product_update(item, text):
        return "product_updates"
    if _is_hot_news_item(item, text):
        return "hot_news"
    return None


def reroute_items_for_digest(items: list[PipelineItem]) -> list[PipelineItem]:
    routed: list[PipelineItem] = []
    for item in items:
        cloned = PipelineItem.from_dict(item.to_dict())
        category = route_item_for_digest(cloned)
        if not category:
            continue
        cloned.category = category
        routed.append(cloned)
    return routed


def item_sort_key(item: PipelineItem):
    published_value = item.published_time or ""
    try:
        published_ts = datetime.fromisoformat(published_value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        published_ts = 0

    breakout_rank = item.product_rank if item.category == "breakout_products" and item.product_rank is not None else 999
    selection_score = item.selection_score if item.selection_score is not None else -1
    return (item.priority, -selection_score, breakout_rank, -published_ts, item.title.lower())
