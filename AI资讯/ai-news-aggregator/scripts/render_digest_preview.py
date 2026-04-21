#!/usr/bin/env python3
"""
Render digest JSON into English-first markdown and HTML previews.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from nexttoken_sections import iter_display_sections

def _contains_keyword(text: str, keyword: str) -> bool:
    lowered = text.lower()
    token = keyword.lower()
    if re.search(r"[\u4e00-\u9fff]", token):
        return token in lowered
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
    return bool(pattern.search(lowered))


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _append_tag(tags: list[str], tag: str) -> None:
    if tag not in tags:
        tags.append(tag)


def display_source_label(item: dict) -> str:
    source = (item.get("source") or "").strip()
    platform = (item.get("platform") or "").strip().lower()
    source_type = (item.get("source_type") or "").strip().lower()
    author_handle = (item.get("author_handle") or "").strip()

    if platform == "x":
        handle = author_handle or source.replace("(X)", "").strip()
        if handle and not handle.startswith("@"):
            handle = f"@{handle}"
        return f"X {handle}" if handle else "X"

    if platform == "instagram":
        handle = author_handle or source
        if handle and not handle.startswith("@"):
            handle = f"@{handle}"
        return f"Instagram {handle}" if handle else "Instagram"

    if platform == "xiaohongshu":
        return f"Xiaohongshu {source}" if source else "Xiaohongshu"

    if platform == "wechat":
        return f"WeChat {source}" if source else "WeChat"

    if source == "Product Hunt":
        rank = item.get("product_rank")
        return f"Product Hunt · #{rank}" if rank else "Product Hunt"

    if source_type == "official":
        return f"{source} website" if source else "Official website"

    if source_type == "media":
        return source or "Media"

    if source_type == "research":
        return source or "Research"

    if platform in {"site", "news", "research"}:
        if source_type == "official":
            return f"{source} website" if source else "Official website"
        return source or "Media"

    return source or "Source"


def _strip_display_source_prefix(item: dict, title: str) -> str:
    cleaned = (title or "").strip()
    source = (item.get("source") or "").strip()
    if not cleaned:
        return cleaned

    source_tokens = [source, source.replace("@", ""), "Product Hunt"]
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


def pick_tags(item: dict) -> list[str]:
    text = f"{item.get('title', '')} {item.get('content', '')}".lower()
    category = item.get("category")

    if category == "breakout_products":
        tags = []
        if _has_any(text, ("healthcare", "medical", "patient", "prescription", "clinical")):
            _append_tag(tags, "Healthcare AI")
        if _has_any(text, ("smart home", "display", "device", "hardware", "wearable", "speaker")):
            _append_tag(tags, "Consumer Devices")
        if _has_any(text, ("robot", "robotics", "drone", "evtol", "autonomous vehicle", "aviation", "mobility", "vehicle")):
            _append_tag(tags, "Robotics & Mobility")
        if _has_any(text, ("ecosystem", "platform", "studio", "stack", "hub", "developer api", "developer apis", "api", "apis")):
            _append_tag(tags, "AI Platforms")
        if _has_any(text, ("developer", "developers", "sdk", "cli", "coding", "code", "copilot", "workflow automation", "tool", "tools")):
            _append_tag(tags, "Developer Tools")
        if _has_any(text, ("chat", "assistant", "bot", "copilot", "customer support", "meeting avatar")):
            _append_tag(tags, "Conversational AI")
        if _has_any(text, ("enterprise", "business", "customer service", "contact center", "operations")):
            _append_tag(tags, "Enterprise AI")
        if _has_any(text, ("email", "document", "spreadsheet", "sheet", "workspace", "writing", "knowledge", "search")):
            _append_tag(tags, "Productivity")
        if not tags:
            tags.append("Product Launch")
        return tags[:2]

    if category == "product_updates":
        tags = []
        if _has_any(text, ("character ai", "lovart", "notion", "superhuman", "cursor", "grammarly", "zoom")):
            _append_tag(tags, "Head Product Update")
        if _has_any(text, ("assistant", "copilot", "bot", "agent", "agents")):
            _append_tag(tags, "Workflow Features")
        if _has_any(text, ("writing", "workspace", "document", "sheet", "email", "productivity")):
            _append_tag(tags, "Productivity")
        if _has_any(text, ("design", "creative", "image", "video")):
            _append_tag(tags, "Creative Tools")
        if not tags:
            tags.append("Product Update")
        return tags[:2]

    if category == "llm":
        if _has_any(text, ("benchmark", "评测", "arena", "mmlu", "leaderboard")):
            return ["Model Benchmarks"]
        if _has_any(text, ("gpu", "推理", "infra", "部署", "inference", "serving")):
            return ["AI Infra", "Inference"]
        if _has_any(text, ("moe", "mamba", "architecture", "attention", "reasoning architecture")):
            return ["Architecture"]
        return ["Language Models"]

    if category == "image_video":
        if _has_any(text, ("video generation", "text-to-video", "video", "视频", "sora", "runway", "可灵", "pika")):
            return ["Video Generation"]
        if _has_any(text, ("image editing", "editing", "edit", "background removal", "upscale", "retouch")):
            return ["Image Editing"]
        if _has_any(text, ("music", "音频", "语音", "voice", "speech", "tts")):
            return ["Audio Generation"]
        if _has_any(text, ("3d", "mesh", "gaussian", "nerf", "scene reconstruction")):
            return ["3D Generation"]
        if _has_any(text, ("vision", "ocr", "visual understanding", "image understanding", "vlm")):
            return ["Vision Models"]
        return ["Image Generation"]

    if _has_any(text, ("partnership", "collaboration", "join forces", "partnered")):
        return ["Partnerships"]
    if _has_any(text, ("policy", "regulation", "act", "compliance", "law")):
        return ["Policy & Regulation"]
    if _has_any(text, ("research", "science", "paper", "study", "benchmark")):
        return ["Research & Science"]
    if _has_any(text, ("发布", "上线", "product", "launch", "update", "feature")):
        return ["Product Launch"]
    if _has_any(text, ("开源", "github", "release", "open source")):
        return ["Open Source"]
    if _has_any(text, ("融资", "投资", "并购", "funding", "acquisition", "market", "valuation")):
        return ["Industry Moves", "Market Signals"]
    return ["Industry News"]


def display_title(item: dict) -> str:
    title = (item.get("display_title") or item.get("title") or "AI update").strip()
    return _strip_display_source_prefix(item, title)


def display_summary(item: dict) -> str:
    summary = (item.get("summary") or "").strip()
    if summary:
        return summary
    source = (item.get("source") or "The source").strip()
    return f"{source} published an AI-related update that was included in today's digest."


def display_key_points(item: dict) -> list[str]:
    points = item.get("key_points")
    if isinstance(points, list):
        cleaned = [str(point).strip() for point in points if str(point).strip()]
        if cleaned:
            return cleaned[:3]
    return [
        "Collected from the source material in this crawl window.",
        "Included because it adds a meaningful product or industry signal.",
        "Use the source link for the full primary context.",
    ]


def format_date(date_str: str) -> str:
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return date_str[:10]


def _optimized_image_url(image_url: str) -> str:
    if not image_url:
        return image_url

    parsed = urlparse(image_url)
    if "imgix.net" not in parsed.netloc:
        return image_url

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("auto", "format")
    query.setdefault("fit", "max")
    query.setdefault("w", "1400")
    query.setdefault("q", "90")
    query.setdefault("dpr", "2")
    return urlunparse(parsed._replace(query=urlencode(query)))


def _visual_url_for_item(item: dict) -> str:
    if item.get("category") == "breakout_products":
        return str(item.get("logo_url") or item.get("image_url") or "").strip()
    return str(item.get("image_url") or "").strip()


def render_card(item: dict) -> str:
    tags = " ".join(f"`{tag}`" for tag in pick_tags(item))
    source_line = f"[Read more]({item['url']}) · {format_date(item['published_time'])} · {display_source_label(item)}"

    lines = [
        f"### {display_title(item)}",
        "",
        f"> **Tags:** {tags}",
        ">",
        f"> {source_line}",
        "",
        display_summary(item),
        "",
    ]
    for point in display_key_points(item):
        lines.append(f"- {point}")
    lines.append("")
    if item.get("image_url"):
        lines.append(f"![Preview image]({item['image_url']})")
        lines.append("")
    lines.append("---")
    return "\n".join(lines)


def render_web_markdown(digest: dict) -> str:
    sections = iter_display_sections(digest)
    lines = [
        f"# Daily AI Brief — {digest['date']}",
        "",
        f"> {digest['total_count']} stories in today's digest",
        "",
    ]

    for section in sections:
        items = section["items"]
        if not items:
            continue
        lines.append(f"## {section['label']}")
        lines.append("")
        for item in items:
            lines.append(render_card(item))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_email_markdown(digest: dict) -> str:
    sections = iter_display_sections(digest)
    all_items = []
    for section in sections:
        all_items.extend(section["items"])

    lines = [
        "# Daily AI Brief · Email Preview",
        "",
        f"> {digest['date']} · {digest['total_count']} stories",
        "",
        "---",
        "",
        "## Top Stories",
        "",
    ]

    for idx, item in enumerate(all_items[:5], start=1):
        lines.append(f"{idx}. **{display_title(item)}** — {display_summary(item)}")

    lines.extend(["", "---", "", "## Full Brief", ""])

    for section in sections:
        items = section["items"]
        if not items:
            continue
        lines.append(f"### {section['label']}")
        lines.append("")
        for item in items:
            lines.append(f"#### {display_title(item)}")
            lines.append("")
            meta_parts = [f"[Read more]({item['url']})", format_date(item["published_time"]), display_source_label(item)]
            lines.append(f"> {' · '.join(part for part in meta_parts if part)}")
            lines.append("")
            lines.append(display_summary(item))
            lines.append("")
            for point in display_key_points(item):
                lines.append(f"- {point}")
            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_html_card(item: dict) -> str:
    tags_html = " ".join(
        f"<span style=\"display:inline-block;background:#f3f4f6;color:#374151;border-radius:999px;padding:4px 10px;font-size:12px;margin-right:6px;\">{html.escape(tag)}</span>"
        for tag in pick_tags(item)
    )
    meta_parts = [format_date(item["published_time"]), display_source_label(item)]
    meta_line = " · ".join(html.escape(part) for part in meta_parts if part)

    image_block = ""
    visual_url = _visual_url_for_item(item)
    if visual_url:
        image_url = _optimized_image_url(visual_url)
        if item.get("category") == "breakout_products":
            image_block = (
                '<div style="margin:16px 0 4px 0;">'
                '<div style="width:76px;height:76px;border-radius:18px;border:1px solid #e5e7eb;'
                'background:#ffffff;overflow:hidden;">'
                f'<img src="{html.escape(image_url)}" '
                'style="display:block;width:100%;height:100%;object-fit:cover;object-position:center;" alt="logo">'
                '</div>'
                '</div>'
            )
        else:
            image_block = (
                '<div style="margin-top:16px;border-radius:18px;overflow:hidden;background:#eef2f7;'
                'border:1px solid #e5e7eb;">'
                f'<img src="{html.escape(image_url)}" '
                'style="display:block;width:100%;height:auto;" alt="preview">'
                '</div>'
            )

    return f"""
    <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:20px 20px 18px;margin-bottom:18px;box-shadow:0 8px 24px rgba(15,23,42,0.05);">
      <div style="margin-bottom:10px;">{tags_html}</div>
      <h3 style="margin:0 0 10px 0;font-size:22px;line-height:1.35;color:#111827;">{html.escape(display_title(item))}</h3>
      <div style="font-size:13px;color:#6b7280;margin-bottom:12px;">
        <a href="{html.escape(item['url'])}" style="color:#0f766e;text-decoration:none;">Read more</a> · {meta_line}
      </div>
      <p style="margin:0 0 12px 0;font-size:15px;line-height:1.7;color:#374151;">{html.escape(display_summary(item))}</p>
      <ul style="margin:0 0 0 18px;padding:0;color:#374151;font-size:14px;line-height:1.7;">
        {''.join(f'<li>{html.escape(point)}</li>' for point in display_key_points(item))}
      </ul>
      {image_block}
    </section>
    """


def render_email_html(digest: dict) -> str:
    display_sections = iter_display_sections(digest)
    sections = []
    for section in display_sections:
        items = section["items"]
        if not items:
            continue
        cards = "\n".join(_render_html_card(item) for item in items)
        sections.append(
            f"""
            <section style="margin-bottom:28px;">
              <h2 style="margin:0 0 14px 0;font-size:24px;color:#111827;">{html.escape(section['label'])}</h2>
              {cards}
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily AI Brief - {html.escape(digest['date'])}</title>
</head>
<body style="margin:0;padding:0;background:#f6f3ee;font-family:Georgia,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',serif;color:#111827;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f3ee;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="760" cellpadding="0" cellspacing="0" style="max-width:760px;width:100%;">
          <tr>
            <td style="background:linear-gradient(135deg,#163b36 0%,#225d54 100%);padding:34px 32px;border-radius:26px 26px 0 0;">
              <div style="font-size:13px;letter-spacing:0.12em;color:#d1fae5;text-transform:uppercase;">Daily AI Brief</div>
              <h1 style="margin:10px 0 0 0;font-size:34px;line-height:1.15;color:#f8fafc;">Daily AI Brief</h1>
              <p style="margin:14px 0 0 0;font-size:16px;line-height:1.6;color:#d1fae5;">{html.escape(digest['date'])} · {digest['total_count']} stories</p>
            </td>
          </tr>
          <tr>
            <td style="background:#fcfbf8;padding:28px 24px 10px;border-radius:0 0 26px 26px;">
              {''.join(sections)}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def render_assets(digest: dict, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    date = digest.get("date", "preview")
    web_md_path = output_dir / f"web_preview_{date}.md"
    email_md_path = output_dir / f"email_preview_{date}.md"
    html_path = output_dir / "preview.html"

    web_md_path.write_text(render_web_markdown(digest), encoding="utf-8")
    email_md_path.write_text(render_email_markdown(digest), encoding="utf-8")
    html_path.write_text(render_email_html(digest), encoding="utf-8")

    return {"web_md": web_md_path, "email_md": email_md_path, "html": html_path}


def main():
    parser = argparse.ArgumentParser(description="Render digest preview markdown")
    parser.add_argument("digest", nargs="?", default="output/digest.json")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    digest_path = Path(args.digest)
    digest = json.loads(digest_path.read_text(encoding="utf-8"))
    paths = render_assets(digest, Path(args.output_dir))
    print(paths["web_md"])
    print(paths["email_md"])
    print(paths["html"])


if __name__ == "__main__":
    main()
