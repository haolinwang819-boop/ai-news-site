#!/usr/bin/env python3
"""
Build browser-ready data for the NextToken web experience from one or more digests.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from datetime import datetime
import os
from pathlib import Path
from typing import Any

from nexttoken_sections import SECTION_DEFS, iter_display_sections
from render_digest_preview import display_source_label, format_date
from supabase_subscription_store import supabase_public_config

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SITE_DATA_OUTPUT = WORKSPACE_ROOT / "website" / "data" / "site-data.js"


def _load_root_env_file() -> None:
    env_path = WORKSPACE_ROOT / ".env.local"
    if not env_path.exists():
        return

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


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.min
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min


def _sort_timestamp(value: str) -> float:
    dt = _parse_datetime(value)
    if dt == datetime.min:
        return 0.0
    try:
        return dt.timestamp()
    except (OverflowError, OSError, ValueError):
        return 0.0


def _slugify(text: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return lowered or "item"


def _visual_type(section_id: str, item: dict[str, Any]) -> str:
    if section_id == "breakout":
        return "logo"
    if item.get("image_url"):
        return "image"
    return "none"


def _logo_url(section_id: str, item: dict[str, Any]) -> str | None:
    if section_id != "breakout":
        return item.get("logo_url") or None
    return item.get("logo_url") or item.get("image_url") or None


def _model_track(item: dict[str, Any]) -> str:
    category = item.get("category")
    if category == "image_video":
        return "Multimodal"
    if category == "llm":
        return "Foundation Model"
    return ""


def _normalize_item(section_id: str, item: dict[str, Any], index: int) -> dict[str, Any]:
    title = (item.get("display_title") or item.get("title") or "AI update").strip()
    published_time = item.get("published_time") or ""
    key_points = [str(point).strip() for point in item.get("key_points") or [] if str(point).strip()]
    key_points = key_points[:3]

    return {
        "id": f"{section_id}-{index}-{_slugify(title)}",
        "title": title,
        "sourceTitle": item.get("title") or "",
        "summary": (item.get("summary") or "").strip(),
        "keyPoints": key_points,
        "url": item.get("url") or "",
        "source": item.get("source") or "",
        "sourceLabel": display_source_label(item),
        "publishedAt": published_time,
        "dateLabel": format_date(published_time),
        "sortTimestamp": _sort_timestamp(published_time),
        "imageUrl": item.get("image_url") or None,
        "logoUrl": _logo_url(section_id, item),
        "visualType": _visual_type(section_id, item),
        "productRank": item.get("product_rank"),
        "category": item.get("category") or "",
        "modelTrack": _model_track(item),
        "searchText": " ".join(
            part
            for part in [
                title,
                item.get("summary") or "",
                " ".join(key_points),
                item.get("source") or "",
                display_source_label(item),
            ]
            if part
        ).lower(),
    }


def _build_digest_snapshot(digest: dict[str, Any]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []

    for section in iter_display_sections(digest):
        normalized_items = [
            _normalize_item(section["id"], item, index)
            for index, item in enumerate(section["items"], start=1)
        ]
        sections.append(
            {
                "id": section["id"],
                "label": section["label"],
                "shortLabel": section["shortLabel"],
                "cnLabel": section["cnLabel"],
                "description": section["description"],
                "accent": section["accent"],
                "count": len(normalized_items),
                "items": normalized_items,
            }
        )

    return {
        "date": digest.get("date") or "",
        "generatedAt": digest.get("generated_at") or "",
        "totalCount": sum(section["count"] for section in sections),
        "sectionCount": len(SECTION_DEFS),
        "sections": sections,
    }


def _load_existing_snapshots(site_data_path: str | Path | None) -> list[dict[str, Any]]:
    if not site_data_path:
        return []

    path = Path(site_data_path)
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8").strip()
    prefix = "window.__NEXTTOKEN_DATA__ = "
    if text.startswith(prefix):
        text = text[len(prefix):]
    if text.endswith(";"):
        text = text[:-1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    existing = payload.get("digests")
    if isinstance(existing, list) and existing:
        return existing

    legacy_sections = payload.get("sections")
    if isinstance(legacy_sections, list) and legacy_sections:
        return [
            {
                "date": payload.get("digestDate") or "",
                "generatedAt": payload.get("generatedAt") or "",
                "totalCount": payload.get("totalCount") or 0,
                "sectionCount": payload.get("sectionCount") or len(legacy_sections),
                "sections": legacy_sections,
            }
        ]
    return []


def _merge_snapshots(
    existing_snapshots: list[dict[str, Any]],
    discovered_snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_date: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for snapshot in existing_snapshots:
        date = str(snapshot.get("date") or "").strip()
        if date:
            by_date[date] = snapshot

    for snapshot in discovered_snapshots:
        date = str(snapshot.get("date") or "").strip()
        if date:
            by_date[date] = snapshot

    return sorted(
        by_date.values(),
        key=lambda digest: digest.get("date") or "",
        reverse=True,
    )


def _build_archive_sections(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    archive_sections: list[dict[str, Any]] = []

    for section_def in SECTION_DEFS:
        count = 0
        for snapshot in snapshots:
            for section in snapshot.get("sections") or []:
                if section.get("id") == section_def["id"]:
                    count += int(section.get("count") or 0)
                    break

        archive_sections.append(
            {
                "id": section_def["id"],
                "label": section_def["label"],
                "shortLabel": section_def["short_label"],
                "cnLabel": section_def["cn_label"],
                "description": section_def["description"],
                "accent": section_def["accent"],
                "count": count,
            }
        )

    return archive_sections


def discover_digest_paths(
    explicit_digest: str | Path | None = None,
    archive_dir: str | Path | None = None,
) -> list[Path]:
    ordered_paths: list[Path] = []

    if explicit_digest:
        path = Path(explicit_digest)
        if not path.is_absolute():
            path = WORKSPACE_ROOT / path
        if path.exists():
            ordered_paths.append(path)

    if archive_dir:
        root = Path(archive_dir)
        if not root.is_absolute():
            root = WORKSPACE_ROOT / root
        if root.exists():
            ordered_paths.extend(sorted(root.glob("**/digest_*.json"), reverse=True))

    default_digest = WORKSPACE_ROOT / "output" / "digest.json"
    if default_digest.exists():
        ordered_paths.append(default_digest)

    deduped: list[Path] = []
    seen = set()
    for path in ordered_paths:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def build_site_data_from_paths(digest_paths: list[Path]) -> dict[str, Any]:
    _load_root_env_file()
    supabase_config = supabase_public_config()
    digests_by_date: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for path in digest_paths:
        try:
            digest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        snapshot = _build_digest_snapshot(digest)
        date = snapshot["date"] or path.stem
        if date not in digests_by_date:
            digests_by_date[date] = snapshot

    existing_snapshots = _load_existing_snapshots(SITE_DATA_OUTPUT)
    snapshots = _merge_snapshots(existing_snapshots, list(digests_by_date.values()))

    latest = snapshots[0] if snapshots else {"date": "", "generatedAt": "", "totalCount": 0, "sectionCount": len(SECTION_DEFS), "sections": []}
    archive_sections = _build_archive_sections(snapshots)
    archive_total_count = sum(int(snapshot.get("totalCount") or 0) for snapshot in snapshots)

    return {
        "brand": {
            "name": "NextToken",
            "eyebrow": "AI Signal Terminal",
            "tagline": "One surface for breakout AI products, market-moving AI news, model frontier releases, and top product updates.",
        },
        "digestDate": latest.get("date") or "",
        "generatedAt": latest.get("generatedAt") or "",
        "totalCount": latest.get("totalCount", 0),
        "sectionCount": len(SECTION_DEFS),
        "sections": latest.get("sections") or [],
        "archiveTotalCount": archive_total_count,
        "briefCount": len(snapshots),
        "archiveSections": archive_sections,
        "defaultDigestDate": latest.get("date") or "",
        "availableDates": [snapshot.get("date") or "" for snapshot in snapshots],
        "digests": snapshots,
        "supabase": {
            "enabled": bool(supabase_config),
            "url": supabase_config.get("url", ""),
            "publishableKey": supabase_config.get("publishable_key", ""),
        },
    }


def build_site_data(
    explicit_digest: str | Path | None = None,
    archive_dir: str | Path | None = "output/runs",
) -> dict[str, Any]:
    return build_site_data_from_paths(discover_digest_paths(explicit_digest, archive_dir))


def write_site_data(output_path: str | Path, site_data: dict[str, Any]) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "window.__NEXTTOKEN_DATA__ = " + json.dumps(site_data, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static website data from one or more digests")
    parser.add_argument("digest", nargs="?", default=None)
    parser.add_argument("--archive-dir", default="output/runs")
    parser.add_argument("--output", default="website/data/site-data.js")
    args = parser.parse_args()

    site_data = build_site_data(args.digest, archive_dir=args.archive_dir)
    output_path = write_site_data(args.output, site_data)
    print(output_path)


if __name__ == "__main__":
    main()
