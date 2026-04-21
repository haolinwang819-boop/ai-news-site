"""
流水线入口：从文件或 stdin 读取抓取条目，运行 LangGraph 流水线，将结果写入 data/digests/YYYY-MM-DD.json。
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .config import DIGESTS_DIR
from .editorial_routing import (
    CATEGORY_LIMITS,
    CATEGORY_ORDER,
    item_sort_key,
    reroute_items_for_digest,
)
from .models import PipelineItem
from .pipeline import (
    ProcessingPipeline,
    _fallback_classify_items,
    _fallback_dedup_items,
    _fallback_normalize_items,
)
from .presentation import enrich_digest_for_display


def _ensure_digests_dir():
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_digest(deduped_items: list[PipelineItem], date: str | None = None) -> dict:
    """将去重后的条目按 category 分组，得到规范中的日报结构。"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    categories = {category: [] for category in CATEGORY_ORDER}
    routed_items = reroute_items_for_digest(deduped_items)

    grouped_items: dict[str, list[PipelineItem]] = {category: [] for category in CATEGORY_ORDER}
    for item in routed_items:
        if item.category not in grouped_items:
            grouped_items[item.category] = []
        grouped_items[item.category].append(item)

    for category in CATEGORY_ORDER:
        values = sorted(grouped_items.get(category, []), key=item_sort_key)
        limit = CATEGORY_LIMITS.get(category, int(os.environ.get("DIGEST_MAX_ITEMS_PER_CATEGORY", "10")))
        if limit > 0:
            values = values[:limit]
        categories[category] = [item.to_dict() for item in values]

    total = sum(len(v) for v in categories.values())
    return {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "total_count": total,
        "categories": categories,
    }


def _chunk_list(items: list[dict], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _merge_final_items(items: list[PipelineItem]) -> list[PipelineItem]:
    merged: list[PipelineItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in items:
        normalized_url = item.url.strip()
        normalized_title = item.title.strip().lower()
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title and normalized_title in seen_titles:
            continue
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        merged.append(item)

    return merged


def _fast_path_process(items: list[dict]) -> list[PipelineItem]:
    normalized = _fallback_normalize_items(items)
    classified = _fallback_classify_items(normalized)
    deduped = _fallback_dedup_items(classified)
    return sorted(deduped, key=item_sort_key, reverse=False)


def _dedup_raw_items(items: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in items:
        normalized_url = str(item.get("url") or "").strip()
        normalized_title = str(item.get("title") or "").strip().lower()
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title and normalized_title in seen_titles:
            continue
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        deduped.append(item)

    return deduped


def _annotate_product_hunt_ranks(items: list[dict]) -> list[dict]:
    annotated: list[dict] = []
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


def main():
    parser = argparse.ArgumentParser(description="AI 资讯处理流水线（LangGraph）")
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="抓取条目 JSON 文件路径（每行一条或整体数组）；缺省为 stdin",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 digest 文件路径；缺省为 data/digests/YYYY-MM-DD.json",
    )
    parser.add_argument(
        "--date",
        help="日报日期 YYYY-MM-DD；缺省为今天",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("PROCESSING_BATCH_SIZE", "12")),
        help="分批处理的 batch size；缺省为 12",
    )
    args = parser.parse_args()

    # 读取输入条目
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
        # 尝试 JSONL
        items = []
        for line in input_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))

    if not items:
        print("未读取到任何条目，退出。", file=sys.stderr)
        sys.exit(1)

    items = _annotate_product_hunt_ranks(items)
    raw_count = len(items)
    items = _dedup_raw_items(items)
    print(f"已读取 {raw_count} 条条目，预去重后 {len(items)} 条，开始运行流水线…")

    fast_path_threshold = int(os.environ.get("PROCESSING_FAST_PATH_THRESHOLD", "24"))
    force_fast_path = os.environ.get("PROCESSING_FORCE_FAST_PATH", "").lower() in {"1", "true", "yes"}

    if force_fast_path or len(items) > fast_path_threshold:
        print(f"启用快速路径：{len(items)} 条输入超过阈值 {fast_path_threshold}。")
        deduped = _fast_path_process(items)
    else:
        pipeline = ProcessingPipeline()
        batch_size = max(args.batch_size, 1)
        merged_items: list[PipelineItem] = []

        for index, batch in enumerate(_chunk_list(items, batch_size), start=1):
            print(f"处理 batch {index}：{len(batch)} 条")
            result = pipeline.run(batch)
            error = result.get("error")
            if error:
                print(f"流水线错误: {error}", file=sys.stderr)
                sys.exit(2)
            merged_items.extend(result.get("deduped_items") or [])

        deduped = _merge_final_items(merged_items)

    print(f"去重后共 {len(deduped)} 条。")

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    digest = _build_digest(deduped, date)
    digest = enrich_digest_for_display(digest)

    _ensure_digests_dir()
    out_path = args.output or str(DIGESTS_DIR / f"{date}.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    print(f"已写入: {out_path}")


if __name__ == "__main__":
    main()
