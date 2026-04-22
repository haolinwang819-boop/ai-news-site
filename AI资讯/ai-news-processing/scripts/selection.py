"""
Deterministic prefilter + parallel shortlist screening.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .config import LLM_SELECTION_CONFIG, SCREENING_CONFIG
from .editorial_routing import CATEGORY_ORDER
from .llm_utils import PromptLoader, get_llm_invoker, parse_json_from_model_output


VALID_SECTIONS = set(CATEGORY_ORDER)


def _clean_text(value: str, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _normalize_compare_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\u3400-\u9fff]+", " ", _clean_text(value).lower()).strip()


def _near_duplicate_title(left: str, right: str) -> bool:
    left_norm = _normalize_compare_text(left)
    right_norm = _normalize_compare_text(right)
    if not left_norm or not right_norm:
        return False
    if left_norm == right_norm:
        return True
    if left_norm in right_norm or right_norm in left_norm:
        return True
    return SequenceMatcher(None, left_norm, right_norm).ratio() >= 0.96


def _parse_published_time(value: str) -> float:
    cleaned = _clean_text(value)
    if not cleaned:
        return 0.0
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_prompt_item(item: dict[str, Any]) -> dict[str, Any]:
    prepared = {
        "url": item.get("url") or "",
        "title": _clean_text(str(item.get("title") or ""), 220),
        "source": _clean_text(str(item.get("source") or ""), 80),
        "published_time": item.get("published_time") or "",
        "content": _clean_text(
            str(item.get("content") or item.get("summary") or item.get("title") or ""),
            1800,
        ),
    }
    if item.get("platform"):
        prepared["platform"] = item["platform"]
    if item.get("source_type"):
        prepared["source_type"] = item["source_type"]
    if item.get("product_rank") is not None:
        prepared["product_rank"] = item["product_rank"]
    return prepared


def deterministic_prefilter(
    items: list[dict[str, Any]],
    artifact_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Remove obvious junk before any model call:
    - exact URL dupes
    - normalized / near-title dupes
    - empty or ultra-short items
    - per-source caps
    """
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    source_counts: dict[str, int] = {}

    per_source_cap = max(int(SCREENING_CONFIG["per_source_cap"]), 1)
    min_content_length = max(int(SCREENING_CONFIG["min_content_length"]), 1)

    for raw in items:
        url = _clean_text(str(raw.get("url") or ""))
        title = _clean_text(str(raw.get("title") or ""))
        source = _clean_text(str(raw.get("source") or "Unknown source"))
        content = _clean_text(str(raw.get("content") or raw.get("summary") or title))

        if not url or not title or not source:
            continue
        if len(content) < min_content_length:
            continue
        lowered_url = url.lower()
        if lowered_url in seen_urls:
            continue
        if any(_near_duplicate_title(title, existing_title) for existing_title in seen_titles):
            continue

        source_key = source.lower()
        source_counts.setdefault(source_key, 0)
        if source_counts[source_key] >= per_source_cap:
            continue

        cloned = dict(raw)
        cloned["url"] = url
        cloned["title"] = title
        cloned["source"] = source
        cloned["content"] = content
        deduped.append(cloned)

        seen_urls.add(lowered_url)
        seen_titles.append(title)
        source_counts[source_key] += 1

    if artifact_dir:
        _save_json(artifact_dir / "raw_prefiltered.json", deduped)

    return deduped


def _normalize_screening_records(
    records: Any,
    expected_urls: set[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError("screening response is not a JSON array")

    normalized: dict[str, dict[str, Any]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            raise ValueError("screening record is not a JSON object")
        url = _clean_text(str(raw.get("url") or ""))
        if not url or url not in expected_urls:
            raise ValueError(f"unexpected url in screening output: {url or '<empty>'}")
        section = _clean_text(str(raw.get("section") or ""))
        keep = bool(raw.get("keep"))
        if keep and section not in VALID_SECTIONS:
            raise ValueError(f"invalid section for kept item: {section}")
        if not keep and section not in VALID_SECTIONS:
            section = "hot_news"

        try:
            score = int(raw.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(score, 100))

        reason = _clean_text(str(raw.get("reason") or ""), 160)
        if not reason:
            reason = "Low-signal candidate" if not keep else "Strong AI news candidate"

        normalized[url] = {
            "url": url,
            "keep": keep,
            "section": section,
            "score": score,
            "reason": reason,
        }

    missing_urls = expected_urls - set(normalized)
    if missing_urls:
        raise ValueError(f"missing screening decisions for {len(missing_urls)} items")

    return normalized


def _sort_selected_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            -(int(item.get("selection_score") or 0)),
            item.get("product_rank") if item.get("product_rank") is not None else 999,
            -_parse_published_time(str(item.get("published_time") or "")),
            _clean_text(str(item.get("title") or "")).lower(),
        ),
    )


def _screen_chunk(
    *,
    chunk: list[dict[str, Any]],
    chunk_index: int,
    prompt_loader: PromptLoader,
    invoker,
    artifact_dir: Path | None,
) -> dict[str, Any]:
    expected_urls = {_clean_text(str(item.get("url") or "")) for item in chunk}
    prompt_input = [_prepare_prompt_item(item) for item in chunk]
    prompt = prompt_loader.load(
        "select",
        input_json=json.dumps(prompt_input, ensure_ascii=False, indent=2),
    )

    errors: list[str] = []
    max_attempts = max(int(SCREENING_CONFIG["chunk_retry_attempts"]), 1)

    for attempt in range(1, max_attempts + 1):
        try:
            response_text = invoker(prompt)
            normalized = _normalize_screening_records(
                parse_json_from_model_output(response_text),
                expected_urls,
            )
            result = {
                "chunk_index": chunk_index,
                "status": "ok",
                "attempts": attempt,
                "items": prompt_input,
                "decisions": list(normalized.values()),
            }
            if artifact_dir:
                _save_json(artifact_dir / f"chunk_{chunk_index:02d}.json", result)
            return result
        except Exception as exc:  # noqa: BLE001 - keep chunk-local retry control explicit
            errors.append(f"attempt {attempt}: {exc}")

    result = {
        "chunk_index": chunk_index,
        "status": "failed",
        "errors": errors,
        "items": prompt_input,
    }
    if artifact_dir:
        _save_json(artifact_dir / f"chunk_{chunk_index:02d}.json", result)
    return result


def _apply_screening_decisions(
    items: list[dict[str, Any]],
    chunk_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions_by_url: dict[str, dict[str, Any]] = {}
    for result in chunk_results:
        for decision in result.get("decisions") or []:
            decisions_by_url[str(decision.get("url") or "")] = decision

    kept: list[dict[str, Any]] = []
    for item in items:
        url = _clean_text(str(item.get("url") or ""))
        decision = decisions_by_url.get(url)
        if not decision or not decision.get("keep"):
            continue

        selected = dict(item)
        selected["category"] = decision["section"]
        selected["selection_score"] = int(decision["score"])
        selected["selection_reason"] = decision["reason"]
        kept.append(selected)

    return kept


def merge_shortlist_candidates(kept: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept_by_section = {section: [] for section in CATEGORY_ORDER}
    for item in _sort_selected_candidates(kept):
        kept_by_section.setdefault(str(item.get("category") or ""), []).append(item)

    section_targets = dict(SCREENING_CONFIG["shortlist_targets"])
    max_items = max(int(SCREENING_CONFIG["max_items"]), 1)
    shortlist: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    leftovers: list[dict[str, Any]] = []

    for section in CATEGORY_ORDER:
        bucket = kept_by_section.get(section, [])
        target = max(int(section_targets.get(section, 0)), 0)
        for item in bucket[:target]:
            url = str(item.get("url") or "")
            if url in seen_urls:
                continue
            shortlist.append(item)
            seen_urls.add(url)
        leftovers.extend(bucket[target:])

    for item in _sort_selected_candidates(leftovers):
        if len(shortlist) >= max_items:
            break
        url = str(item.get("url") or "")
        if url in seen_urls:
            continue
        shortlist.append(item)
        seen_urls.add(url)

    return _sort_selected_candidates(shortlist[:max_items])


def build_shortlist(
    items: list[dict[str, Any]],
    artifact_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Use Gemini Flash in parallel to shrink a large corpus into a shortlist.
    """
    if not items:
        if artifact_dir:
            _save_json(artifact_dir / "shortlist.json", [])
        return []

    prompt_loader = PromptLoader()
    invoker = get_llm_invoker(LLM_SELECTION_CONFIG, label="selection")
    chunk_size = max(int(SCREENING_CONFIG["chunk_size"]), 1)
    chunks = [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]
    chunk_artifact_dir = artifact_dir / "screening" if artifact_dir else None

    results: list[dict[str, Any]] = []
    failed_chunks = 0

    with ThreadPoolExecutor(max_workers=max(int(SCREENING_CONFIG["max_workers"]), 1)) as executor:
        future_map = {
            executor.submit(
                _screen_chunk,
                chunk=chunk,
                chunk_index=index,
                prompt_loader=prompt_loader,
                invoker=invoker,
                artifact_dir=chunk_artifact_dir,
            ): index
            for index, chunk in enumerate(chunks, start=1)
        }

        for future in as_completed(future_map):
            result = future.result()
            results.append(result)
            if result.get("status") != "ok":
                failed_chunks += 1

    total_chunks = len(chunks)
    if total_chunks and (failed_chunks / total_chunks) > float(SCREENING_CONFIG["failure_ratio_threshold"]):
        raise RuntimeError(
            f"Screening aborted because {failed_chunks}/{total_chunks} chunks failed "
            + f"(threshold {SCREENING_CONFIG['failure_ratio_threshold']:.0%})."
        )

    kept = _apply_screening_decisions(items, results)
    shortlist = merge_shortlist_candidates(kept)

    if artifact_dir:
        _save_json(artifact_dir / "shortlist.json", shortlist)

    return shortlist
