"""
Local-first editorial pipeline entrypoint:
collect -> deterministic prefilter -> parallel Flash screening ->
shortlist merge -> Pro presentation enrichment -> digest JSON
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DIGESTS_DIR
from .editorial_routing import CATEGORY_LIMITS, CATEGORY_ORDER, item_sort_key, route_item_for_digest
from .models import PipelineItem
from .presentation import enrich_digest_for_display
from .selection import build_shortlist, deterministic_prefilter


def _ensure_digests_dir() -> None:
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


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
    return False


def _sort_timestamp(value: str) -> float:
    cleaned = _clean_text(value)
    if not cleaned:
        return 0.0
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _priority_from_score(score: int | None) -> int:
    score = int(score or 0)
    if score >= 90:
        return 1
    if score >= 75:
        return 2
    if score >= 60:
        return 3
    return 4


def _artifact_dir(output_path: str | None, date: str) -> Path:
    explicit = os.environ.get("PROCESSING_ARTIFACTS_DIR")
    if explicit:
        return Path(explicit)
    if output_path:
        return Path(output_path).resolve().parent / "_artifacts"
    return DIGESTS_DIR / "_artifacts" / date


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _annotate_product_hunt_ranks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    product_rank = 0

    for item in items:
        cloned = dict(item)
        is_product_hunt = str(cloned.get("source") or "").lower() == "product hunt"
        is_product_hunt = is_product_hunt or "producthunt.com/products" in str(cloned.get("url") or "").lower()
        if is_product_hunt and cloned.get("product_rank") is None:
            product_rank += 1
            cloned["product_rank"] = product_rank
        annotated.append(cloned)

    return annotated


def _dedup_exact_raw_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in items:
        normalized_url = _clean_text(str(item.get("url") or "")).lower()
        normalized_title = _normalize_compare_text(str(item.get("title") or ""))
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title and normalized_title in seen_titles:
            continue
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        deduped.append(dict(item))

    return deduped


def _finalize_candidates(shortlist: list[dict[str, Any]], artifact_dir: Path | None = None) -> list[PipelineItem]:
    ordered = sorted(
        shortlist,
        key=lambda item: (
            -(int(item.get("selection_score") or 0)),
            item.get("product_rank") if item.get("product_rank") is not None else 999,
            -_sort_timestamp(str(item.get("published_time") or "")),
            _clean_text(str(item.get("title") or "")).lower(),
        ),
    )

    final_items: list[PipelineItem] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for raw in ordered:
        item = PipelineItem.from_dict(raw)
        item.priority = _priority_from_score(item.selection_score)

        corrected_category = route_item_for_digest(item)
        if corrected_category:
            item.category = corrected_category
        if item.category not in CATEGORY_ORDER:
            continue

        normalized_url = _clean_text(item.url).lower()
        if normalized_url and normalized_url in seen_urls:
            continue
        if any(_near_duplicate_title(item.title, title) for title in seen_titles):
            continue

        if normalized_url:
            seen_urls.add(normalized_url)
        seen_titles.append(item.title)
        final_items.append(item)

    if artifact_dir:
        _save_json(artifact_dir / "editorial_candidates.json", [item.to_dict() for item in final_items])

    return final_items


def _build_digest(items: list[PipelineItem], date: str) -> dict[str, Any]:
    grouped_items: dict[str, list[PipelineItem]] = {category: [] for category in CATEGORY_ORDER}
    for item in items:
        if item.category in grouped_items:
            grouped_items[item.category].append(item)

    categories: dict[str, list[dict[str, Any]]] = {}
    for category in CATEGORY_ORDER:
        values = sorted(grouped_items.get(category, []), key=item_sort_key)
        limit = CATEGORY_LIMITS.get(category, int(os.environ.get("DIGEST_MAX_ITEMS_PER_CATEGORY", "10")))
        categories[category] = [item.to_dict() for item in values[:limit]]

    total = sum(len(values) for values in categories.values())
    return {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "total_count": total,
        "categories": categories,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 资讯处理流水线（local-first parallel editorial pipeline）")
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="抓取条目 JSON 文件路径（每行一条或整体数组）；缺省为 stdin",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="输出 digest 文件路径；缺省为 data/digests/YYYY-MM-DD.json",
    )
    parser.add_argument(
        "--date",
        help="日报日期 YYYY-MM-DD；缺省为今天",
    )
    args = parser.parse_args()

    if args.input == "-":
        input_text = sys.stdin.read()
    else:
        input_text = Path(args.input).read_text(encoding="utf-8")

    try:
        data = json.loads(input_text)
        if isinstance(data, list):
            items = data
        else:
            items = data.get("items", [])
    except json.JSONDecodeError:
        items = []
        for line in input_text.strip().split("\n"):
            line = line.strip()
            if line:
                items.append(json.loads(line))

    if not items:
        print("未读取到任何条目，退出。", file=sys.stderr)
        sys.exit(1)

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    artifact_dir = _artifact_dir(args.output, date)

    items = _annotate_product_hunt_ranks(items)
    raw_count = len(items)
    raw_exact_deduped = _dedup_exact_raw_items(items)
    _save_json(artifact_dir / "raw_exact_deduped.json", raw_exact_deduped)

    print(f"已读取 {raw_count} 条条目，精确去重后 {len(raw_exact_deduped)} 条，开始规则预处理…")
    prefiltered = deterministic_prefilter(raw_exact_deduped, artifact_dir=artifact_dir)
    print(f"规则预处理后保留 {len(prefiltered)} 条，开始并行 Flash 初筛…")

    shortlist = build_shortlist(prefiltered, artifact_dir=artifact_dir)
    if not shortlist:
        print("Flash 初筛后没有可发布条目，终止。", file=sys.stderr)
        sys.exit(2)
    print(f"Flash 初筛后 shortlist {len(shortlist)} 条，开始最终候选整理…")

    final_items = _finalize_candidates(shortlist, artifact_dir=artifact_dir)
    if not final_items:
        print("最终候选为空，终止。", file=sys.stderr)
        sys.exit(2)
    print(f"最终候选 {len(final_items)} 条，开始 Pro 成稿与质量校验…")

    digest = _build_digest(final_items, date)
    digest = enrich_digest_for_display(
        digest,
        chunk_size=int(os.environ.get("LLM_EDITOR_CHUNK_SIZE", "6")),
    )

    _ensure_digests_dir()
    out_path = Path(args.output) if args.output else DIGESTS_DIR / f"{date}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已写入: {out_path}")


if __name__ == "__main__":
    main()
