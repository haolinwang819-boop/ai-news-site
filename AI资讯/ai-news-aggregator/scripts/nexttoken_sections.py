"""
Shared NextToken section definitions and helpers.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


SECTION_DEFS = (
    {
        "id": "breakout",
        "label": "AI Breakout Products",
        "short_label": "Breakout",
        "cn_label": "AI黑马产品",
        "description": "Fresh AI-native applications that feel genuinely new, not routine feature updates.",
        "source_categories": ("breakout_products",),
        "accent": "cyan",
    },
    {
        "id": "hot-news",
        "label": "AI Hot News",
        "short_label": "Hot News",
        "cn_label": "AI热点资讯",
        "description": "Market-moving AI stories, policy shocks, acquisitions, funding, legal action, and company moves.",
        "source_categories": ("hot_news",),
        "accent": "gold",
    },
    {
        "id": "models-frontier",
        "label": "AI Models Frontier",
        "short_label": "Models Frontier",
        "cn_label": "AI基模与多模态",
        "description": "Foundation model launches, multimodal updates, and capability leaps across text, image, audio, and video.",
        "source_categories": ("llm", "image_video"),
        "accent": "violet",
    },
    {
        "id": "product-updates",
        "label": "Top AI Product Updates",
        "short_label": "Product Updates",
        "cn_label": "AI热门产品更新",
        "description": "What the most important AI products shipped next, from workflow upgrades to new modes and integrations.",
        "source_categories": ("product_updates",),
        "accent": "lime",
    },
)

RAW_CATEGORY_ORDER = (
    "breakout_products",
    "hot_news",
    "llm",
    "image_video",
    "product_updates",
)

SECTION_BY_ID = {section["id"]: section for section in SECTION_DEFS}
ALL_SECTION_IDS = tuple(section["id"] for section in SECTION_DEFS)
DIGEST_CATEGORY_TO_SECTION_ID = {
    source_category: section["id"]
    for section in SECTION_DEFS
    for source_category in section["source_categories"]
}

_ALIASES = {
    "all": "all",
    "all modules": "all",
    "all_sections": "all",
    "all-sections": "all",
    "full brief": "all",
    "full-brief": "all",
    "full_brief": "all",
    "全部订阅": "all",
}

for section in SECTION_DEFS:
    section_id = section["id"]
    alias_candidates = {
        section_id,
        section_id.replace("-", "_"),
        section["label"],
        section["short_label"],
        section["cn_label"],
        *section["source_categories"],
    }
    for candidate in alias_candidates:
        normalized = str(candidate or "").strip().lower()
        if normalized:
            _ALIASES[normalized] = section_id

_ALIASES.update(
    {
        "breakout ai products": "breakout",
        "ai breakout products": "breakout",
        "ai breakouts": "breakout",
        "ai hot news": "hot-news",
        "hot news": "hot-news",
        "ai models frontier": "models-frontier",
        "models frontier": "models-frontier",
        "ai foundation models": "models-frontier",
        "ai multimodal": "models-frontier",
        "foundation models": "models-frontier",
        "multimodal": "models-frontier",
        "ai基模或多模态": "models-frontier",
        "top ai product updates": "product-updates",
        "product updates": "product-updates",
        "ai热门产品更新": "product-updates",
    }
)


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.min
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min


def _sort_timestamp(item: dict[str, Any]) -> float:
    dt = _parse_datetime(str(item.get("published_time") or ""))
    if dt == datetime.min:
        return 0.0
    try:
        return dt.timestamp()
    except (OverflowError, OSError, ValueError):
        return 0.0


def canonical_section_id(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    normalized = normalized.replace("—", "-")
    return _ALIASES.get(normalized)


def normalize_section_ids(section_ids: list[str] | tuple[str, ...] | None) -> list[str]:
    if not section_ids:
        return list(ALL_SECTION_IDS)

    canonical_ids = []
    for value in section_ids:
        canonical = canonical_section_id(value)
        if not canonical:
            continue
        if canonical == "all":
            return list(ALL_SECTION_IDS)
        if canonical not in canonical_ids:
            canonical_ids.append(canonical)

    if not canonical_ids:
        return list(ALL_SECTION_IDS)

    ordered = [section_id for section_id in ALL_SECTION_IDS if section_id in canonical_ids]
    return ordered or list(ALL_SECTION_IDS)


def section_labels(section_ids: list[str] | tuple[str, ...] | None) -> list[str]:
    return [SECTION_BY_ID[section_id]["label"] for section_id in normalize_section_ids(section_ids)]


def digest_categories_for_sections(section_ids: list[str] | tuple[str, ...] | None) -> list[str]:
    categories: list[str] = []
    for section_id in normalize_section_ids(section_ids):
        section = SECTION_BY_ID[section_id]
        for category in section["source_categories"]:
            if category not in categories:
                categories.append(category)
    return categories


def merge_section_items(digest: dict[str, Any], section_def: dict[str, Any]) -> list[dict[str, Any]]:
    categories = digest.get("categories") or {}
    merged_items: list[dict[str, Any]] = []
    for source_category in section_def["source_categories"]:
        merged_items.extend(deepcopy(categories.get(source_category) or []))
    merged_items.sort(key=_sort_timestamp, reverse=True)
    return merged_items


def iter_display_sections(digest: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_def in SECTION_DEFS:
        sections.append(
            {
                "id": section_def["id"],
                "label": section_def["label"],
                "shortLabel": section_def["short_label"],
                "cnLabel": section_def["cn_label"],
                "description": section_def["description"],
                "accent": section_def["accent"],
                "sourceCategories": list(section_def["source_categories"]),
                "items": merge_section_items(digest, section_def),
            }
        )
    return sections


def filter_digest_by_sections(digest: dict[str, Any], section_ids: list[str] | tuple[str, ...] | None) -> dict[str, Any]:
    selected_categories = set(digest_categories_for_sections(section_ids))
    categories = digest.get("categories") or {}
    filtered_categories = {
        category: deepcopy(categories.get(category) or []) if category in selected_categories else []
        for category in RAW_CATEGORY_ORDER
    }

    filtered_digest = deepcopy(digest)
    filtered_digest["categories"] = filtered_categories
    filtered_digest["selected_sections"] = normalize_section_ids(section_ids)
    filtered_digest["total_count"] = sum(len(items) for items in filtered_categories.values())
    return filtered_digest
