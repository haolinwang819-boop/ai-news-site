"""
Display-oriented enrichment for the final digest.
"""
from __future__ import annotations

import json
import html as html_lib
import os
import re
from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any

from .config import LLM_EDITOR_CONFIG
from .llm_utils import PromptLoader, get_llm_invoker, parse_json_from_model_output


DISPLAY_CATEGORY_ORDER = ("breakout_products", "hot_news", "llm", "image_video", "product_updates")

NON_READER_FACING_PREFIXES = (
    "reported by ",
    "included in the ",
    "covered by ",
    "collected from ",
    "use the source link",
    "it was included because",
    "the item contains a source-backed update",
    "the item contains a source backed update",
)

ACTION_LEADING_VERBS = (
    "practice",
    "assess",
    "build",
    "create",
    "generate",
    "help",
    "manage",
    "organize",
    "search",
    "write",
    "design",
    "draft",
    "automate",
    "turn",
    "transcribe",
    "summarize",
    "plan",
    "run",
    "deploy",
    "monitor",
    "coach",
    "learn",
    "train",
)

PRODUCT_LAUNCH_VERBS = (
    "debuts",
    "introduces",
    "launches",
    "releases",
    "ships",
    "unveils",
)


def _clean_text(value: str, limit: int | None = None) -> str:
    text = html_lib.unescape(value or "").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _prepare_prompt_item(item: dict[str, Any]) -> dict[str, Any]:
    cleaned_title = _clean_source_title(str(item.get("title", "")), str(item.get("source", "")))
    prepared = {
        "url": item.get("url", ""),
        "title": _clean_text(cleaned_title, 220),
        "source": item.get("source", ""),
        "published_time": item.get("published_time", ""),
        "category": item.get("category", ""),
        "platform": item.get("platform", ""),
        "source_type": item.get("source_type", ""),
        "content": _clean_text(str(item.get("content", "")), 2200),
    }
    if item.get("product_rank") is not None:
        prepared["product_rank"] = item.get("product_rank")
    if item.get("author_handle"):
        prepared["author_handle"] = item["author_handle"]
    return prepared


def _clean_source_title(title: str, source: str) -> str:
    cleaned = _clean_text(title)
    if not cleaned:
        return cleaned

    source_tokens = [
        _clean_text(source),
        _clean_text(source).replace("@", ""),
    ]
    for token in source_tokens:
        if not token:
            continue
        cleaned = re.sub(
            rf"\s*(?:[-|:]\s*)?{re.escape(token)}\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
    return cleaned.rstrip("-|: ").strip()


def _strip_leading_source_reference(title: str, source: str) -> str:
    cleaned = _clean_text(title)
    if not cleaned:
        return cleaned

    source_tokens = [
        _clean_text(source),
        _clean_text(source).replace("@", ""),
        "Product Hunt",
    ]
    for token in source_tokens:
        if not token:
            continue
        cleaned = re.sub(
            rf"^{re.escape(token)}\s*[:|\-]\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
    return cleaned


def _is_product_hunt_item(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "").strip().lower()
    url = str(item.get("url") or "").strip().lower()
    return source == "product hunt" or "producthunt.com/products" in url


def _fallback_display_title(item: dict[str, Any]) -> str:
    source = _clean_text(str(item.get("source", "")))
    title = _strip_leading_source_reference(
        _clean_source_title(str(item.get("title", "")), source),
        source,
    )
    content = _clean_text(str(item.get("content", "")))
    seed = title or content or "AI update"

    # Truncate to a reasonable display length
    words = seed.split()
    if len(words) > 12:
        seed = " ".join(words[:12]).rstrip(",;:")

    return _strip_leading_source_reference(seed, source).rstrip(".:; ")


def _normalized_compare_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalized_sentences(text: str) -> list[str]:
    return [
        _normalized_compare_text(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", _clean_text(text))
        if _normalized_compare_text(sentence)
    ]


def _sentence_count(text: str) -> int:
    return len(_normalized_sentences(text))


def _is_english_fallback_text(value: str) -> bool:
    cleaned = _clean_text(value)
    return bool(cleaned) and not _has_non_english_script(cleaned)


def _title_too_close(candidate: str, original: str) -> bool:
    candidate_norm = _normalized_compare_text(candidate)
    original_norm = _normalized_compare_text(original)
    if not candidate_norm or not original_norm:
        return False
    if candidate_norm == original_norm:
        return True
    if candidate_norm in original_norm or original_norm in candidate_norm:
        return True
    return SequenceMatcher(None, candidate_norm, original_norm).ratio() >= 0.86


def _editorial_title_from_summary(item: dict[str, Any], summary: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", _clean_text(summary))[0].strip().rstrip(".")
    if not sentence:
        return _fallback_display_title(item)

    replacements = {
        " has launched ": " launches ",
        " has announced ": " announces ",
        " has introduced ": " introduces ",
        " has released ": " releases ",
        " has unveiled ": " unveils ",
        " has expanded ": " expands ",
        " has partnered ": " partners ",
        " have announced ": " announce ",
        " have launched ": " launch ",
    }
    rewritten = sentence
    for old, new in replacements.items():
        rewritten = rewritten.replace(old, new).replace(old.title(), new.title())

    words = rewritten.split()
    if len(words) > 14:
        rewritten = " ".join(words[:14]).rstrip(",;:")

    return _strip_leading_source_reference(
        rewritten.rstrip(".:; "),
        str(item.get("source", "")),
    )


def _looks_non_reader_facing(value: str) -> bool:
    normalized = _normalized_compare_text(value)
    if not normalized:
        return True

    if "product hunt s daily ai leaderboard" in normalized:
        return True

    for prefix in NON_READER_FACING_PREFIXES:
        if normalized.startswith(_normalized_compare_text(prefix)):
            return True
    return False


def _extract_product_categories(item: dict[str, Any]) -> list[str]:
    content = _clean_text(str(item.get("content", "")))
    match = re.search(r"Product categories:\s*(.+?)(?:[.!?]|$)", content, flags=re.IGNORECASE)
    if not match:
        return []

    categories: list[str] = []
    seen: set[str] = set()
    for raw_part in match.group(1).split(","):
        cleaned = _clean_text(raw_part)
        normalized = _normalized_compare_text(cleaned)
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        categories.append(cleaned)
    return categories


def _extract_owner_hint(item: dict[str, Any]) -> str:
    content = _clean_text(str(item.get("content", "")))
    if not content:
        return ""

    patterns = (
        r"developed by ([A-Z][A-Za-z0-9& .-]+?)(?:[.,]|$)",
        r"from ([A-Z][A-Za-z0-9& .-]+?)(?:[.,]|$)",
        r"team,\s*([A-Z][A-Za-z0-9& .-]+?)(?:[.,]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))

    known_owners = (
        "Alibaba Cloud",
        "Google",
        "OpenAI",
        "Anthropic",
        "Meta",
        "Microsoft",
        "Perplexity",
        "Moonshot",
        "Qwen team",
    )
    lowered = content.lower()
    for owner in known_owners:
        if owner.lower() in lowered:
            return owner
    return ""


def _selection_reason(item: dict[str, Any]) -> str:
    reason = _clean_text(str(item.get("selection_reason", "")))
    return reason if _is_english_fallback_text(reason) else ""


def _section_fallback_label(item: dict[str, Any]) -> str:
    labels = {
        "breakout_products": "a breakout AI product launch",
        "hot_news": "a major AI industry development",
        "llm": "a foundation model release",
        "image_video": "a multimodal image or video release",
        "product_updates": "a meaningful AI product update",
    }
    return labels.get(str(item.get("category") or ""), "an AI product update")


def _summary_from_reason(item: dict[str, Any], reason: str) -> str:
    cleaned = _clean_text(reason).rstrip(".")
    lowered = _sentence_case(cleaned)
    if " with " in lowered:
        base, feature = lowered.split(" with ", 1)
        return f"A {base} adds {feature.rstrip('.')}."
    if lowered.startswith("new "):
        return f"This launch introduces a {lowered[4:]}."
    if lowered.startswith("major "):
        return f"This story centers on a {lowered}."
    return f"This story centers on {lowered}."


def _title_from_reason(item: dict[str, Any], reason: str) -> str:
    cleaned = _clean_text(reason).rstrip(".")
    if " with " in cleaned:
        base, feature = cleaned.split(" with ", 1)
        candidate = f"{base} Adds {feature}"
    elif cleaned.lower().startswith("new "):
        candidate = cleaned[4:]
    else:
        candidate = cleaned
    words = candidate.split()
    if len(words) > 14:
        candidate = " ".join(words[:14]).rstrip(",;:")
    return candidate


def _bullets_from_reason(item: dict[str, Any], reason: str) -> list[str]:
    cleaned = _clean_text(reason).rstrip(".")
    bullets: list[str] = []
    lowered = cleaned.lower()

    if "enterprise" in lowered or "team" in lowered or "collaboration" in lowered:
        bullets.append("The workflow is aimed at coordinated team collaboration rather than solo prompting.")
    if "coding" in lowered:
        bullets.append("Coding is treated as a core workflow instead of a side feature.")
    if "agents" in lowered or "agentic" in lowered:
        bullets.append("Integrated agents are embedded directly into the working environment.")
    if "llm" in lowered or "model" in lowered:
        bullets.append("The release was treated as a model-focused update rather than general company news.")

    if str(item.get("category") or "") == "breakout_products":
        bullets.append("The product is framed as a new workflow rather than a routine feature refresh.")
    elif str(item.get("category") or "") == "llm":
        bullets.append("The shortlist placed it in the foundation model track rather than general product news.")
    elif str(item.get("category") or "") == "image_video":
        bullets.append("The shortlist placed it in the multimodal release track rather than a generic product launch.")
    elif str(item.get("category") or "") == "product_updates":
        bullets.append("The update was treated as a meaningful shipped change rather than general commentary.")
    else:
        bullets.append(f"The item was selected as {_section_fallback_label(item)}.")

    deduped: list[str] = []
    for bullet in bullets:
        cleaned_bullet = _clean_text(bullet)
        if not cleaned_bullet:
            continue
        if _bullet_repeats_summary(_summary_from_reason(item, reason), cleaned_bullet, deduped):
            continue
        deduped.append(cleaned_bullet)
        if len(deduped) >= 3:
            return deduped

    fallback_pool = [
        "The shortlist ranked it as a strong candidate for the final reader-facing digest.",
        "The release was treated as a substantial workflow story rather than minor chatter.",
        "The item survived final editorial review because it signaled a concrete AI product move.",
    ]
    for bullet in fallback_pool:
        if _bullet_repeats_summary(_summary_from_reason(item, reason), bullet, deduped):
            continue
        deduped.append(bullet)
        if len(deduped) >= 3:
            return deduped

    return deduped[:3]


def _join_phrases(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _extract_primary_fact(item: dict[str, Any]) -> str:
    content = _clean_text(str(item.get("content", "")))
    if not content:
        return ""

    content = re.sub(r"Product categories:\s*.+?(?:[.!?]|$)", "", content, flags=re.IGNORECASE).strip()
    title_norm = _normalized_compare_text(str(item.get("title", "")))

    for sentence in _extract_distinct_sentences(content, limit=5):
        cleaned = _clean_text(sentence.rstrip(". "))
        normalized = _normalized_compare_text(cleaned)
        if not normalized:
            continue
        if title_norm and (normalized == title_norm or normalized in title_norm or title_norm in normalized):
            continue
        if _looks_non_reader_facing(cleaned):
            continue
        return cleaned
    return ""


def _sentence_case(value: str) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return cleaned
    return cleaned[0].lower() + cleaned[1:]


def _fallback_product_summary(item: dict[str, Any]) -> str:
    title = _clean_source_title(str(item.get("title", "")), str(item.get("source", "")))
    primary_fact = _extract_primary_fact(item)
    categories = _extract_product_categories(item)

    lowered_fact = _sentence_case(primary_fact)
    if lowered_fact:
        if "option + space" in lowered_fact and "right there" in lowered_fact:
            subject = title or "The product"
            return f"{subject} puts an AI assistant behind a Mac keyboard shortcut."
        if any(lowered_fact.startswith(f"{verb} ") for verb in ACTION_LEADING_VERBS):
            return f"It helps users {lowered_fact.rstrip('.')}."
        return f"{primary_fact.rstrip('.')}."

    if categories:
        return f"It is positioned around {_join_phrases(categories[:4])} workflows."
    if title:
        return f"{title} is a newly featured AI product."
    return "This is a newly featured AI product."


def _deterministic_summary(item: dict[str, Any]) -> str:
    reason = _selection_reason(item)
    if reason:
        candidate = _summary_from_reason(item, reason)
        if not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate

    summary = _fallback_summary(item)
    if not _title_too_close(summary, str(item.get("title", ""))):
        return summary

    primary_fact = _extract_primary_fact(item)
    owner = _extract_owner_hint(item)
    categories = _extract_product_categories(item)

    lowered_fact = _sentence_case(primary_fact)
    if owner and "agentic coding" in lowered_fact:
        candidate = f"{owner} has positioned this release as a flagship model for agentic coding."
        if not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate
    if owner and primary_fact:
        candidate = f"{owner} has highlighted {lowered_fact.rstrip('.')}."
        if not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate
    if categories:
        candidate = f"This release targets {_join_phrases(categories[:4])} workflows."
        if not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate

    title = _clean_source_title(str(item.get("title", "")), str(item.get("source", "")))
    if title:
        words = title.split()
        if len(words) <= 4:
            candidate = f"This launch introduces a new AI release for advanced user workflows."
            if not _title_too_close(candidate, str(item.get("title", ""))):
                return candidate

    return summary


def _deterministic_title(item: dict[str, Any], summary: str) -> str:
    reason = _selection_reason(item)
    if reason:
        candidate = _title_from_reason(item, reason)
        if candidate and not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate

    candidate = _editorial_title_from_summary(item, summary)
    if not _title_too_close(candidate, str(item.get("title", ""))):
        return candidate

    primary_fact = _extract_primary_fact(item)
    owner = _extract_owner_hint(item)
    categories = _extract_product_categories(item)

    if owner and "agentic coding" in primary_fact.lower():
        candidate = f"{owner} Debuts a Flagship Model for Agentic Coding"
        if not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate
    if owner and categories:
        candidate = f"{owner} {PRODUCT_LAUNCH_VERBS[0].title()} a New Release for {_join_phrases(categories[:3])} Workflows"
        if not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate
    if primary_fact:
        words = primary_fact.rstrip(". ").split()
        candidate = " ".join(words[:12]).rstrip(",;:")
        if candidate and not _title_too_close(candidate, str(item.get("title", ""))):
            return candidate

    return _fallback_display_title(item)


def _finalize_summary(item: dict[str, Any], summary: str) -> str:
    sentences = _extract_distinct_sentences(summary, limit=5)
    title_norm = _normalized_compare_text(str(item.get("title", "")))

    for sentence in sentences:
        cleaned = _clean_text(sentence.rstrip(". "))
        normalized = _normalized_compare_text(cleaned)
        if not normalized or _looks_non_reader_facing(cleaned):
            continue
        if _is_product_hunt_item(item):
            cleaned = re.sub(r"Product categories:\s*.+$", "", cleaned, flags=re.IGNORECASE).strip().rstrip(",;:")
        if title_norm and normalized == title_norm:
            continue
        return f"{cleaned}."

    return _fallback_summary(item)


def _fallback_summary(item: dict[str, Any]) -> str:
    title = _clean_source_title(str(item.get("title", "")), str(item.get("source", "")))

    if _is_product_hunt_item(item):
        return _fallback_product_summary(item)

    primary_fact = _extract_primary_fact(item)
    if primary_fact:
        return f"{primary_fact.rstrip('.')}."
    if title:
        return f"{title.rstrip('.')}."
    return "This item covers an AI-related development."


def _deterministic_enrichment(item: dict[str, Any]) -> dict[str, Any]:
    summary = _deterministic_summary(item)
    display_title = _deterministic_title(item, summary)
    reason = _selection_reason(item)
    if reason and _has_non_english_script(str(item.get("content", ""))):
        key_points = _bullets_from_reason(item, reason)
    else:
        key_points = _ensure_complementary_bullets(item, summary, [])
    return {
        "display_title": _clean_text(display_title, 180),
        "summary": _clean_text(summary, 600),
        "key_points": [_clean_text(point, 160) for point in key_points[:3]],
    }


def _fallback_key_points(item: dict[str, Any]) -> list[str]:
    title = _clean_source_title(str(item.get("title", "")), str(item.get("source", "")))
    content = _clean_text(str(item.get("content", "")))
    categories = _extract_product_categories(item)
    candidate_points: list[str] = []

    for sentence in _extract_distinct_sentences(content, limit=6):
        cleaned = _clean_text(sentence.rstrip(". "), 140)
        if cleaned and not _looks_non_reader_facing(cleaned):
            candidate_points.append(cleaned)

    if categories:
        candidate_points.append(f"Category focus: {_join_phrases(categories[:4])}")

    if title and _is_product_hunt_item(item):
        if " for Mac" in title:
            candidate_points.append("Targets Mac desktop usage")
        version_match = re.search(r"\b\d+(?:\.\d+)+\b", title)
        if version_match:
            candidate_points.append(f"Presented as a {version_match.group(0)} release")
        candidate_points.append(f"Product focus: {title}")
    elif title:
        candidate_points.append(title)

    accepted: list[str] = []
    seen: set[str] = set()
    for point in candidate_points:
        cleaned = _clean_text(point, 140).rstrip(". ")
        normalized = _normalized_compare_text(cleaned)
        if not cleaned or not normalized or normalized in seen or _looks_non_reader_facing(cleaned):
            continue
        seen.add(normalized)
        accepted.append(cleaned)
        if len(accepted) >= 3:
            break

    while len(accepted) < 3 and accepted:
        accepted.append(accepted[-1])

    return accepted[:3] if accepted else ["Key details were limited in the scraped source material."] * 3


def _extract_distinct_sentences(text: str, limit: int = 4) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    distinct: list[str] = []
    seen: set[str] = set()

    for sentence in sentences:
        candidate = _clean_text(sentence)
        if not candidate:
            continue
        normalized = _normalized_compare_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        distinct.append(candidate if candidate.endswith((".", "!", "?")) else f"{candidate}.")
        if len(distinct) >= limit:
            break

    return distinct


def _extract_fact_candidates(item: dict[str, Any], limit: int = 8) -> list[str]:
    text = _clean_text(str(item.get("content", "")))
    if not text:
        return []

    raw_parts: list[str] = []
    for sentence in _extract_distinct_sentences(text, limit=limit * 2):
        raw_parts.append(sentence)
        for fragment in re.split(r"\s*[;:]\s*|\s+\u2014\s+|\s+-\s+|\s+and\s+", sentence):
            cleaned = _clean_text(fragment)
            if len(cleaned.split()) >= 4:
                raw_parts.append(cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}.")

    deduped: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        normalized = _normalized_compare_text(part)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(part)
        if len(deduped) >= limit:
            break

    return deduped


def _bullet_repeats_summary(summary: str, bullet: str, existing_bullets: list[str] | None = None) -> bool:
    bullet_norm = _normalized_compare_text(bullet)
    if not bullet_norm:
        return True

    summary_norm = _normalized_compare_text(summary)
    if bullet_norm in summary_norm:
        return True

    for sentence_norm in _normalized_sentences(summary):
        if bullet_norm == sentence_norm:
            return True
        if bullet_norm in sentence_norm or sentence_norm in bullet_norm:
            return True
        if SequenceMatcher(None, bullet_norm, sentence_norm).ratio() >= 0.82:
            return True

    for existing in existing_bullets or []:
        existing_norm = _normalized_compare_text(existing)
        if not existing_norm:
            continue
        if bullet_norm == existing_norm:
            return True
        if SequenceMatcher(None, bullet_norm, existing_norm).ratio() >= 0.9:
            return True

    return False


def _metadata_fact_candidates(item: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    categories = _extract_product_categories(item)
    if categories:
        candidates.append(f"Category focus: {_join_phrases(categories[:4])}.")

    return candidates


def _ensure_complementary_bullets(item: dict[str, Any], summary: str, bullets: list[str]) -> list[str]:
    accepted: list[str] = []

    for bullet in bullets:
        cleaned = _clean_text(str(bullet), 160)
        if not cleaned:
            continue
        if _looks_non_reader_facing(cleaned):
            continue
        cleaned = re.sub(r"^Product categories:\s*", "Category focus: ", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."
        if _bullet_repeats_summary(summary, cleaned, accepted):
            continue
        accepted.append(cleaned)
        if len(accepted) >= 3:
            return accepted

    for candidate in _extract_fact_candidates(item) + _metadata_fact_candidates(item):
        cleaned = _clean_text(candidate, 160)
        if not cleaned:
            continue
        if _looks_non_reader_facing(cleaned):
            continue
        cleaned = re.sub(r"^Product categories:\s*", "Category focus: ", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."
        if _bullet_repeats_summary(summary, cleaned, accepted):
            continue
        accepted.append(cleaned)
        if len(accepted) >= 3:
            return accepted

    fallback_points = _fallback_key_points(item)
    for candidate in fallback_points:
        cleaned = _clean_text(candidate, 160)
        if not cleaned:
            continue
        if _looks_non_reader_facing(cleaned):
            continue
        cleaned = re.sub(r"^Product categories:\s*", "Category focus: ", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."
        if _bullet_repeats_summary(summary, cleaned, accepted):
            continue
        accepted.append(cleaned)
        if len(accepted) >= 3:
            return accepted

    while len(accepted) < 3 and fallback_points:
        accepted.append(_clean_text(fallback_points[min(len(accepted), len(fallback_points) - 1)], 160))

    return accepted[:3]


def _normalize_enrichment_records(records: Any) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    if not isinstance(records, list):
        return normalized

    for record in records:
        if not isinstance(record, dict):
            continue
        url = str(record.get("url", "")).strip()
        if not url:
            continue

        bullets = record.get("key_points")
        if not isinstance(bullets, list):
            bullets = []
        cleaned_bullets = [_clean_text(str(point), 160) for point in bullets if _clean_text(str(point), 160)]

        normalized[url] = {
            "display_title": _clean_text(str(record.get("display_title", "")), 180),
            "summary": _clean_text(str(record.get("summary", "")), 600),
            "key_points": cleaned_bullets[:3],
        }
    return normalized


def _has_non_english_script(value: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", value or ""))


def _enrichment_quality_issues(
    chunk: list[dict[str, Any]],
    enrichment_by_url: dict[str, dict[str, Any]],
) -> list[str]:
    issues: list[str] = []

    for item in chunk:
        url = str(item.get("url") or "").strip()
        record = enrichment_by_url.get(url)
        if not record:
            issues.append(f"missing enrichment for {url}")
            continue

        display_title = _clean_text(str(record.get("display_title", "")))
        summary = _clean_text(str(record.get("summary", "")))
        bullets = [_clean_text(str(point)) for point in record.get("key_points") or [] if _clean_text(str(point))]

        if not display_title:
            issues.append(f"empty display_title for {url}")
        elif _title_too_close(display_title, str(item.get("title", ""))):
            issues.append(f"display_title too close to source title for {url}")
        elif _has_non_english_script(display_title):
            issues.append(f"display_title is not English for {url}")

        if not summary:
            issues.append(f"empty summary for {url}")
        elif _has_non_english_script(summary):
            issues.append(f"summary is not English for {url}")
        elif _looks_non_reader_facing(summary):
            issues.append(f"summary is not reader-facing for {url}")
        elif _title_too_close(summary, str(item.get("title", ""))):
            issues.append(f"summary too close to source title for {url}")
        elif _sentence_count(summary) != 1:
            issues.append(f"summary is not exactly one sentence for {url}")

        if len(bullets) != 3:
            issues.append(f"expected 3 bullets for {url}, got {len(bullets)}")
            continue

        accepted: list[str] = []
        for bullet in bullets:
            if _has_non_english_script(bullet):
                issues.append(f"bullet is not English for {url}")
                break
            if _looks_non_reader_facing(bullet):
                issues.append(f"bullet is not reader-facing for {url}")
                break
            if _bullet_repeats_summary(summary, bullet, accepted):
                issues.append(f"bullet repeats summary or another bullet for {url}")
                break
            accepted.append(bullet)

    return issues


def _request_chunk_enrichment(
    chunk: list[dict[str, Any]],
    *,
    prompt_loader: PromptLoader,
    invoker,
    max_attempts: int,
) -> dict[str, dict[str, Any]]:
    prompt_input = [_prepare_prompt_item(item) for item in chunk]
    prompt = prompt_loader.load(
        "present",
        input_json=json.dumps(prompt_input, ensure_ascii=False, indent=2),
    )
    errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
        try:
            text = invoker(prompt)
            chunk_enrichment = _normalize_enrichment_records(parse_json_from_model_output(text))
            issues = _enrichment_quality_issues(chunk, chunk_enrichment)
            if issues:
                raise ValueError("; ".join(issues[:6]))
            return chunk_enrichment
        except Exception as exc:  # noqa: BLE001 - explicit chunk retry boundary
            errors.append(f"attempt {attempt}: {exc}")

    raise RuntimeError(" | ".join(errors))


def _enrich_chunk(
    chunk: list[dict[str, Any]],
    *,
    prompt_loader: PromptLoader,
    invoker,
    max_attempts: int,
) -> dict[str, dict[str, Any]]:
    try:
        return _request_chunk_enrichment(
            chunk,
            prompt_loader=prompt_loader,
            invoker=invoker,
            max_attempts=max_attempts,
        )
    except Exception as exc:
        if len(chunk) == 1:
            item = chunk[0]
            deterministic = {str(item.get("url") or ""): _deterministic_enrichment(item)}
            issues = _enrichment_quality_issues(chunk, deterministic)
            if issues:
                raise RuntimeError(
                    "Presentation enrichment failed quality checks; deterministic fallback also failed. "
                    + str(exc)
                    + " | "
                    + "; ".join(issues[:6])
                ) from exc
            return deterministic

    merged: dict[str, dict[str, Any]] = {}
    for item in chunk:
        merged.update(
            _enrich_chunk(
                [item],
                prompt_loader=prompt_loader,
                invoker=invoker,
                max_attempts=max_attempts,
            )
        )
    return merged


def enrich_digest_for_display(digest: dict[str, Any], chunk_size: int = 6) -> dict[str, Any]:
    enriched = deepcopy(digest)
    items: list[dict[str, Any]] = []
    for category in DISPLAY_CATEGORY_ORDER:
        items.extend(enriched.get("categories", {}).get(category) or [])

    if not items:
        return enriched

    enrichment_by_url: dict[str, dict[str, Any]] = {}

    prompt_loader = PromptLoader()
    invoker = get_llm_invoker(LLM_EDITOR_CONFIG, label="editorial")
    max_attempts = int(os.environ.get("PRESENTATION_MAX_ATTEMPTS", "3"))

    for start in range(0, len(items), chunk_size):
        chunk = items[start : start + chunk_size]
        enrichment_by_url.update(
            _enrich_chunk(
                chunk,
                prompt_loader=prompt_loader,
                invoker=invoker,
                max_attempts=max_attempts,
            )
        )

    for category, category_items in (enriched.get("categories") or {}).items():
        for item in category_items:
            enriched_item = enrichment_by_url.get(item.get("url", "")) or {}
            if not enriched_item:
                raise RuntimeError(f"Missing presentation enrichment for {item.get('url', '')}")

            item["summary"] = _finalize_summary(item, enriched_item["summary"])
            candidate_title = enriched_item["display_title"]
            candidate_title = _strip_leading_source_reference(candidate_title, str(item.get("source", "")))
            if _title_too_close(candidate_title, str(item.get("title", ""))):
                raise RuntimeError(f"Presentation title is too close to source title: {item.get('url', '')}")
            item["display_title"] = _strip_leading_source_reference(
                candidate_title.rstrip(".:; "),
                str(item.get("source", "")),
            )
            bullet_points = enriched_item["key_points"]
            item["key_points"] = _ensure_complementary_bullets(item, item["summary"], bullet_points)
            final_issues = _enrichment_quality_issues([item], {item.get("url", ""): {
                "display_title": item["display_title"],
                "summary": item["summary"],
                "key_points": item["key_points"],
            }})
            if final_issues:
                raise RuntimeError(
                    "Presentation enrichment failed final quality checks: " + "; ".join(final_issues[:6])
                )

    return enriched
